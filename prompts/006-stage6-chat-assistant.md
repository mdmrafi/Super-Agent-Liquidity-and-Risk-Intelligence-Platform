# Prompt: Stage 6 AI chat assistant

**Spec section:** Master Specification section 10 (AI chat assistant — stretch/build-if-time)
**Model:** Claude Opus 4.8 (orchestration) calling OpenAI `gpt-4o` (the grounded answer call)
**Timestamp:** 2026-07-11

## Prompt text (verbatim)

> Stage 6 — AI chat assistant (build only if time remains)
> This stage reads Stage 2/3's live computed state (open alerts, balances, cohort figures) and answers natural-language questions about it. It never computes a new forecast, severity, or routing decision — it only reports on what's already been decided upstream.
> 1. Retrieval — keep it simple, this system is small enough not to need real search. You have 20 agents, 3 providers, 5 areas — retrieval here means "filter live state to the entities mentioned," not a search index: `retrieve_relevant_state(question)` matches known providers/areas/agent_ids against the question, filters open (non-resolved) alerts to any entity mentioned, defaults to all open alerts sorted by severity desc when none is mentioned, and returns `{open_alerts, balance_snapshot, cohort_summary}`.
> 2. The answer call — same LLM boundary discipline as Stage 5. `answer_chat_query(question, language)` retrieves context; if there are no open alerts it returns a plain templated response with no LLM call; otherwise it calls the LLM with a system prompt that says: "Answer ONLY using the provided context. Never invent a number, provider, or alert not present in it. If the context doesn't answer the question, say so plainly instead of guessing." The empty-context path matters as much as the populated one — a query about a provider with no open alerts should say "no current issues for {provider}," not fabricate one.
> 3. Support these three at minimum: "why is bKash at risk" (filters to provider, grounded summary), "which provider needs attention" (no entity → highest-severity open alert across all), "what should we do next" (surfaces recommended_action + recommended_owner from the relevant open alerts, doesn't invent a new recommendation).
> 4. Minimal UI — a text input and a response area in the dashboard, wired to answer_chat_query. Don't spend time on chat-bubble styling or history/threading.
> Before calling this stage done, verify: all three required queries return grounded, correct answers on real Stage 3 data; a zero-open-alert entity returns the "no current issues" path, not a hallucinated one; an out-of-scope question gets a graceful decline; and nowhere in this stage's code does it call the forecast engine, create an alert, or change a case_status — it's read-only by construction.
> If cutting this short on time, ship just the three required queries with the simple entity-matching rather than open-ended robustness.
> Log this prompt to prompts/00X-stage6-chat-assistant.md per section 3.1, committed with the code it produces.

**Provider note:** kept on OpenAI `gpt-4o` via the standard `openai` SDK, matching
Stage 5, so both LLM stages share one client, one env var (`OPENAI_API_KEY` in the
gitignored `.env`), and one boundary discipline. A fresh Anthropic key
(`hackathon_SUST`) was available and offered as an option, but consistency with the
existing Stage 5 layer was chosen over introducing a second provider + dependency.

## What was built

- `chat/retrieve.py` — `retrieve_relevant_state(question, split)`. Entity matching
  is literal, not learned: case-insensitive substring match for the 3 providers and
  5 areas (longest-name-first for determinism), and a `agent[_ ]?(\d+)` regex for
  agent ids that only accepts ids actually present in the data. Filters
  `case_status != "resolved"` alerts to any mentioned entity; with none mentioned,
  returns every open alert sorted by severity desc (high>medium>low, confidence as
  tiebreaker) so the head of the list is the single most severe open alert. Also
  returns `balance_snapshot` (only when a specific agent is named, read from Stage
  1 balances) and a compact `cohort_summary` (count of cohort_context values).
- `chat/answer.py` — `answer_chat_query(question, language, split)`. Empty-context
  path is templated per language (en/bn/banglish) and **never calls the LLM**. The
  populated path sends a compact projection (11 fields per alert, capped at the top
  20 by severity) with a system prompt forbidding any invented number/provider/
  area/agent/alert and forbidding new recommendations — any "next step" must be an
  alert's own `recommended_action`/`recommended_owner`. It also reuses Stage 5's
  "never say fraud/high risk → say unusual/requires review" constraint and declines
  out-of-scope questions. On any LLM failure it degrades to a grounded restatement
  of the top alert (invents nothing), mirroring Stage 5's boundary catch.
- `api/main.py` — `POST /api/chat` (`{question, lang, split}` → `{answer, lang}`).
- Frontend — `askChat()` in `api.js`, a new `AssistantView.jsx` (text input +
  response area + the three required queries as one-click chips), added as a fourth
  "Assistant" tab in `App.jsx`, with styling in `App.css`. No history/threading —
  a stretch feature earns a stretch-appropriate UI, per the prompt.

## Read-only by construction

`chat/` imports only `api.store` (and calls exclusively its read functions —
`load_alerts`, `list_agents`, `agent_balances`; never `save_alerts`), the
`LANGUAGE_NAMES` constant from `explain`, and the `openai` client. It does not
import the engine, `alerts.lifecycle`, or `alerts.build`. Verified by grep that no
line calls the forecast/cohort/anomaly engine, creates an alert, or assigns
`case_status`. The retrieval read leaves `data/alerts_calibration.json`
byte-for-byte identical (checked before/after).

## Verification (all required checks)

- **Three required queries, real calibration data (live `gpt-4o`)**:
  - *"why is bKash at risk"* → filtered to 109 open bKash alerts, grounded summary
    citing real burn rate (-8,279 BDT/hour) and confidence (35%) — both confirmed
    present in the exact JSON context sent to the model — and the real
    `request_replenishment_support` → `field_officer` routing.
  - *"which provider needs attention"* → no entity matched → returned bKash, the
    provider of the single highest-severity open alert (`agent_11`, high
    liquidity_shortage).
  - *"what should we do next"* → surfaced existing recommended_action/owner per
    alert type (request_replenishment_support for shortages, review_evidence for
    data_quality), invented no new recommendation.
- **Zero-open-alert entity → templated path, no LLM**: every real agent has ≥1
  alert in this dataset, so simulated a provider whose alerts are all resolved and
  patched the client factory to raise if ever called; all three languages returned
  the plain "no open alerts for {entity}" template and the LLM was provably never
  invoked.
- **Out-of-scope decline**: "what is the weather today" → graceful "outside what I
  can help with" in both the direct call and a live HTTP round-trip, never an
  in-character financial answer.
- **LLM-failure fallback**: patched the client to raise; `answer_chat_query`
  returned a grounded one-line restatement of the top open alert only.
- **End-to-end HTTP**: started uvicorn, `POST /api/chat` returned 200 with a
  grounded in-scope answer and a graceful out-of-scope decline.
- **Frontend**: `oxlint` clean on the new files (only pre-existing LanguageContext
  warnings remain); `vite build` succeeds.
