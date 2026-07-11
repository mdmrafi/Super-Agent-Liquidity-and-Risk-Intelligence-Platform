import { useEffect, useState } from "react";
import { getAgentBalances, getAlerts } from "../api";
import BalanceCard from "../components/BalanceCard";
import AlertCard from "../components/AlertCard";
import DisplayStatusBanner from "../components/DisplayStatusBanner";
import Loading from "../components/Loading";
import EmptyState from "../components/EmptyState";

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

export default function AgentView({ meta, split, user }) {
  // Logged-in agents only ever see their own dashboard, not a picker over
  // every agent -- that full-roster lookup is what the Ops/Provider/Risk
  // roles use AlertCard's agent_id/area columns for instead.
  const lockedToSelf = user?.role === "agent" && user.agent_id;
  const [agentId, setAgentId] = useState(lockedToSelf ? user.agent_id : meta.agents[0]?.agent_id);
  const [balances, setBalances] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!agentId) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([getAgentBalances(split, agentId), getAlerts(split, { agent_id: agentId })]).then(
      ([b, a]) => {
        if (cancelled) return;
        setBalances(b);
        setAlerts(a);
        setLoading(false);
      }
    );
    return () => {
      cancelled = true;
    };
  }, [agentId, split]);

  const constrained = alerts.find((a) => a.display_status !== "normal");

  return (
    <div className="view">
      <div className="view__toolbar">
        {lockedToSelf ? (
          <div>
            <span className="eyebrow">Agent</span>
            <p className="locked-agent-label">{user.agent_id} — {user.area}</p>
          </div>
        ) : (
          <label>
            Agent
            <select value={agentId} onChange={(e) => setAgentId(e.target.value)}>
              {meta.agents.map((a) => (
                <option key={a.agent_id} value={a.agent_id}>{a.agent_id} — {a.area}</option>
              ))}
            </select>
          </label>
        )}
      </div>

      {loading ? (
        <Loading />
      ) : (
        <>
          <DisplayStatusBanner status={constrained ? constrained.display_status : "normal"} />

          <BalanceCard balances={balances} />

          <AgentActions />

          <h3>Alerts affecting this agent ({alerts.length})</h3>
          {alerts.length === 0 && <EmptyState title="No alerts for this agent right now" />}
          {alerts.map((a) => (
            <AlertCard key={a.alert_id} alert={a} availableActions={[]} split={split} />
          ))}
        </>
      )}
    </div>
  );
}
