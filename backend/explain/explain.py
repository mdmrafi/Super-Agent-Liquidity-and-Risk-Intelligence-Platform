"""Stage 5 bilingual explanation layer (spec section 9).

explain_alert() is a translator, not an analyst: it turns an already-computed
Stage 3 alert object into one or two natural-language sentences in the
requested language. It computes nothing -- severity, confidence, routing, and
evidence all come from the alert object exactly as Stage 2/3 produced them.
Consumes only alert_type, evidence, confidence, confidence_label,
cohort_context, severity, recommended_action, per this stage's own scope.
"""
import json

from openai import OpenAI

MODEL = "gpt-4o"

LANGUAGE_NAMES = {
    "en": "English",
    "bn": "Bengali (বাংলা, Bengali script)",
    "banglish": "Banglish (Bengali spoken naturally, written in Roman/Latin script with "
                "natural English code-mixing -- not a literal transliteration and not "
                "plain English with a few Bengali words dropped in)",
}

SYSTEM_PROMPT_TEMPLATE = (
    "You are a translator, not an analyst. Rephrase the following structured alert "
    "into one or two natural sentences in {language}. Use only the facts given in "
    "the evidence field. Do not invent numbers, do not add urgency beyond what "
    "severity indicates, do not use the words 'fraud' or 'high risk' -- use "
    "'unusual' or 'requires review' if referring to anomalies."
)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


_FALLBACK_LABELS = {
    "bn": {
        "liquidity_shortage": "তারল্য সংকট",
        "unusual_activity": "অস্বাভাবিক কার্যকলাপ",
        "data_quality": "ডেটার মান",
    },
    "banglish": {
        "liquidity_shortage": "liquidity shortage",
        "unusual_activity": "unusual activity",
        "data_quality": "data quality",
    },
}


def _fallback_explanation(alert, language="en"):
    evidence = alert["evidence"][0]
    if language == "bn":
        label = _FALLBACK_LABELS["bn"].get(alert["alert_type"], alert["alert_type"])
        return f"{alert['agent_id']}-এর জন্য {label} সতর্কতা। প্রমাণ: {evidence}"
    if language == "banglish":
        label = _FALLBACK_LABELS["banglish"].get(alert["alert_type"], alert["alert_type"])
        return f"{alert['agent_id']}-er jonno {label} alert. Proman: {evidence}"
    return f"{alert['alert_type']} alert for {alert['agent_id']}: {evidence}"


def _alert_facts(alert):
    return {
        "alert_type": alert["alert_type"],
        "severity": alert["severity"],
        "evidence": alert["evidence"],
        "confidence": alert["confidence"],
        "confidence_label": alert["confidence_label"],
        "cohort_context": alert["cohort_context"],
        "recommended_action": alert["recommended_action"],
    }


def explain_alert(alert_object, language="en"):
    """alert_object: a Stage 3 alert dict. language: 'en' | 'bn' | 'banglish'.

    Returns one or two natural-language sentences. On any failure or timeout,
    falls back to a plain template built directly from the structured fields --
    the dashboard never blocks on this call.
    """
    language_name = LANGUAGE_NAMES.get(language, language)
    facts = _alert_facts(alert_object)

    try:
        client = _get_client()
        response = client.with_options(timeout=8.0).chat.completions.create(
            model=MODEL,
            max_tokens=250,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(language=language_name)},
                {"role": "user", "content": f"Structured alert: {json.dumps(facts)}"},
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            return _fallback_explanation(alert_object, language)
        return text
    except Exception:
        # Never let an LLM-layer failure (network, auth, rate limit, timeout,
        # malformed response) block the dashboard -- degrade to the plain
        # template instead. This is the boundary function; a broad catch is
        # intentional here, not a shortcut.
        return _fallback_explanation(alert_object, language)
