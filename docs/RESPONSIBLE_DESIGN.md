# Responsible-Design Note

*Deliverable for Master Specification §10 (Responsible-design note), §9 (Risk
interpretation rule), and §14 (Constraints and Guardrails). States privacy, human
review, false positives, advisory boundaries, and the actions this prototype
intentionally does **not** perform.*

---

## 1. An anomaly is not proof of fraud

This is enforced in behavior, not just stated. The anomaly detector produces an
**advisory review signal**, never a verdict:

- **Careful language, checked in code.** Alerts of this type are labeled
  *"Unusual activity — requires review."* The bilingual explanation layer's system
  prompt forbids the words "fraud" and "high risk" and substitutes "unusual" /
  "requires review"
  ([explain/explain.py](../explain/explain.py)); `alerts.main` greps all alert
  evidence for banned verdict language and asserts zero matches (check 5).
- **What a flag means:** a cluster of near-identical amounts from a small set of
  accounts in a short window — a *pattern worth a human look*, which on an Eid or
  salary day may be entirely legitimate demand.
- **Evidence + uncertainty on every alert.** Each alert carries a plain-language
  `evidence` array and a `confidence` / `confidence_label`; the Risk view shows
  both. Nothing presents an "anomaly score as proof of fraud" (§7).

## 2. Expected false positives

Measured on the held-out split with locked thresholds:

| Metric | Value |
|---|---|
| Anomaly precision | 0.75 |
| Anomaly recall | 0.90 |
| Anomaly F1 | 0.82 |
| False-positive rate on normal Eid/salary spikes | 0.28% |
| Provider-balance forecast MAE | 1,036 BDT/hour |
| Shortage-detection lead time | 143.8 min (agent_11, holdout) |

Precision 0.75 means **~1 in 4 anomaly flags is expected to be a false positive** —
which is *why* the workflow routes them to a human reviewer rather than acting on
them. Liquidity alerts are additionally **debounced**: a single-hour EWMA blip is
suppressed, requiring 2+ consecutive crossings before firing. On this dataset that
removed ~58 of ~84 high-severity liquidity episodes that were single-hour noise on
agents never touched by any injection ([alerts/build.py](../alerts/build.py)).

## 3. Human-in-the-loop by construction

- **No automatic action.** The prototype never blocks a user, freezes funds,
  accuses an agent, or moves money. `alerts.main` (check 2) greps `alerts/`,
  `engine/`, and `data_generation/` for any `block/freeze/disable/lock (agent|
  account|transact)` code path and asserts there are none.
- **The agent keeps operating.** A "constrained — replenishment requested" display
  status is purely informational; the Agent view's actions are never disabled by it
  ([DisplayStatusBanner.jsx](../frontend/src/components/DisplayStatusBanner.jsx)).
- **Every important alert has an owner, a next step, and a traceable status.**
  Routing is a deterministic function of cohort context; ownership, acknowledgement,
  escalation, and resolution are recorded as an append-only `case_history` (§8, §5
  auditability). Risk analysts review; ops escalates; **no one declares final
  fraud** (§5).

## 4. Provider boundaries & privacy

- **Provider separation.** Each provider's e-money is tracked separately and never
  summed into a single transferable pool. The combined-balance figure in the Agent
  view exists specifically to *debunk* the naive "add it all up" view — the
  per-provider breakdown is one click away with a caption warning that a healthy
  total can hide a shared-cash squeeze. Nothing implies unauthorized conversion
  between provider balances (§4.2, §14).
- **Synthetic identifiers only.** Agent, customer, and transaction ids are
  generated (`agent_07`, `cust_00272`, `txn_000001`). No PIN, OTP, password, private
  key, or real credential is collected, stored, or requested (§14).

## 5. What this prototype intentionally does NOT do

- Execute, settle, reverse, or reconcile any real financial transaction.
- Connect to any production wallet, API, or account.
- Block, freeze, restrict, or accuse any agent or customer.
- Make a final fraud determination or claim regulatory / production readiness.
- Convert or transfer liquidity between providers.

## 6. Known responsibility-relevant gaps (stated honestly)

- **No per-provider access control.** A single dashboard shows all providers'
  alerts to one viewer. In production, a bKash operator must not see another
  provider's confidential alerts; this prototype does not yet model that isolation.
- **`provider_ops` / network-coordination routing is lightly exercised**, because
  the cohort layer rarely classifies pressure as `provider_wide` on this synthetic
  data. "Upcoming pressure automatically visible to provider operators" is therefore
  only partially realized — see the evaluation notes for the recommended
  owner-filtered inbox and provider-scoped view.
- **Single anomaly pattern** — see [DATA_AND_ASSUMPTIONS.md](./DATA_AND_ASSUMPTIONS.md) §4.
