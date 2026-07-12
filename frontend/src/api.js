const BASE = "/api";
const STORAGE_KEY = "super_agent_token";

async function req(path, options = {}) {
  const token = localStorage.getItem(STORAGE_KEY);
  const headers = { ...authHeaders(token), ...(options.headers || {}) };
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${path}: ${body}`);
  }
  return res.json();
}

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function login(username, password, role) {
  return req(`/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, role }),
  });
}

export function getMe(token) {
  return req(`/auth/me`, { headers: authHeaders(token) });
}

export function getMeta(split) {
  return req(`/meta?split=${split}`);
}

export function getAlerts(split, filters = {}) {
  const params = new URLSearchParams({ split, ...filters });
  return req(`/alerts?${params.toString()}`);
}

export function getAgentBalances(split, agentId) {
  return req(`/agents/${agentId}/balances?split=${split}`);
}

function lifecycleAction(action) {
  // actor is derived server-side from the bearer token (see
  // backend/api/main.py) -- a logged-in user can only ever act as
  // themselves, never as a client-supplied name.
  return (alertId, split, token) =>
    req(`/alerts/${alertId}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders(token) },
      body: JSON.stringify({ split }),
    });
}

export const acknowledgeAlert = lifecycleAction("acknowledge");
export const escalateAlert = lifecycleAction("escalate");
export const resolveAlert = lifecycleAction("resolve");

export function explainAlert(alertId, lang, split) {
  return req(`/alerts/${alertId}/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lang, split }),
  });
}

export function askChat(question, lang, split) {
  return req(`/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, lang, split }),
  });
}
