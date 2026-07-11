import { useEffect, useState } from "react";
import { getAgentBalances, getAlerts } from "../api";
import BalanceCard from "../components/BalanceCard";
import AlertCard from "../components/AlertCard";
import DisplayStatusBanner from "../components/DisplayStatusBanner";

/** Buttons here are illustrative of "normal agent operation" -- this platform
 *  never executes real transactions. The point being demonstrated is that
 *  none of them are ever disabled by an active constrained alert. */
function AgentActions() {
  const [note, setNote] = useState("");
  return (
    <div className="agent-actions">
      <h3>Agent actions (always available)</h3>
      <div className="agent-actions__row">
        <button type="button" onClick={() => setNote("Cash pickup requested.")}>Request cash pickup</button>
        <button type="button" onClick={() => setNote("Transaction history opened.")}>View transaction history</button>
        <button type="button" onClick={() => setNote("Note saved.")}>Add a note</button>
        <button type="button" onClick={() => setNote("Support contacted.")}>Contact support</button>
      </div>
      {note && <p className="hint-text">{note}</p>}
    </div>
  );
}

export default function AgentView({ meta, split }) {
  const [agentId, setAgentId] = useState(meta.agents[0]?.agent_id);
  const [balances, setBalances] = useState(null);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    if (!agentId) return;
    getAgentBalances(split, agentId).then(setBalances);
    getAlerts(split, { agent_id: agentId }).then(setAlerts);
  }, [agentId, split]);

  const constrained = alerts.find((a) => a.display_status !== "normal");

  return (
    <div className="view">
      <div className="view__toolbar">
        <label>
          Agent
          <select value={agentId} onChange={(e) => setAgentId(e.target.value)}>
            {meta.agents.map((a) => (
              <option key={a.agent_id} value={a.agent_id}>{a.agent_id} — {a.area}</option>
            ))}
          </select>
        </label>
      </div>

      <DisplayStatusBanner status={constrained ? constrained.display_status : "normal"} />

      <BalanceCard balances={balances} />

      <AgentActions />

      <h3>Alerts affecting this agent ({alerts.length})</h3>
      {alerts.length === 0 && <p className="muted">No alerts for this agent right now.</p>}
      {alerts.map((a) => (
        <AlertCard key={a.alert_id} alert={a} availableActions={[]} split={split} />
      ))}
    </div>
  );
}
