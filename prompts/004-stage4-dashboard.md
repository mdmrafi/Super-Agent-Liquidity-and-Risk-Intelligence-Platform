# Prompt: Stage 4 dashboard — agent / ops / risk views

**Spec section:** Master Specification section 2 (stakeholders), 7 (alert/evidence object), 8 (coordination workflow), section 10 of the build order (dashboard)
**Model:** Claude Sonnet 5
**Timestamp:** 2026-07-11

## Prompt text (verbatim)

> Stage 4 — Dashboard: agent / ops / risk views
> This stage consumes Stage 3's alert objects only (section 7 schema) — no recomputation of evidence, confidence, or routing in the frontend. If Stage 3 output doesn't exist yet, generate a handful of sample alert objects matching that schema to build against, clearly flagged as placeholder data.
> 1. Three views, matching section 2's stakeholders: Agent view (combined cash + per-provider balances, display_status banner, alerts affecting this agent), Ops/coordination view (filterable alert list, owner + escalation path + status, acknowledge/escalate/resolve wired to Stage 3's lifecycle functions), Risk/compliance view (unusual_activity only, evidence and confidence prominent, review or escalate only -- no verdict action).
> 2. Every alert card, every view, must show: evidence array verbatim; confidence_label paired with the raw number; cohort_context rendered plainly ("similar to 6 nearby agents" vs "isolated to this agent"), not the raw enum; recommended_owner, recommended_action; case_status and a timeline from case_history.
> 3. The hidden-shortage reveal -- combined balance total first, every balance card expandable into per-provider breakdown, no pre-flattening.
> 4. display_status handling: "constrained" shows a visibly urgent banner; every normal agent action stays fully clickable; no screen disables/greys out/gates any transaction flow because of this field. Test this explicitly.
> 5. Optional area/hotspot view (cohort_z-based) -- skip if time is tight, not load-bearing.
> 6. Filters -- provider, agent, area, time -- at minimum on the ops view.
> 7. Language selector now (English / বাংলা / Banglish), wired to a placeholder function returning raw evidence untranslated; Stage 5 swaps the implementation.
> 8. Legible over flashy -- clean table with clear evidence text beats a chart-heavy dashboard.
> Before calling this stage done, verify: all three views render from Stage 3's real alert objects, not hardcoded mockup data; the hidden-shortage drill-down actually works on a Scenario A alert; click through every normal agent action while a "constrained" alert is active and confirm nothing is blocked; filters actually filter, tested on at least two different provider/area combinations; screenshot all three views for the final presentation deck.
> Log this prompt to prompts/00X-stage4-dashboard.md per section 3.1, committed with the code it produces.

Preceded by a stack discussion: initially proposed Streamlit (fastest path in pure
Python); user asked to switch to React + Vite instead and asked for my opinion
first. Recommended React+Vite for presentation polish, with a thin FastAPI
backend to genuinely wire lifecycle actions to Stage 3's real Python functions
(rather than reimplementing the transitions in JS) -- confirmed with the user
before building. Also installed the 21st.dev CLI/skills mid-session at the
user's request (see the API-key setup exchange in conversation; key stored in
the repo's already-gitignored `.env`, never committed).

## What was built

- `api/` -- FastAPI backend: `store.py` (file-backed alert read/write, balance
  derivation from Stage 1 raw CSVs), `main.py` (REST endpoints: `/api/meta`,
  `/api/alerts` with filters, `/api/agents/{id}/balances`,
  `/api/alerts/{id}/{acknowledge,escalate,resolve}` calling the real
  `alerts/lifecycle.py` functions and persisting back to
  `data/alerts_*.json`, `/api/translate` placeholder).
- `frontend/` -- React + Vite app: three views (`AgentView`, `OpsView`,
  `RiskView`), a shared `AlertCard` with every mandatory explainability
  field, an expandable `BalanceCard` (the hidden-shortage reveal), a
  `DisplayStatusBanner` (purely informational, wired to nothing else),
  `Filters` (provider/agent/area/date range, ops view), a language toggle
  (EN/বাংলা/Banglish) wired to the placeholder `/api/translate` endpoint.

Stage 3's output already existed in the repo, so no placeholder data was
needed.

## Deviations from the literal spec (flagged, not silent)

- **Added `cohort_peer_count`** to both Stage 2's output contract
  (`engine/pipeline.py`) and Stage 3's alert object
  (`alerts/build.py`) -- neither literal schema includes it, but this
  stage's own instruction gives a concrete example ("similar to 6 nearby
  agents") that requires a real number, and `cohort.py` was already
  computing it internally without surfacing it. Purely additive; regenerated
  Stage 2 and Stage 3 output and reran all of their existing verification
  checks -- unchanged (same counts, same pass/fail), confirming this didn't
  touch any actual logic.
- **Risk view's action vocabulary** is literally limited to
  acknowledge/escalate (no resolve button ever renders there) via
  `availableActions`, per "review or escalate, nothing else." Resolving
  still happens through the ops view once a case has been escalated to the
  right team -- consistent with a real handoff workflow, not a missing
  feature.
- **Skipped the optional area/hotspot view** (section 5's own suggestion),
  given time and that everything else was already substantial. Nothing else
  was cut.

## Verification (all required checks, driven live with Playwright, not just read from code)

No `chromium-cli` available in this environment; used the Playwright Node
API directly per the `run` skill's fallback guidance, from a throwaway
scratchpad script (not committed).

- **Real data, not mocks**: ops view showed 175 alerts unfiltered, exactly
  matching `data/alerts_calibration.json`'s real count; filtering to
  `provider=bKash` correctly dropped it to 109, then adding `area=Zindabazar`
  to 25 -- two different filter combinations, both correct.
- **Hidden-shortage drill-down**: clicking the combined balance on agent_07
  (Scenario A) revealed exactly 4 rows (cash + 3 providers); the first alert
  listed was the real Scenario A liquidity_shortage alert
  (`time_to_shortage 0 minutes`, `confidence 75%`, cohort rendered as
  "Isolated to this agent — compared against 3 similar agents, none show the
  same pattern").
- **display_status never blocks anything**: with agent_07's constrained
  banner visibly showing, all 4 "Agent actions" buttons measured
  `disabled: false` via Playwright (not just visual inspection), and
  clicking one produced its visible response.
- **Lifecycle wiring is real**: clicking "Acknowledge" in the ops view
  transitioned `case_status` from `new` to `acknowledged` and grew
  `case_history` from 1 to 2 entries -- round-tripped through the actual
  FastAPI endpoint into the real `alerts/lifecycle.py` function and back.
- **Language-neutral verdict check carries through**: risk view showed 4
  `unusual_activity` alerts, all labeled "Unusual activity — requires
  review," never "fraud" or "high risk."
- **Console errors**: none, across the full driven session.
- Screenshots saved to `docs/screenshots/` (agent view collapsed/expanded,
  Scenario A view, ops view, risk view) for the presentation deck.
