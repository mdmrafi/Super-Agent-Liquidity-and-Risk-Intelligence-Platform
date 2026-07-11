const BASE = "/api";

async function req(path, options) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${path}: ${body}`);
  }
  return res.json();
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
  return (alertId, actor, split) =>
    req(`/alerts/${alertId}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor, split }),
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
