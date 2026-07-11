# Prompt: Stage 5 bilingual explanation layer

**Spec section:** Master Specification section 9 (explanation & language layer)
**Model:** Claude Sonnet 5 (orchestration) calling OpenAI `gpt-4o` (the explanation layer itself, per explicit user instruction -- see below)
**Timestamp:** 2026-07-11

## Prompt text (verbatim)

> Stage 5 — Bilingual explanation layer
> This stage consumes Stage 3's alert objects only (section 7 schema — alert_type, evidence, confidence, confidence_label, cohort_context, severity, recommended_action). It reads that object and produces exactly one thing: a natural-language sentence in the requested language. It computes nothing.
> 1. The boundary, enforced in code, not just convention: explain_alert(alert_object, language: "en" | "bn" | "banglish") -> string. The system prompt must explicitly forbid the model from introducing any number, claim, or severity judgment not already present in alert_object.evidence: "You are a translator, not an analyst. Rephrase the following structured alert into one or two natural sentences in {language}. Use only the facts given in the evidence field. Do not invent numbers, do not add urgency beyond what severity indicates, do not use the words 'fraud' or 'high risk' — use 'unusual' or 'requires review' if referring to anomalies. Structured alert: {alert_object_json}"
> 2. Three languages, one function, one prompt template.
> 3. Validation before this stage is "done": run against 5-6 real Stage 3 alert objects, check every number/fact traces to evidence, check it avoids fraud/high-risk language even on a high-severity anomaly, check Banglish reads as natural code-mixing not literal transliteration.
> 4. Failure handling: fall back to a plain template string (f"{alert_type} alert for {agent_id}: {evidence[0]}") if the LLM call fails or times out.
> 5. Wire it into Stage 4 — replace the placeholder language-toggle function with this real one.
> Log this prompt to prompts/00X-stage5-bilingual-explanation-layer.md, committed with the code it produces.

**Provider note:** mid-session, the user explicitly redirected from Claude/Anthropic to
OpenAI ("use codex api", providing an OpenAI project API key and stating "you have
credits, use any model"). The whole rest of this project's LLM-adjacent tooling
(the `claude-api` skill's own defaults) points at Anthropic models, but this is an
explicit, direct instruction naming a different provider -- honored as written.
Used `gpt-4o` via the standard `openai` Python SDK (`chat.completions.create`).
The key is stored in the repo's already-gitignored `.env` (same pattern as the
21st.dev key from Stage 4), never committed, never printed in full in output.

## What was built

- `explain/explain.py` -- `explain_alert(alert_object, language)`, one function,
  one prompt template per language (the language name is interpolated, not the
  constraint logic), with a broad `except Exception` boundary that degrades to
  the plain template on any failure (network, auth, timeout, malformed response,
  empty completion) -- deliberately broad here since this is the "never let the
  LLM layer block the dashboard" boundary, not a place to be narrowly precise
  about exception types.
- `api/main.py` -- replaced the Stage 4 placeholder `/api/translate` endpoint
  (which took a raw evidence string) with `POST /api/alerts/{alert_id}/explain`
  (loads the real alert object server-side, calls `explain_alert`).
- Frontend: `LanguageContext.jsx` now exposes a cached `explain(alertId, split)`
  keyed by `lang::split::alertId` instead of the old raw-text `t()`; replaced
  `Translated.jsx` (deleted, now orphaned) with `AlertExplanation.jsx`.

## A real architectural correction, not just a swap

Stage 4's placeholder wrapped each **evidence bullet individually** in a
translate-this-string call. Stage 5's `explain_alert` takes the **whole alert
object** and produces one or two holistic sentences (matching section 9's own
example, which synthesizes across evidence + context, not a line-by-line
translation) -- a different shape, not just a different backend. Kept the
evidence array itself always verbatim and untranslated (Stage 4's own explicit
requirement), and added the LLM-derived explanation as a distinct, additional
element on the card. This is the one place this session deviated from "nothing
else in the dashboard should need to change" -- flagged rather than silently
forcing the old per-string shape onto a per-alert function.

## A real scalability bug caught during verification, not before

Initial version fetched the explanation eagerly on every card's mount. The ops
view renders up to 175 alert cards unfiltered -- switching language queued 175+
sequential OpenAI calls against a single-threaded dev backend; the first
explanation didn't resolve in 30 seconds during a live Playwright check. Fixed
by making `AlertExplanation` lazy (click-to-reveal "Explain in plain language"
button; fetches only when actually requested, still refetches on language
change once revealed). Re-verified live: a Bangla explanation for a real alert
now resolves in well under a second and renders correctly in the browser
(Bengali script, no mojibake).

## Also caught: test-data pollution in the previous commit

While investigating a stray "acknowledged" status during this stage's live
verification, found that Stage 4's committed `data/alerts_calibration.json`
included a real state mutation from an earlier Playwright lifecycle test
(`alert_c00175`, acknowledged by `dashboard_user`) that should have been reset
before committing and wasn't. Regenerated clean data via `alerts.main` and
included the fix in this commit.

## Also fixed: `requirements.txt` gaps

`fastapi` and `uvicorn` (added in Stage 4) were never added to
`requirements.txt`; added them alongside `openai` now.

## Verification (all required checks)

- **5-6 real alerts, all three languages**: tested 6 real calibration alerts
  spanning liquidity_shortage (high & low severity), data_quality, and
  unusual_activity (medium & low). Every number in every output traces to the
  alert's literal `evidence` string -- spot-checked BDT amounts, minute counts,
  and percentages against source evidence in all 18 outputs (6 alerts x 3
  languages).
- **High-severity anomaly wording**: no `unusual_activity` alert in either
  split ever reached "high" severity in this dataset (a real characteristic --
  anomaly bursts in this data consistently co-occur with lower confidence, so
  severity, which follows confidence_label for anomalies, never reaches
  "high"). Per the instruction's own "deliberately feed it" framing,
  constructed a synthetic high-severity/high-confidence anomaly
  (6 cash-outs, 24,900 BDT average, 3-minute window) and confirmed all three
  languages say "unusual"/requires review, zero occurrences of "fraud" or
  "high risk" in any of the three outputs.
- **Banglish readability**: outputs read as natural code-mixed Bengali-in-Roman-
  script ("Dekhuna ektu unusual situation asche!", "Ekhn-er burn rate...",
  "Korechhi self history theke compare") -- not literal transliteration and not
  English with isolated Bengali words dropped in.
- **Fallback fires correctly**: mocked the OpenAI client to raise on every call;
  `explain_alert` returned exactly the plain-template string
  (`f"{alert_type} alert for {agent_id}: {evidence[0]}"`), byte-for-byte match
  confirmed programmatically.
- **Live dashboard check**: switched to বাংলা in the running Ops view, clicked
  "Explain in plain language" on a real card, confirmed correct Bengali-script
  rendering with no console errors.
- **Presentation deliverable**: saved to `docs/bilingual-sample.md` -- one
  alert's English/Bengali/Banglish outputs side by side, annotated against the
  situation/evidence/uncertainty/safe-next-step checklist from section 9.
