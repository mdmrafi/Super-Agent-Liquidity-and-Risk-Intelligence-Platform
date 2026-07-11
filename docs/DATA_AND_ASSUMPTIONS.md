# Data & Simulation Note

*Deliverable for Master Specification §9 (Data and Assumptions) and §10 (Data and simulation note).*

All data in this project is **fully synthetic**. No production API, real customer
identity, real balance, or real transaction account is used or accessed
(§6 out-of-scope, §14 guardrails). The generator is deterministic — one command
reproduces every byte:

```bash
python -m data_generation.main      # writes data/transactions_{calibration,holdout}.csv
python -m engine.main               # writes data/forecast_{split}.json
python -m alerts.main               # writes data/alerts_{split}.json
```

Reproducibility is fixed by `RANDOM_SEED = 42` in
[data_generation/config.py](../data_generation/config.py).

---

## 1. How the data was created

**World.** 20 agents across 5 areas (4 agents/area, round-robin), each serving 3
providers — **bKash, Nagad, Rocket**. 30 calendar days starting 2026-01-01,
split **21 calibration + 9 holdout** days. Day types are assigned deterministically
(not random) so the mix is documented: calibration = 15 normal / 4 salary / 2 Eid;
holdout = 5 normal / 2 salary / 2 Eid.

**Transaction stream.** For each agent, [simulate.py](../data_generation/simulate.py)
draws an hourly Poisson transaction count from a base of ~13 txns/agent/day, shaped
by an hourly demand curve (lunch + evening peaks) and scaled 3–5× on salary/Eid
days. Each transaction is a `cash_in` or `cash_out` (ratio ~1.12:1), amount drawn
from a lognormal (median 2,100 BDT), with a 3% failure rate and a customer id drawn
from a 400-id rotating pool per agent.

**Balances & reconciliation.** Opening cash (200k–400k BDT) and per-provider
e-money (100k–250k BDT) are replayed transaction-by-transaction into
`agent_cash_before/after` and `agent_provider_balance_before/after`. A
`cash_out` drains **shared physical cash** and raises that provider's e-money;
`cash_in` does the reverse. [reconcile.py](../data_generation/reconcile.py)
asserts the replay invariant holds on the **clean** ledger before any data faults
are applied.

**Injected scenarios (§5, §11).** Labeled ground truth is injected on top of the
clean stream so the analytics can be measured:

| Scenario | What it is | Where | Rows |
|---|---|---|---|
| **A** — hidden shortage | cash-out burst on one provider drains shared cash while that provider's own balance looks healthy | agent_07 / bKash, day 8 | 39 |
| **B** — pressure + anomaly | a liquidity burst **and** a near-identical-amount anomaly on the same agent/day | agent_14 / Nagad, day 5 | 37 |
| **C** — data inconsistency | delayed / duplicated / null-balance rows in one provider's feed for one day (applied *after* reconciliation, deliberately breaking the invariant) | Rocket, day 6 | 46 |
| **D** — coordination | routing / case-lifecycle only; needs no injected data | see below | — |
| General anomaly bursts | 4 extra labeled anomalies across both splits | agents 02/09/03/18 | included in 25 anomaly rows |
| General data faults | 2 extra provider-feed faults | bKash day 3, Nagad day 14 | included in 449 fault rows |
| General liquidity pressure | a holdout-day shortage so held-out lead-time is measurable | agent_11 / Nagad, day 12 | — |

**Totals:** calibration 5,087 txns (15 anomaly rows, 160 data-fault rows);
holdout 2,686 txns (10 anomaly rows, 289 data-fault rows).

**Scenario D is a real, *visible* artifact, not just a runtime check.**
[alerts/main.py](../alerts/main.py) deterministically walks one alert
(`alert_c00098`, agent_14's shared-physical-cash shortage) through the full
coordination lifecycle (new → acknowledged → escalated → resolved) and **persists**
it into `data/alerts_calibration.json`. Every other alert stays at
`case_status: "new"` (raw detector output). See
[coordinated-case-example.md](./coordinated-case-example.md).

---

## 2. Schema — mapping to §9's expected fields

Every field §9 lists is present in `data/transactions_{split}.csv`:

| §9 expects | Column(s) |
|---|---|
| agent & provider IDs | `agent_id`, `provider` |
| area, time | `area`, `timestamp` |
| transaction type, amount, status | `txn_type`, `amount`, `status` |
| **opening and current balances** | `agent_cash_before` / `agent_cash_after`, `agent_provider_balance_before` / `agent_provider_balance_after` |
| event flags | `event_flag`, `is_injected_anomaly`, `is_injected_data_fault`, `injected_scenario` |
| case status | `case_status` |

Additional analytical fields are added downstream (never in the raw ledger):
Stage 2 forecast rows carry `burn_rate`, `time_to_shortage_minutes`, `confidence`,
`cohort_z`, `cohort_context`, `is_anomalous`; Stage 3 alerts add
`liquidity_type` (`physical_cash` | `provider_emoney`), `recommended_owner` (who
acts), `audience` (who may see it — physical cash is agent-side only, e-money also
reaches `provider_ops`), `recommended_action`, `case_history`.

---

## 3. Sourced vs. assumed

**Anchored to Bangladesh Bank MFS statistics (Oct 2023):** ~11–13 transactions per
agent per day; cash-in:cash-out ≈ 1.12:1; median transaction ≈ 2,100 BDT.

**Assumptions (not sourced — flagged `# assumption:` in code):** provider
market-share weights (bKash 0.50 / Nagad 0.33 / Rocket 0.17); the 3–5× day-type
multiplier; the hourly demand shape; lognormal sigma (0.7); 3% failure rate;
opening-balance ranges; 400-id customer pool; and all liquidity/cohort/anomaly
thresholds except the anomaly-pattern grid, which is *calibrated* against labels
(see [RESPONSIBLE_DESIGN.md](./RESPONSIBLE_DESIGN.md)).

---

## 4. Limitations

- **Synthetic, small-scale:** 20 agents × 30 days. Distributions are plausible but
  not fitted to a real institution; absolute BDT figures are illustrative.
- **Anomaly coverage is one pattern:** near-identical repeated amounts from few
  accounts in a short window. Velocity spikes, transaction-splitting, and circular
  flows are *not* separately modeled (§5 requires "at least one"; this meets it).
- **Cohort layer rarely reaches `provider_wide`/`area_wide`** on this data, so the
  `provider_ops` / `area_team` routing destinations fire very rarely — a real
  characteristic of the generated distributions, not a bug, but it means those
  coordination paths are lightly exercised in the demo.
- **Data faults are injected as export-time corruption** on a copy of the clean
  ledger; they intentionally break reconciliation and must never be fed back into
  `reconcile.check()`.
- **Split discipline:** anomaly thresholds are tuned on calibration only, locked,
  and run unmodified on holdout — holdout is never used for tuning.
