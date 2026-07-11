import { useEffect, useState } from "react";
import { getAlerts } from "../api";
import AlertCard from "../components/AlertCard";

export default function RiskView({ split }) {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    getAlerts(split, { alert_type: "unusual_activity" }).then(setAlerts);
  }, [split]);

  return (
    <div className="view">
      <p className="risk-notice">
        These are flagged as <strong>unusual — requires review</strong>, never as a fraud
        determination. Actions here are limited to reviewing the evidence or escalating; nothing
        here blocks or restricts the agent.
      </p>
      <p className="muted">{alerts.length} unusual_activity alert(s)</p>
      {alerts.map((a) => (
        <AlertCard
          key={a.alert_id}
          alert={a}
          availableActions={["acknowledge", "escalate"]}
          split={split}
          actor="risk_analyst"
        />
      ))}
    </div>
  );
}
