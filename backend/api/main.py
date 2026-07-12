"""Thin API layer for the Stage 4 dashboard.

Serves Stage 3's alert objects as-is (no recomputation of evidence,
confidence, or routing) and Stage 1's raw balances for the agent view.
Lifecycle actions call the real alerts/lifecycle.py functions and persist
the result back to the same JSON files Stage 3 produced.

Run with (from backend/): python -m api.main
Port comes from BACKEND_PORT in the repo-root .env (default 8000) --
frontend/vite.config.js reads the same variable for its dev proxy, so the
two never drift apart. `uvicorn api.main:app --reload --port <N>` still
works directly if you want to override without touching .env.
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from alerts import lifecycle
from auth.dependencies import CurrentUser, get_current_user
from auth.security import create_access_token, verify_password
from auth.scope import (
    AREA_SCOPED_ROLES,
    PROVIDER_SCOPED_ROLES,
    ensure_complete_scope,
    project_balance,
    provider_of,
    require_area_access,
    require_alert_access,
    require_lifecycle_action,
    require_requested_agent,
    require_requested_provider,
    role_of,
    scope_alerts,
)
from chat.answer import answer_chat_query
from db.connection import init_db
from db.models import User, UserRole
from explain.explain import explain_alert
from . import store

load_dotenv()

BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 5173))
Split = Literal["calibration", "holdout"]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Super Agent Liquidity & Risk Intelligence API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{FRONTEND_PORT}"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str
    role: UserRole


def _user_public(user: User) -> dict:
    return {
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role.value,
        "agent_id": user.agent_id,
        "area": user.area,
        "provider": provider_of(user),
    }


@app.post("/api/auth/login")
async def login(body: LoginRequest):
    user = await User.find_one(User.username == body.username)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "invalid username or password")
    if user.role != body.role:
        raise HTTPException(401, "credentials or selected role do not match")
    ensure_complete_scope(user)
    provider = provider_of(user)
    token = create_access_token({
        "sub": user.username,
        "display_name": user.display_name,
        "role": user.role.value,
        "agent_id": user.agent_id,
        "area": user.area,
        "provider": provider,
    })
    return {"token": token, "user": _user_public(user)}


@app.get("/api/auth/me")
def me(current_user: CurrentUser = Depends(get_current_user)):
    """Lets the frontend restore a session from a stored token on page load
    without re-prompting for a password."""
    return {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "agent_id": current_user.agent_id,
        "area": current_user.area,
        "provider": current_user.provider,
    }


class LifecycleAction(BaseModel):
    split: Split = "calibration"


class ExplainRequest(BaseModel):
    lang: str = "en"
    split: Split = "calibration"


class ChatRequest(BaseModel):
    question: str
    lang: str = "en"
    split: Split = "calibration"


@app.get("/api/meta")
def meta(
    split: Split = "calibration",
    current_user: CurrentUser = Depends(get_current_user),
):
    agents = store.list_agents(split)
    role = role_of(current_user)
    if role == "agent":
        agents = [a for a in agents if a["agent_id"] == current_user.agent_id]
    elif role in AREA_SCOPED_ROLES:
        agents = [a for a in agents if a["area"] == current_user.area]
    areas = sorted({a["area"] for a in agents})
    providers = (
        [provider_of(current_user)]
        if role in PROVIDER_SCOPED_ROLES
        else store.list_providers(split)
    )
    return {"agents": agents, "areas": areas, "providers": providers}


@app.get("/api/alerts")
def list_alerts(
    split: Split = "calibration",
    provider: str | None = None,
    agent_id: str | None = None,
    area: str | None = None,
    alert_type: str | None = None,
    audience: str | None = None,
    start: str | None = None,
    end: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    require_requested_provider(current_user, provider)
    require_requested_agent(current_user, agent_id)
    # Apply the authenticated scope before every optional UI filter. Omitting
    # provider/audience parameters can therefore never broaden access.
    alerts = scope_alerts(current_user, store.load_alerts(split))

    if provider:
        alerts = [a for a in alerts if a["provider"] == provider]
    if agent_id:
        alerts = [a for a in alerts if a["agent_id"] == agent_id]
    if area:
        alerts = [a for a in alerts if a["area"] == area]
    if alert_type:
        alerts = [a for a in alerts if a["alert_type"] == alert_type]
    if audience:
        # who should *see* the alert -- e.g. audience=provider_ops returns only
        # alerts a provider operations user is entitled to see (e-money pressure,
        # never an agent's physical cash drawer).
        alerts = [a for a in alerts if audience in a.get("audience", [])]
    if start:
        alerts = [a for a in alerts if a["timestamp"] >= start]
    if end:
        alerts = [a for a in alerts if a["timestamp"] <= end]

    return sorted(alerts, key=lambda a: a["timestamp"], reverse=True)


@app.get("/api/agents/{agent_id}/balances")
def agent_balances(
    agent_id: str,
    split: Split = "calibration",
    current_user: CurrentUser = Depends(get_current_user),
):
    require_requested_agent(current_user, agent_id)
    result = store.agent_balances(split, agent_id)
    if result is None:
        raise HTTPException(404, f"no data for agent {agent_id}")
    return project_balance(current_user, result)


@app.get('/api/agents/{agent_id}/analytics')
def agent_analytics(
    agent_id: str,
    split: Split = 'calibration',
    window_minutes: int = Query(default=30, ge=1, le=1440),
    limit: int = Query(default=96, ge=1, le=1000),
    current_user: CurrentUser = Depends(get_current_user),
):
    '''Return observed closing balances grouped into real ledger windows.

    Empty time windows are omitted and missing provider readings stay null;
    this endpoint never interpolates, forecasts, or fabricates data.
    '''
    require_requested_agent(current_user, agent_id)
    role = role_of(current_user)
    provider = (
        provider_of(current_user)
        if role in PROVIDER_SCOPED_ROLES
        else None
    )
    result = store.agent_analytics(
        split,
        agent_id,
        window_minutes=window_minutes,
        limit=limit,
        provider=provider,
    )
    if result is None:
        raise HTTPException(404, f'no data for agent {agent_id}')
    require_area_access(current_user, result['area'])

    if role in PROVIDER_SCOPED_ROLES:
        for bucket in result['buckets']:
            bucket['cash_closing_balance'] = None
            bucket['cash_as_of'] = None
    return result


def _apply_lifecycle(alert_id: str, action: str, body: LifecycleAction, current_user: CurrentUser):
    require_lifecycle_action(current_user, action)
    fn = {"acknowledge": lifecycle.acknowledge, "escalate": lifecycle.escalate, "resolve": lifecycle.resolve}[action]
    alerts, alert = store.find_alert(body.split, alert_id)
    if alert is None:
        raise HTTPException(404, f"no such alert: {alert_id}")
    require_alert_access(current_user, alert)

    # actor comes from the verified JWT, never a client-supplied string --
    # a logged-in user can't act as anyone but themselves.
    actor = f"{current_user.display_name} ({current_user.role})"
    try:
        updated = fn(alert, actor=actor, at=datetime.now(timezone.utc).isoformat())
    except ValueError as e:
        raise HTTPException(409, str(e))

    alerts = [updated if a["alert_id"] == alert_id else a for a in alerts]
    store.save_alerts(body.split, alerts)
    return updated


@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, body: LifecycleAction, current_user: CurrentUser = Depends(get_current_user)):
    return _apply_lifecycle(alert_id, "acknowledge", body, current_user)


@app.post("/api/alerts/{alert_id}/escalate")
def escalate_alert(alert_id: str, body: LifecycleAction, current_user: CurrentUser = Depends(get_current_user)):
    return _apply_lifecycle(alert_id, "escalate", body, current_user)


@app.post("/api/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, body: LifecycleAction, current_user: CurrentUser = Depends(get_current_user)):
    return _apply_lifecycle(alert_id, "resolve", body, current_user)


@app.post("/api/alerts/{alert_id}/explain")
def explain(
    alert_id: str,
    body: ExplainRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Stage 5: translate an already-computed alert object into one or two
    natural-language sentences. Computes nothing new -- see explain/explain.py."""
    _, alert = store.find_alert(body.split, alert_id)
    if alert is None:
        raise HTTPException(404, f"no such alert: {alert_id}")
    require_alert_access(current_user, alert)
    return {"explanation": explain_alert(alert, body.lang), "lang": body.lang}


@app.post("/api/chat")
def chat(
    body: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Stage 6: answer a natural-language question about current liquidity/risk
    state. Read-only by construction -- reports on Stage 2/3's already-computed
    alerts and never creates one or changes a case_status. See chat/answer.py."""
    role = role_of(current_user)
    return {
        "answer": answer_chat_query(
            body.question,
            body.lang,
            body.split,
            scope_provider=(provider_of(current_user) if role in PROVIDER_SCOPED_ROLES else None),
            scope_agent_id=(current_user.agent_id if role == "agent" else None),
            scope_area=(current_user.area if role in AREA_SCOPED_ROLES else None),
            scope_role=role,
        ),
        "lang": body.lang,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=BACKEND_PORT, reload=True)
