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

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from alerts import lifecycle
from auth.dependencies import CurrentUser, get_current_user
from auth.security import create_access_token, verify_password
from chat.answer import answer_chat_query
from db.connection import init_db
from db.models import User
from explain.explain import explain_alert
from . import store

load_dotenv()

BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 5173))


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


def _user_public(user: User) -> dict:
    return {
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role.value,
        "agent_id": user.agent_id,
        "area": user.area,
        "provider": user.provider,
    }


@app.post("/api/auth/login")
async def login(body: LoginRequest):
    user = await User.find_one(User.username == body.username)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "invalid username or password")
    token = create_access_token({
        "sub": user.username,
        "display_name": user.display_name,
        "role": user.role.value,
        "agent_id": user.agent_id,
        "area": user.area,
        "provider": user.provider,
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
    split: str = "calibration"


class ExplainRequest(BaseModel):
    lang: str = "en"
    split: str = "calibration"


class ChatRequest(BaseModel):
    question: str
    lang: str = "en"
    split: str = "calibration"


@app.get("/api/meta")
def meta(split: str = "calibration"):
    agents = store.list_agents(split)
    alerts = store.load_alerts(split)
    areas = sorted({a["area"] for a in agents})
    providers = sorted({a["provider"] for a in alerts if a["provider"]})
    return {"agents": agents, "areas": areas, "providers": providers}


@app.get("/api/alerts")
def list_alerts(
    split: str = "calibration",
    provider: str | None = None,
    agent_id: str | None = None,
    area: str | None = None,
    alert_type: str | None = None,
    audience: str | None = None,
    start: str | None = None,
    end: str | None = None,
):
    alerts = store.load_alerts(split)

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
def agent_balances(agent_id: str, split: str = "calibration"):
    result = store.agent_balances(split, agent_id)
    if result is None:
        raise HTTPException(404, f"no data for agent {agent_id}")
    return result


def _apply_lifecycle(alert_id: str, action: str, body: LifecycleAction, current_user: CurrentUser):
    fn = {"acknowledge": lifecycle.acknowledge, "escalate": lifecycle.escalate, "resolve": lifecycle.resolve}[action]
    alerts, alert = store.find_alert(body.split, alert_id)
    if alert is None:
        raise HTTPException(404, f"no such alert: {alert_id}")

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
def explain(alert_id: str, body: ExplainRequest):
    """Stage 5: translate an already-computed alert object into one or two
    natural-language sentences. Computes nothing new -- see explain/explain.py."""
    _, alert = store.find_alert(body.split, alert_id)
    if alert is None:
        raise HTTPException(404, f"no such alert: {alert_id}")
    return {"explanation": explain_alert(alert, body.lang), "lang": body.lang}


@app.post("/api/chat")
def chat(body: ChatRequest):
    """Stage 6: answer a natural-language question about current liquidity/risk
    state. Read-only by construction -- reports on Stage 2/3's already-computed
    alerts and never creates one or changes a case_status. See chat/answer.py."""
    return {"answer": answer_chat_query(body.question, body.lang, body.split), "lang": body.lang}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=BACKEND_PORT, reload=True)
