# Prompt: Stage 2 forecast + cohort + anomaly engine

**Spec section:** Master Specification section 6 (6.1-6.4), section 11 (validation)
**Model:** Claude Sonnet 5
**Timestamp:** 2026-07-11

## Prompt text (verbatim)

> Stage 2 — Forecast + cohort + anomaly engine
> This stage consumes Stage 1's synthetic dataset (schema in section 4.2, with is_injected_anomaly/is_injected_data_fault labels and the calibration/held-out split from 4.1). If that dataset doesn't exist in the repo yet, generate a small sample matching sections 4.2 and 5 first so this stage has something to run against — but flag it clearly as a placeholder, not the real Stage 1 deliverable.
> Build, per section 6 of the master spec:
> - Liquidity forecast (6.1) — per (agent, provider): EWMA burn_rate over a rolling window, project time_to_shortage, confidence that narrows when burn_rate variance is low and data is fresh, widens when the relevant feed is late, missing, or conflicting.
> - Peer-cohort layer (6.2) — cohort_key = (provider, area, hour_bucket, day_type); compute cohort_mean/std of the metric across agents sharing that cohort; compute agent_z. Fewer than 3 peers → fall back to self-history comparison, mark confidence lower.
> - Routing determination (6.3) — implement the routing table as a pure function: cohort_context in → recommended_owner out. High-severity unusual-activity alerts additionally copy to risk_team regardless of cohort_context.
> - Anomaly rule (6.4) — the near-identical-amounts pattern from section 5. Tune thresholds on the calibration split only, lock them, then run once, unmodified, against held-out.
> No "fraud" or "high risk" anywhere — "unusual — requires review" only, paired with confidence and literal evidence numbers. This stage is fully deterministic, no LLM calls — phrasing is Stage 5's job.
> Output contract (Stage 3 builds the formal alert objects from this — match field names exactly): [JSON schema: agent_id, provider, area, timestamp, burn_rate, time_to_shortage_minutes, confidence, confidence_label, cohort_z, cohort_context, is_anomalous, anomaly_evidence, recommended_owner]
> Before calling this stage done, verify:
> - Held-out metrics computed and reported: provider-level demand/balance error, shortage detection lead time, anomaly precision & recall vs is_injected_anomaly, false-positive rate on a normal Eid/salary spike.
> - A manufactured thin-cohort case (< 3 peers) actually falls back to self-history with visibly lower confidence — check real output, don't just trust the code path exists.
> - A manufactured data-fault case actually widens confidence rather than guessing.
> - Hand-check 3-5 outputs against agents you know sit in Scenario A/B/C windows — do the numbers make narrative sense before Stage 3 builds on top of them.
> Log this prompt to prompts/00X-stage2-forecast-cohort-anomaly-engine.md per section 3.1, committed with (or just before) the code it produces.

(Preceded by: "first commit and then move to stage 2" -- the Stage 1 commit, and a
prior exchange resolving a cross-stage gap: Stage 1 had no liquidity-shortage
scenario on a holdout day, needed for this stage's lead-time metric. User chose
to add one to Stage 1 rather than measure on calibration only; see
prompts/001's addendum.)

## What was built

`engine/` package: `data.py` (load + hour_bucket), `liquidity.py` (EWMA burn_rate,
relative safety-threshold time_to_shortage, confidence), `cohort.py` (cohort_z with
self-history fallback, area/provider-wide context resolution), `anomaly.py` (greedy
near-identical-amount detector + calibration grid search), `routing.py` (pure
routing function), `pipeline.py` (orchestration matching the output contract),
`evaluate.py` (section 11 metrics), `main.py` (CLI entry).

Stage 1's dataset already existed in the repo (committed in the prior step), so
no placeholder generation was needed.

## Deviations from the literal spec (flagged, not silent)

- **`provider: null` on shared-cash rows.** The contract has one row shape, but
  catching Scenario A's hidden shortage requires forecasting shared cash
  (agent-level, no provider) alongside each per-(agent, provider) balance
  forecast -- a provider-only forecast would show bKash balance *rising* during
  the exact hours cash is draining. Cash rows use `provider: null`; the field
  set is otherwise identical.
- **`recommended_owner` collapses to `risk_team` for anomalous rows**, dropping
  whatever the liquidity-routing owner would have been. Section 7/8's "+ copy to
  risk/compliance analyst" implies an addition, not a replacement, but the given
  contract has a single owner field with no second slot to carry both. Kept the
  literal contract shape rather than adding a field.
- **Safety threshold is relative, not the flat BDT figure implied by "the
  spec gives no number here."** A fixed threshold either never triggers for
  well-funded agents or false-positives on modestly-funded ones, given how much
  opening balances vary per agent in Stage 1. Used a fraction (0.80 cash / 0.70
  provider) of each agent's own rolling peak balance, computed causally.
- **Cohort stats are pooled, not strict leave-one-out** (includes the row's own
  agent alongside peers) -- a simplification accepted given >=3 peers are
  required before pooled stats are used at all, making the self-inclusion bias
  minor at this dataset's scale.
- **Cross-agent cohort comparisons use `net_change`** (the realized hourly
  balance delta), not the EWMA-smoothed `burn_rate` -- comparing already-smoothed
  values cross-agent would mix unevenly-aged history between agents.

## Bug caught by the required verification checks

The self-history-fallback code path triggered correctly (cohort_context was
right), but confidence was computed in `liquidity.py` *before* `cohort.py` even
determined fallback status -- so "mark confidence lower" was never actually
wired in. First real-output check (thin-cohort case) surfaced a fallback row at
confidence 0.90 ("high"), contradicting the spec directly. Fixed by applying a
0.20 confidence penalty in `pipeline.py` after cohort scoring, then
re-deriving `confidence_label`. Re-verified: 82.5% of fallback rows are now
"low" confidence vs mostly "medium/high" for normal cohort comparisons.

A related issue: the initial flat `CASH_SAFETY_THRESHOLD=30,000` (vs. opening
cash of 200k-400k) meant the shortage-lead-time metric came back
"no_crossing_observed" for both Scenario A and the holdout pressure window --
the engineered ~21-27% depletions never came anywhere near a flat 30,000 floor.
Fixed by switching to the relative-threshold design above; lead time on the
holdout scenario now measures at 143.8 minutes.

## Verification (all four required checks)

- **Held-out metrics**: provider-balance MAE 1,036 BDT/hour (71 cells); shortage
  lead time 143.8 min (agent_11, holdout); anomaly precision 0.75 / recall 0.90
  / F1 0.82 (holdout, locked params); false-positive rate 0.28% on holdout's
  eid day (3/1068); explanation coverage 100%/100%; latency ~12-23s for 7,773
  transactions.
- **Thin-cohort fallback**: 1,997 rows fall back; confidence distribution
  skews low (1648 low / 305 medium / 44 high) vs the general population
  (mostly medium/high) -- visibly lower, not just labeled differently.
- **Data-fault confidence widening**: Scenario C (Rocket, calibration day 6)
  hours average 0.30 confidence vs 0.39 for clean Rocket hours elsewhere.
- **Hand-check narrative sense**: Scenario A (agent_07, bKash, day 8) shows
  bKash's own balance *rising* (cohort_z 1.7-2.2, flagged as unusually high)
  while the same agent's shared-cash row shows deep negative burn_rate and
  time_to_shortage hitting 0 by midday -- exactly the hidden-shortage story,
  routed to field_officer since it's isolated to one agent. Scenario B
  (agent_14, Nagad, day 5) correctly detected as anomalous, evidence populated
  with real numbers, routed to risk_team.
