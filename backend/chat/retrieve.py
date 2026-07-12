"""Stage 6 retrieval (spec section 10): narrow live Stage 2/3 state down to the
entities a question mentions.

This is deliberately NOT a search index. With 20 agents, 3 providers, and 5
areas, "retrieval" here means a literal entity-match filter over the alerts
Stage 3 already produced -- not embeddings, not ranking learned from a corpus.
Nothing in this module computes a forecast, a severity, or a routing decision;
it only reads and narrows what Stage 2/3 decided upstream. It also never writes:
alerts are loaded through the same read path the dashboard uses and returned
as-is.
"""
import re
from collections import Counter

from api import store

# high > medium > low; used to surface the most severe open alert first when
# no entity is mentioned (the "which provider needs attention" query).
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}


def _known_entities(alerts, agents):
    providers = sorted({a["provider"] for a in alerts if a.get("provider")})
    areas = sorted({a["area"] for a in alerts if a.get("area")})
    agent_ids = sorted({a["agent_id"] for a in agents})
    return providers, areas, agent_ids


def _match_substring(candidates, question):
    """Case-insensitive substring match. Longest candidate first so a longer
    name wins deterministically if two known entities overlap."""
    q = question.lower()
    for c in sorted(candidates, key=len, reverse=True):
        if c.lower() in q:
            return c
    return None


def _match_agent(agent_ids, question):
    """Accept 'agent_16', 'agent 16', or 'agent16'; only returns an id that
    actually exists in the data (a bare number alone is not treated as an id)."""
    m = re.search(r"agent[_ ]?(\d+)", question.lower())
    if not m:
        return None
    candidate = f"agent_{m.group(1)}"
    return candidate if candidate in agent_ids else None


def _severity_sort_key(alert):
    return (SEVERITY_RANK.get(alert.get("severity"), 0), alert.get("confidence", 0.0))


def _balance_snapshot(split, agent_id, scope_provider=None):
    """Only pulled when a specific agent is named -- keeps the context small and
    the query grounded. A provider employee receives only their provider's
    e-money balance, never shared cash or another provider's balance."""
    if not agent_id:
        return None
    snapshot = store.agent_balances(split, agent_id)
    if snapshot is None or not scope_provider:
        return snapshot
    provider_balance = snapshot.get("providers", {}).get(scope_provider)
    return {
        "agent_id": snapshot["agent_id"],
        "area": snapshot["area"],
        "cash": None,
        "cash_as_of": None,
        "providers": {scope_provider: provider_balance} if provider_balance else {},
    }


def _cohort_summary(open_alerts):
    if not open_alerts:
        return {}
    return {"by_cohort_context": dict(Counter(a.get("cohort_context") for a in open_alerts))}


def _scoped_state(
    split,
    scope_provider=None,
    scope_agent_id=None,
    scope_area=None,
    scope_role=None,
):
    alerts = store.load_alerts(split)
    agents = store.list_agents(split)
    if scope_role and scope_role != "admin":
        alerts = [a for a in alerts if scope_role in a.get("audience", [])]
    if scope_provider:
        alerts = [a for a in alerts if a.get("provider") == scope_provider]
    if scope_agent_id:
        alerts = [a for a in alerts if a.get("agent_id") == scope_agent_id]
        agents = [a for a in agents if a.get("agent_id") == scope_agent_id]
    if scope_area:
        alerts = [a for a in alerts if a.get("area") == scope_area]
        agents = [a for a in agents if a.get("area") == scope_area]
    return alerts, agents


def match_entities(
    question,
    split="calibration",
    scope_provider=None,
    scope_agent_id=None,
    scope_area=None,
    scope_role=None,
):
    """Expose which known entities a question mentions (used by callers/tests)."""
    alerts, agents = _scoped_state(
        split, scope_provider, scope_agent_id, scope_area, scope_role
    )
    providers, areas, agent_ids = _known_entities(alerts, agents)
    if scope_provider and scope_provider not in providers:
        providers.append(scope_provider)
    if scope_agent_id:
        # An agent may discuss every provider, even if one has no open alert.
        providers = store.list_providers(split)
    return {
        "provider": _match_substring(providers, question),
        "area": _match_substring(areas, question),
        "agent_id": _match_agent(agent_ids, question),
    }


def retrieve_relevant_state(
    question,
    split="calibration",
    scope_provider=None,
    scope_agent_id=None,
    scope_area=None,
    scope_role=None,
):
    """Filter live state to the entities mentioned in `question`.

    Returns a dict with:
      - mentioned:        which provider/area/agent (if any) the question named
      - open_alerts:      alerts whose case_status != 'resolved', filtered to the
                          mentioned entities and sorted by severity desc. With no
                          entity mentioned this is every open alert, so the top of
                          the list is the highest-severity open alert overall.
      - balance_snapshot: latest balances for a named agent, else None
      - cohort_summary:   compact count of cohort_context across the open alerts
    """
    alerts, agents = _scoped_state(
        split, scope_provider, scope_agent_id, scope_area, scope_role
    )
    providers, areas, agent_ids = _known_entities(alerts, agents)
    if scope_provider and scope_provider not in providers:
        providers.append(scope_provider)
    if scope_agent_id:
        providers = store.list_providers(split)

    mentioned_provider = _match_substring(providers, question)
    mentioned_area = _match_substring(areas, question)
    mentioned_agent = _match_agent(agent_ids, question)

    open_alerts = [a for a in alerts if a.get("case_status") != "resolved"]
    if mentioned_provider:
        open_alerts = [a for a in open_alerts if a.get("provider") == mentioned_provider]
    if mentioned_area:
        open_alerts = [a for a in open_alerts if a.get("area") == mentioned_area]
    if mentioned_agent:
        open_alerts = [a for a in open_alerts if a.get("agent_id") == mentioned_agent]

    open_alerts = sorted(open_alerts, key=_severity_sort_key, reverse=True)

    return {
        "mentioned": {
            "provider": mentioned_provider,
            "area": mentioned_area,
            "agent_id": mentioned_agent,
        },
        "open_alerts": open_alerts,
        "balance_snapshot": _balance_snapshot(split, mentioned_agent, scope_provider),
        "cohort_summary": _cohort_summary(open_alerts),
    }
