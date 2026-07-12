"""Stage 6 answer call (spec section 10).

Read-only by construction. This module reports on alerts Stage 2/3 already
decided; it never computes a forecast, severity, or routing decision, never
creates an alert, and never changes a case_status. It touches state only
through `retrieve_relevant_state`, which itself only reads.

Same LLM-boundary discipline as Stage 5: the system prompt forbids the model
from introducing any number, provider, area, agent, or alert not present in the
retrieved context, and forbids inventing a new recommendation -- any "next
step" it surfaces must be an alert's own recommended_action / recommended_owner.
The empty-context path never reaches the model at all: a question about an
entity with no open alerts gets a plain templated "no current issues" reply
rather than a fabricated one.
"""
import json

from openai import OpenAI

from explain.explain import LANGUAGE_NAMES
from chat.retrieve import retrieve_relevant_state

MODEL = "gpt-4o"

SYSTEM_PROMPT_TEMPLATE = (
    "You are a read-only assistant for a mobile-money agent liquidity and risk "
    "dashboard. Answer ONLY using the JSON context provided (open alerts, an "
    "optional balance snapshot, and a cohort summary). "
    "Never invent a number, provider, area, agent, or alert that is not present "
    "in the context. Do not compute a new forecast, severity, or recommendation: "
    "if you mention what to do next, it must be an alert's own recommended_action "
    "and recommended_owner exactly as given. "
    "If the context does not answer the question, say so plainly instead of "
    "guessing. If the question is not about these agents, providers, areas, "
    "alerts, or balances (for example small talk, weather, or general knowledge), "
    "politely decline as outside what you can help with -- do not answer it. "
    "Never use the words 'fraud' or 'high risk'; say 'unusual' or 'requires "
    "review'. Reply in {language}, in two to four sentences, no preamble."
)

# Compact projection sent to the model: enough to answer the three required
# queries, small enough to keep token use sane even with many open alerts.
CONTEXT_ALERT_FIELDS = (
    "alert_id", "agent_id", "provider", "area", "alert_type", "severity",
    "confidence_label", "evidence", "cohort_context",
    "recommended_action", "recommended_owner",
)
MAX_CONTEXT_ALERTS = 20

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _compact(alert):
    return {k: alert.get(k) for k in CONTEXT_ALERT_FIELDS}


def _llm_context(context):
    return {
        "open_alert_count": len(context["open_alerts"]),
        "open_alerts": [_compact(a) for a in context["open_alerts"][:MAX_CONTEXT_ALERTS]],
        "balance_snapshot": context["balance_snapshot"],
        "cohort_summary": context["cohort_summary"],
    }


def _subject(mentioned):
    return mentioned["provider"] or mentioned["area"] or mentioned["agent_id"] or None


def _no_issues_message(context, language):
    """Templated empty-context reply -- no LLM call. Names the entity if one was
    mentioned so it never sounds like it fabricated a scope."""
    subject = _subject(context["mentioned"])
    if language == "bn":
        who = f"{subject}-এর জন্য" if subject else "এই মুহূর্তে"
        return f"{who} কোনো খোলা সতর্কতা নেই — এখন আলাদা করে কিছু করার দরকার নেই।"
    if language == "banglish":
        who = f"{subject}-er jonno" if subject else "Ekhon"
        return f"{who} kono open alert nei — akhon alada kore kichu korar dorkar nei."
    who = f"for {subject}" if subject else "right now"
    return f"There are no open alerts {who} — nothing needs attention at the moment."


def _grounded_fallback(context, language="en"):
    """Used only when the LLM call itself fails (network, auth, timeout, empty
    completion). Still strictly grounded -- it restates the top open alert's own
    fields, inventing nothing."""
    top = context["open_alerts"][0]
    provider = f" ({top['provider']})" if top.get("provider") else ""
    count = len(context["open_alerts"])
    if language == "bn":
        return (
            f"{count}টি খোলা সতর্কতা আছে। সবচেয়ে গুরুত্বপূর্ণটি "
            f"{top.get('agent_id')}{provider}-এর {top.get('severity')} "
            f"{top.get('alert_type')}। প্রস্তাবিত পদক্ষেপ: "
            f"{top.get('recommended_action')}; দায়িত্বে {top.get('recommended_owner')}।"
        )
    if language == "banglish":
        return (
            f"{count}ta open alert ache. Shobcheye guruttopurno holo "
            f"{top.get('agent_id')}{provider}-er {top.get('severity')} "
            f"{top.get('alert_type')}. Porer podokkhep: "
            f"{top.get('recommended_action')}; dayitte {top.get('recommended_owner')}."
        )
    return (
        f"{count} open alert(s). Highest severity: "
        f"{top.get('severity')} {top.get('alert_type')} for {top.get('agent_id')}{provider}. "
        f"Recommended action: {top.get('recommended_action')} by {top.get('recommended_owner')}."
    )


def answer_chat_query(
    question,
    language="en",
    split="calibration",
    scope_provider=None,
    scope_agent_id=None,
    scope_area=None,
    scope_role=None,
):
    """Answer a natural-language question about current liquidity/risk state.

    language: 'en' | 'bn' | 'banglish'. Returns a string. Never mutates state.
    """
    context = retrieve_relevant_state(
        question,
        split,
        scope_provider=scope_provider,
        scope_agent_id=scope_agent_id,
        scope_area=scope_area,
        scope_role=scope_role,
    )

    if not context["open_alerts"]:
        return _no_issues_message(context, language)

    language_name = LANGUAGE_NAMES.get(language, language)
    try:
        client = _get_client()
        response = client.with_options(timeout=12.0).chat.completions.create(
            model=MODEL,
            max_tokens=350,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(language=language_name)},
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\n"
                        f"Context (JSON):\n{json.dumps(_llm_context(context), ensure_ascii=False)}"
                    ),
                },
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        return text or _grounded_fallback(context, language)
    except Exception:
        # Never let the LLM layer break the dashboard -- degrade to a grounded
        # restatement of the top alert. Broad catch is intentional at this
        # boundary, as in Stage 5's explain_alert.
        return _grounded_fallback(context, language)
