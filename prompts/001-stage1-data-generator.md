# Prompt: Stage 1 data generator

**Spec section:** Master Specification sections 3-5, 14 (Stage 0 repo/tooling context recap, then Stage 1: data model, synthetic data generation, injected scenarios A-D)
**Model:** Claude Sonnet 5
**Timestamp:** 2026-07-11

## Prompt text (verbatim)

> ok, let's work on it later
> now use /karpathy-guidelines to code
> # Super Agent Liquidity & Risk Intelligence Platform — Master Specification (Stage 0)
>
> [... full master specification pasted by the user, sections 1-14, covering: project brief, users & routing targets, repo/tooling setup (prompt-logging convention, self-hosted SonarQube), data model, synthetic data generation, forecasting & detection engine, alert/evidence object, coordination workflow, explanation/language layer, AI chat assistant, validation & metrics, required documentation, guardrails, build order ...]

Followed by two clarifying answers from the user after being asked:
- Stack: **Python**
- Scope for this session: **Stage 1 only** (data generator, not the forecast/anomaly engine)

## What was built

`data_generation/` package: `config.py` (world parameters), `simulate.py` (Poisson/lognormal
baseline transaction generation + balance replay), `scenarios.py` (Scenario A/B/C injection +
general anomaly/data-fault injection), `reconcile.py` (balance-replay verification),
`main.py` (orchestration, writes `data/transactions_calibration.csv` and
`data/transactions_holdout.csv`).

## Deviations from the literal spec (flagged to the user, not silent)

- Added `customer_id`: not in the section 4.2 schema table, but required for section 5's
  anomaly rule ("≤3 distinct accounts"), which is otherwise unimplementable.
- Added `day_type` as a field distinct from `event_flag`: `event_flag` gets overridden to
  `injected_anomaly`/`injected_data_fault` on affected rows, which would erase the day-type
  context section 6.2's `cohort_key` needs. `day_type` always reflects the actual simulated
  day; `event_flag` follows the spec's literal enum.
- Added `split`, `is_injected_anomaly`, `is_injected_data_fault`, `injected_scenario` as
  internal-only ground-truth columns per section 5's own instruction ("tag internally... the
  detector never sees this label").

## Verification

- Reconciliation check (`reconcile.check`) passes with zero errors on the clean ledger
  (7,533 transactions, 20 agents) before Scenario C fault injection is applied.
- Scenario A spot-checked: agent_07's shared cash drops ~21% (346,978 -> 272,914 BDT) within
  the injected pressure window while their bKash balance nearly doubles — confirms the
  "hidden shortage" mechanic (a per-provider view looks healthy while shared cash is stressed).
- Scenario B anomaly burst spot-checked: 5 cash-outs within an 8-minute window, amounts within
  ~2% of each other, from 3 distinct customer_ids — matches section 5's pattern definition.
- Scenario C spot-checked: delayed, duplicated, and null-balance ("corrupted") rows present
  and correctly tagged, applied only after reconciliation passed on the clean ledger.

## Addendum (same session, discovered while starting Stage 2)

Stage 2 needs a liquidity-shortage event on a **holdout** day to measure shortage-detection
lead time against held-out data (section 11) -- Scenario A was calibration-only, so holdout
had nothing to detect. Asked the user; confirmed adding a general (unnamed) liquidity-pressure
injection to a holdout day, same pattern as the existing general anomaly/data-fault instances.
Added `GENERAL_LIQUIDITY_PRESSURE` (agent_11, Nagad, day 12, hours 11-17) to
`data_generation/main.py`. Re-ran the generator, reconciliation still passes (7,694 clean
transactions), and spot-checked the Nagad-only conservation within the window
(+83,690.61 balance exactly mirrors -83,690.61 cash).
