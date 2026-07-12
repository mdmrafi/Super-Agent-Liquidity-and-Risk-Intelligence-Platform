# Super Agent — Liquidity & Risk Intelligence Platform

A synthetic, multi-provider **liquidity, anomaly, and coordination** prototype for
mobile-money (MFS) agents in Bangladesh. It forecasts liquidity pressure, flags
unusual activity with evidence, and routes important cases through an auditable
human-review workflow.

> **Not connected to real money.** All data is fully synthetic. The prototype never
> touches a real wallet, settles a transaction, blocks an agent, or makes a fraud
> determination. See [Responsible design](#responsible-design--boundaries).

---

## What it does

- Tracks **shared physical cash** and **per-provider e-money** (bKash / Nagad /
  Rocket) separately — a healthy combined total can still hide a single-pool
  shortage.
- **Forecasts** which pool will run short and roughly **when**, with a confidence
  level that drops when data is late, missing, or conflicting.
- **Detects unusual activity** (near-identical repeated amounts from a few accounts
  in a short window) and shows *why* it was flagged — in careful,
  "requires review" language, never "fraud".
- Routes important alerts through **ownership, acknowledgement, escalation, and a
  visible resolution status**, with an append-only audit trail and case notes.
- Explains any alert in **English / বাংলা / Banglish** via an LLM, with a grounded
  template fallback so the dashboard never blocks on the model.
- Enforces **provider / area / agent boundaries** server-side (JWT + scope rules),
  so a provider operator never sees another pool's data.

## Architecture

💾 SYSTEM ARCHITECTURE
│
├── [Stage 1 · data_generation/]
│   └── ⚙️ simulate + inject scenarios (A, A2, B, C, D)
│       └── ───► [transactions CSV (per split)]
│                    │
│                    ├───► [Stage 2 · engine/]
│                    │     ├── ⚙️ liquidity forecast (EWMA burn_rate) ──┐
│                    │     ├── ⚙️ cohort z-score (peer comparison) ─────┤
│                    │     └── ⚙️ anomaly detection (near-identical) ────┤
│                    │                                                   ▼
│                    │                                       [forecast JSON]
│                    │                                               │
│                    │                                               ▼
│                    │                                     [Stage 3 · alerts/]
│                    │                                       └── ⚙️ build alerts
│                    │                                           └── ⚙️ lifecycle
│                    │                                               │
│                    │                                               ▼
│                    │                                         [alerts JSON]
│                    │                                               │
│                    ├───► [Stage 2b · ml/ (comparison only)]        │
│                    │     └── ⚙️ HistGradientBoosting residual      │
│                    │                                               │
│                    └─────────────────────────────────┐             │
│                                                      ▼             ▼
├── [API · api/ + auth/ + db/ + obs.py]             ┌──────────────────┐
│   ├── 📄 store.py ◄───────────────────────────────┤ file-backed reads│
│   │     │                                         └──────────────────┘
│   │     ▼
│   ├── 🔑 JWT + scope.py (role/area boundaries) ◄─── [MongoDB (users + txns)]
│   │     │
│   │     ▼
│   ├── 🧠 explain/ + chat/ (OpenAI + fallback) ───┐
│   │                                               │
│   └──  request logging + /api/health            │
│                                                   │
│                                                   ▼
└── [Frontend · web/ (role dashboards)] ◄───────────┘
    └──  Agent cockpit
          ├──  Network Command
          ├──  Provider Command
          ├──  Risk Command
          └──  AI Assistant

The file pipeline (`data_generation/` → `engine/` → `alerts/`) is deterministic and
reproducible from one seed; the CSV/JSON artifacts are the source of truth the API
reads. MongoDB holds accounts and a queryable mirror of the ledger.

---

## Submission checklist (Master Spec §16)

### ✅ 1. At least two provider contexts represented distinctly
Three providers — **bKash, Nagad, Rocket** — modelled and tracked separately end to
end: distinct market-share weights, per-provider balances, per-provider alerts, and
provider-scoped operator accounts that can only see their own float.
→ [`db/models.py`](backend/db/models.py) (`MFSProvider`),
[`data_generation/config.py`](backend/data_generation/config.py) (`PROVIDER_WEIGHTS`),
[`api/store.py`](backend/api/store.py) (`agent_balances`),
[`auth/scope.py`](backend/auth/scope.py) (`project_balance`).

### ✅ 2. Shared cash and provider-specific balances demonstrated
`agent_balances` returns the **shared physical cash** drawer plus a separate
`providers{}` map of each provider's e-money, rendered side by side in the Agent
cockpit. Two injected scenarios prove the "healthy total hides a shortage" idea from
both directions: **A** (shared cash drains while a provider looks fine) and **A2** (a
provider's e-money drains while shared cash rises to offset).
→ [`api/store.py`](backend/api/store.py),
[`web/src/pages/AgentCockpit.jsx`](web/src/pages/AgentCockpit.jsx),
[`docs/DATA_AND_ASSUMPTIONS.md`](docs/DATA_AND_ASSUMPTIONS.md) (§1 scenario table).

### ✅ 3. Forward-looking liquidity insight demonstrated
An EWMA model produces a `burn_rate` (BDT/hour), a `time_to_shortage_minutes`
estimate against a relative safety threshold, and a `confidence`, per shared-cash
and per-provider series. Measured **shortage-detection lead time: 152 minutes** on
the held-out split. A separate ML residual model is reported as a comparison figure
only (never drives alerts).
→ [`engine/liquidity.py`](backend/engine/liquidity.py),
[`ml/train.py`](backend/ml/train.py),
[`engine/evaluate.py`](backend/engine/evaluate.py).

### ✅ 4. At least one anomaly category demonstrated with evidence
Near-identical repeated amounts from a few accounts in a short window (a
structuring-style pattern). Every flag carries plain-language evidence, e.g.
*"4 cash_outs, avg 5,211 BDT, 2 account(s), 8-minute window"*. Thresholds are
grid-calibrated on the calibration split and locked before held-out evaluation.
→ [`engine/anomaly.py`](backend/engine/anomaly.py) (Scenario B: agent_14 / Nagad).

### ✅ 5. Human-review and careful risk language included
Anomaly alerts are labelled **"Unusual activity — requires review,"** never fraud.
The build pipeline greps all alert evidence for banned verdict language and asserts
zero matches; the LLM explanation/chat system prompts forbid "fraud" / "high risk".
No code path blocks, freezes, or restricts an agent (asserted in the build checks).
→ [`alerts/main.py`](backend/alerts/main.py) (`check_no_banned_language`,
restriction-path grep), [`explain/explain.py`](backend/explain/explain.py),
[`docs/RESPONSIBLE_DESIGN.md`](docs/RESPONSIBLE_DESIGN.md).

### ✅ 6. One alert demonstrates routing, ownership, ack/escalation, and resolution
`alert_c00107` is walked deterministically through the **full coordination
lifecycle** and persisted into the shipped data: routed to a role → **owner assigned**
(stable user id + reason) → acknowledged → escalated → **reassigned** → resolved.
Every step is an append-only `case_history` event recording previous owner, new
owner, actor, timestamp, and reason; free-text case notes are supported too.
Assignment is authenticated and boundary-checked (assignee must be in-scope).
→ [`alerts/lifecycle.py`](backend/alerts/lifecycle.py),
[`api/main.py`](backend/api/main.py) (`/assign`, `/assignees`, `/notes`),
[`auth/scope.py`](backend/auth/scope.py) (`require_assignment`),
[`docs/coordinated-case-example.md`](docs/coordinated-case-example.md).

### ✅ 7. Repository, data, README, and architecture complete
Backend (`backend/`), canonical frontend (`web/`), deterministic data + regeneration
commands, this README with the architecture diagram above, and a `docs/` set
covering data, responsible design, auth, reliability, and worked examples.
→ [Run it](#run-it), [`docs/`](docs/).

### ✅ 8. At least three metrics measured and explained
Seven measured metrics, reproducible via `python -m engine.main` (analytical) and a
live benchmark (latency) — see [Key metrics](#key-metrics).

### ✅ 9. Failure, uncertainty, and false-positive considerations shown
Confidence drops on late/duplicated/null data; liquidity alerts are **debounced**
(2+ consecutive crossings) to suppress single-hour noise; expected
**false-positive rate on normal Eid spikes is 0.137%** and anomaly precision 0.727
(≈1 in 4 flags is a false positive — which is *why* they go to a human). A dedicated
`data_quality` alert surfaces observable feed defects, and the LLM layer degrades to
a grounded fallback on failure.
→ [`engine/liquidity.py`](backend/engine/liquidity.py) (`_confidence`),
[`docs/RESPONSIBLE_DESIGN.md`](docs/RESPONSIBLE_DESIGN.md) §2,
[`docs/RELIABILITY_AND_OBSERVABILITY.md`](docs/RELIABILITY_AND_OBSERVABILITY.md) §4.

### ✅ 10. Safety, privacy, boundaries, and limitations stated
Synthetic identifiers only (no PIN/OTP/credential collected); provider/area/agent
isolation enforced server-side; an explicit list of what the prototype intentionally
does **not** do; and stated limitations (synthetic scale, single anomaly pattern,
prototype auth).
→ [`docs/RESPONSIBLE_DESIGN.md`](docs/RESPONSIBLE_DESIGN.md) §4–§6,
[`docs/DATA_AND_ASSUMPTIONS.md`](docs/DATA_AND_ASSUMPTIONS.md) §4.

---

## Key metrics

Measured on the held-out split with locked thresholds (analytical) and against the
running server (latency). Full context in
[`docs/RESPONSIBLE_DESIGN.md`](docs/RESPONSIBLE_DESIGN.md) §2 and
[`docs/RELIABILITY_AND_OBSERVABILITY.md`](docs/RELIABILITY_AND_OBSERVABILITY.md).

| Metric | Value |
|---|---|
| Anomaly precision / recall / F1 (held-out) | 0.727 / 0.800 / 0.762 |
| False-positive rate on normal Eid spikes | 0.137% |
| Provider-balance forecast MAE | 665 BDT/hour |
| Shortage-detection lead time | 152 min (agent_11, held-out) |
| Alert explanation coverage (evidence + confidence) | 100% |
| `GET /api/alerts` latency (227 alerts) | avg 11.5 ms · p95 12.1 ms |
| Batch pipeline | ~63 s for 16,046 transactions |

---

## Run it

Ports come from the repo-root `.env` (`BACKEND_PORT`, `FRONTEND_PORT`); see
[`.env.example`](.env.example). MongoDB/JWT setup and demo accounts are in
[`docs/MONGODB_AND_AUTH.md`](docs/MONGODB_AND_AUTH.md).

```powershell
# Backend (FastAPI)
cd backend
pip install -r requirements.txt
.\.venv\Scripts\python.exe -m db.seed_users          # idempotent demo accounts
.\.venv\Scripts\python.exe -m db.migrate_transactions
.\.venv\Scripts\python.exe -m api.main               # serves on BACKEND_PORT

# Frontend (canonical: web/)
cd ..\web
npm install
npm run dev                                          # serves on FRONTEND_PORT, proxies /api
```

Regenerate the synthetic dataset and analytics deterministically (seed `42`):

```powershell
cd backend
.\.venv\Scripts\python.exe -m data_generation.main   # transactions_{split}.csv
.\.venv\Scripts\python.exe -m engine.main            # forecast_{split}.json + printed metrics
.\.venv\Scripts\python.exe -m alerts.main            # alerts_{split}.json + build checks
```

### Verify

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v   # 16 tests
cd ..\web
npm run build
```

Demo accounts (one per role; simple passwords by design — mock data behind a
prototype): `agent01` / `fieldofficer` / `areateam` / `providerops` / `riskteam` /
`admin`. Full table in [`docs/MONGODB_AND_AUTH.md`](docs/MONGODB_AND_AUTH.md).

---

## Responsible design & boundaries

This prototype produces **advisory review signals, not verdicts.** It does not
execute, settle, or reverse any transaction; does not connect to any production
wallet or account; does not block, freeze, or accuse any agent or customer; does not
convert liquidity between providers; and does not make a final fraud determination.
All identifiers are synthetic. Details and measured false-positive expectations are
in [`docs/RESPONSIBLE_DESIGN.md`](docs/RESPONSIBLE_DESIGN.md).

## Documentation

| Doc | Contents |
|---|---|
| [`docs/DATA_AND_ASSUMPTIONS.md`](docs/DATA_AND_ASSUMPTIONS.md) | Synthetic data, injected scenarios A/A2/B/C/D, sourced vs. assumed values, limitations |
| [`docs/RESPONSIBLE_DESIGN.md`](docs/RESPONSIBLE_DESIGN.md) | Careful language, measured metrics, human-in-the-loop, provider boundaries, what it does *not* do |
| [`docs/RELIABILITY_AND_OBSERVABILITY.md`](docs/RELIABILITY_AND_OBSERVABILITY.md) | Structured logging, `/api/health`, latency, degraded-run trace |
| [`docs/MONGODB_AND_AUTH.md`](docs/MONGODB_AND_AUTH.md) | MongoDB/Beanie schemas, JWT auth, role scopes, demo accounts |
| [`docs/coordinated-case-example.md`](docs/coordinated-case-example.md) | The end-to-end ownership/lifecycle walkthrough for `alert_c00107` |
| [`docs/bilingual-sample.md`](docs/bilingual-sample.md) | English / বাংলা / Banglish alert example |

> `web/` is the canonical frontend. `frontend/` is a superseded earlier UI, kept for
> reference. AI-assisted development is logged in [`/prompts`](prompts/README.md).
