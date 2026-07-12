"""Reusable server-side authorization rules for role data scopes.

Frontend filters are presentation only. Every API read and mutation must pass
through these helpers so changing query parameters cannot reveal another agent
or provider's data.
"""
from copy import deepcopy

from fastapi import HTTPException


AREA_SCOPED_ROLES = frozenset({"field_officer", "area_team"})
PROVIDER_SCOPED_ROLES = frozenset({"provider_ops", "risk_team"})
VALID_ROLES = frozenset({"agent", *AREA_SCOPED_ROLES, *PROVIDER_SCOPED_ROLES, "admin"})
VALID_PROVIDERS = frozenset({"bKash", "Nagad", "Rocket"})
LIFECYCLE_ACTIONS = {
    "field_officer": frozenset({"acknowledge", "escalate", "resolve"}),
    "provider_ops": frozenset({"acknowledge", "escalate"}),
    "risk_team": frozenset({"acknowledge", "escalate"}),
    "area_team": frozenset({"acknowledge", "escalate", "resolve"}),
    "admin": frozenset({"acknowledge", "escalate", "resolve"}),
}


def _value(value):
    """Return a str enum's value while remaining friendly to JWT strings."""
    return getattr(value, "value", value)


def role_of(user) -> str:
    return _value(user.role)


def provider_of(user) -> str | None:
    provider = _value(getattr(user, "provider", None))
    return provider or None


def ensure_complete_scope(user):
    """Reject malformed/legacy identities before they can reach data access."""
    role = role_of(user)
    if role not in VALID_ROLES:
        raise HTTPException(403, "role has no data access scope")
    if role == "agent" and not getattr(user, "agent_id", None):
        raise HTTPException(403, "agent account is missing its agent assignment")
    if role in AREA_SCOPED_ROLES and not getattr(user, "area", None):
        raise HTTPException(403, "account is missing its area assignment")
    if role in PROVIDER_SCOPED_ROLES:
        provider = provider_of(user)
        if provider not in VALID_PROVIDERS:
            raise HTTPException(403, "account is missing a valid provider assignment")
    return user


def alert_is_visible(user, alert: dict) -> bool:
    """Whether one alert is inside the authenticated identity's hard scope."""
    ensure_complete_scope(user)
    role = role_of(user)
    if role == "admin":
        return True
    if role == "agent":
        return (
            alert.get("agent_id") == user.agent_id
            and role in alert.get("audience", [])
        )
    if role in AREA_SCOPED_ROLES:
        return (
            alert.get("area") == user.area
            and role in alert.get("audience", [])
        )
    if role in PROVIDER_SCOPED_ROLES:
        # Physical-cash alerts have provider=None and are intentionally visible
        # only to the owning agent (or an admin), never a provider employee.
        return (
            alert.get("provider") == provider_of(user)
            and role in alert.get("audience", [])
        )
    return False


def scope_alerts(user, alerts: list[dict]) -> list[dict]:
    ensure_complete_scope(user)
    return [alert for alert in alerts if alert_is_visible(user, alert)]


def require_alert_access(user, alert: dict):
    # Treat an out-of-scope identifier as absent so the response does not
    # confirm another provider's alert exists.
    if not alert_is_visible(user, alert):
        raise HTTPException(404, "no such alert")
    return alert


def require_lifecycle_action(user, action: str):
    ensure_complete_scope(user)
    if action not in LIFECYCLE_ACTIONS.get(role_of(user), frozenset()):
        raise HTTPException(403, f"role cannot {action} alerts")


def require_requested_provider(user, requested_provider: str | None):
    """Reject attempts to override a provider-scoped account via query params."""
    ensure_complete_scope(user)
    if (
        requested_provider
        and role_of(user) in PROVIDER_SCOPED_ROLES
        and requested_provider != provider_of(user)
    ):
        raise HTTPException(403, "provider filter is outside your assigned data scope")


def require_requested_agent(user, requested_agent_id: str | None):
    """Agent accounts can address only their own agent record."""
    ensure_complete_scope(user)
    if (
        requested_agent_id
        and role_of(user) == "agent"
        and requested_agent_id != user.agent_id
    ):
        raise HTTPException(403, "agent is outside your assigned data scope")


def require_area_access(user, area: str | None):
    """Ensure area-scoped operational users stay inside their territory."""
    ensure_complete_scope(user)
    if role_of(user) in AREA_SCOPED_ROLES and area != user.area:
        raise HTTPException(403, "agent is outside your assigned area")


def project_balance(user, balance: dict) -> dict:
    """Return only the balance fields the caller is allowed to observe."""
    ensure_complete_scope(user)
    role = role_of(user)
    if role == "admin":
        return balance
    if role == "agent":
        require_requested_agent(user, balance.get("agent_id"))
        return balance
    if role in AREA_SCOPED_ROLES:
        require_area_access(user, balance.get("area"))
        return balance
    if role in PROVIDER_SCOPED_ROLES:
        provider = provider_of(user)
        scoped = deepcopy(balance)
        # Preserve a stable response shape, but never expose the shared cash
        # drawer or another provider's e-money to provider employees.
        scoped["cash"] = None
        scoped["cash_as_of"] = None
        provider_balance = balance.get("providers", {}).get(provider)
        scoped["providers"] = {provider: provider_balance} if provider_balance else {}
        return scoped
    raise HTTPException(403, "role has no data access scope")
