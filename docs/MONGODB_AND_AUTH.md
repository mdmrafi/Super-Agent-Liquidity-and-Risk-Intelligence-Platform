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
python -m db.seed_users          # idempotent -- 5 mock accounts, one per role
python -m db.migrate_transactions   # idempotent -- replaces each split wholesale
python -m api.main
```

## Schemas (`backend/db/models.py`)

- **`User`** — `username` (unique), `hashed_password` (bcrypt), `role`
  (`agent` | `field_officer` | `provider_ops` | `risk_team` | `admin`), plus
  role-scoping fields: `agent_id`/`area` (which agent an `agent`-role account
  *is*), `provider` (default filter for `provider_ops`).
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

## Roles and dashboards

One primary dashboard per role, matching the app's existing 5 tabs, plus the
read-only Assistant as a shared helper for the operational roles:

| Role | Sees | Notes |
|---|---|---|
| `agent` | Agent view only | Locked to their own `agent_id` — no picker over other agents |
| `field_officer` | Ops/coordination + Assistant | |
| `provider_ops` | Provider ops + Assistant | |
| `risk_team` | Risk/compliance + Assistant | |
| `admin` | All 5 tabs | The only multi-purpose role |

## Demo accounts (`backend/db/seed_users.py`)

Simple, memorable passwords by design — this is mock data behind a
prototype, not a real account system. Still bcrypt-hashed in the database;
shown on the login page itself (`frontend/src/lib/roles.js`'s
`DEMO_ACCOUNTS`) for convenience.

| Role | Username | Password |
|---|---|---|
| Agent | `agent01` | `agent123` |
| Field Officer | `fieldofficer` | `officer123` |
| Provider Ops | `providerops` | `provider123` |
| Risk Team | `riskteam` | `risk123` |
| Admin | `admin` | `admin123` |

## Security note

`MONGODB_URI` and `JWT_SECRET` live only in `.env` (gitignored, never
committed) — `.env.example` documents the shape without real values. If the
Atlas password was ever shared somewhere outside this repo (chat, a ticket,
etc.), rotate it in Atlas' UI; the app only needs `.env` updated to match.
