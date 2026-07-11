"""Routing determination (spec 6.3): a pure function, cohort_context -> owner.

High-severity unusual-activity (is_anomalous) always routes to risk_team,
regardless of cohort_context -- the output contract has a single
recommended_owner field, so for an anomalous row this field carries the
escalation target rather than the liquidity-routing owner. Flagged as a
simplification: section 7/8's "+ copy to risk/compliance analyst" implies an
addition, not a replacement, but the given Stage 2 contract has no second
field to carry both.
"""

_LIQUIDITY_ROUTING = {
    "agent_only": "field_officer",
    "self_history_fallback": "field_officer",
    "area_wide": "area_team",
    "provider_wide": "provider_ops",
}


def recommend_owner(cohort_context, is_anomalous):
    if is_anomalous:
        return "risk_team"
    return _LIQUIDITY_ROUTING.get(cohort_context, "field_officer")
