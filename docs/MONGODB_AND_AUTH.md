# MongoDB integration and role-based login

*Adds persistent accounts and a queryable copy of the transaction ledger on
top of the existing file-based pipeline (data_generation/ → engine/ →
alerts/ still read the CSVs/JSON directly and are unaffected).*

## Why Beanie, not Mongoose

Mongoose is a JavaScript ODM; this backend is Python/FastAPI. **Beanie**
(async, built on Pydantic + pymongo's native async client) is the direct
equivalent: one `Document` class per collection, schema-validated on every
read and write, same "define a model, get a collection" ergonomics.

## Setup

```bash
# .env (repo root, gitignored)
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>/?appName=Cluster0
MONGODB_DB_NAME=Super_agent
JWT_SECRET=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
```

```bash
cd backend
pip install -r requirements.txt
python -m db.seed_users          # idempotent -- 6 mock accounts, one per role
python -m db.migrate_transactions   # idempotent -- replaces each split wholesale
python -m api.main
```

## Schemas (`backend/db/models.py`)

- **`User`** — `username` (unique), `hashed_password` (bcrypt), `role`
  (`agent` | `field_officer` | `area_team` | `provider_ops` | `risk_team` |
  `admin`), plus
  role-scoping fields: `agent_id`, `area`, and `provider`. Field officers and
  area teams are locked to an area; provider operations and risk teams are
  locked to a provider.
- **`Transaction`** — mirrors `data/transactions_{split}.csv` column-for-column.
  Migrated copy for querying; the CSVs stay the pipeline's source of truth.
  `agent_provider_balance_after` is nullable (Scenario C's data-fault
  injection corrupts some readings by design — see
  [DATA_AND_ASSUMPTIONS.md](./DATA_AND_ASSUMPTIONS.md)).

## Auth

Stateless JWT (`backend/auth/`): `POST /api/auth/login` verifies a bcrypt
hash and returns a 12-hour token carrying the identity fields (`sub`, role,
`agent_id`, `area`, `provider`); `GET /api/auth/me` lets the frontend restore
a session from a stored token on page reload without re-prompting for a
password.

The three lifecycle endpoints (`acknowledge`/`escalate`/`resolve`) now
**require** a valid token, and derive `actor` from it server-side — a
logged-in user can no longer act as an arbitrary client-supplied name (the
old `actor` field in the request body is gone).

## Historical analytics

`GET /api/agents/{agent_id}/analytics` groups the real transaction ledger
into observed 30-minute windows (configurable with `window_minutes`) and
returns closing physical-cash/provider balances plus ledger observation
counts. Empty windows are omitted, missing provider readings remain null, and
no value is interpolated or forecast.

The endpoint uses the same authorization rules as balances: an agent can read
only their own multi-provider history, provider-bound officers receive only
their assigned provider with cash removed, and administrators retain the
explicit global scope. The CSV cache uses file modification-time invalidation,
so newly appended or replaced source-ledger history is picked up on the next
request; the dashboard also provides a manual refresh control.

## Roles and dashboards

One primary dashboard per role, matching the app's existing 5 tabs, plus the
read-only Assistant as a shared helper for the operational roles:

| Role | Sees | Notes |
|---|---|---|
| `agent` | Agent view only | Locked to their own `agent_id` — no picker over other agents |
| `field_officer` | Ops/coordination + Assistant | Area-scoped agent-side cases |
| `area_team` | Ops/coordination + Assistant | Area escalation and resolution |
| `provider_ops` | Provider ops + Assistant | |
| `risk_team` | Risk/compliance + Assistant | |
| `admin` | All 5 tabs | The only multi-purpose role |

## Demo accounts (`backend/db/seed_users.py`)

Simple, memorable passwords by design — this is mock data behind a
prototype, not a real account system. Still bcrypt-hashed in the database;
shown on the login page itself (`frontend/src/lib/roles.js`'s
`DEMO_ACCOUNTS`) for convenience.

| Role | Username | Password | Data scope |
|---|---|---|---|
| Agent | `agent01` | `agent123` | All providers for `agent_01` |
| Field Officer | `fieldofficer` | `officer123` | Shibganj area |
| Area Team | `areateam` | `area123` | Shibganj area |
| Provider Ops | `providerops` | `provider123` | Nagad |
| Risk Team | `riskteam` | `risk123` | bKash |
| Admin | `admin` | `admin123` | Unrestricted |

The login form submits a selected role. It must match the stored user role.
Area/provider scope is always read from the user record and signed JWT, never
from client input.

## Security note

`MONGODB_URI` and `JWT_SECRET` live only in `.env` (gitignored, never
committed) — `.env.example` documents the shape without real values. If the
Atlas password was ever shared somewhere outside this repo (chat, a ticket,
etc.), rotate it in Atlas' UI; the app only needs `.env` updated to match.
