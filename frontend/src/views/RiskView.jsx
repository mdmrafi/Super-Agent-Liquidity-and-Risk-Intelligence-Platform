import { useEffect, useState } from "react";
import { getAlerts } from "../api";
import AlertCard from "../components/AlertCard";
import Loading from "../components/Loading";
import EmptyState from "../components/EmptyState";

export default function RiskView({ split }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getAlerts(split, { alert_type: "unusual_activity" }).then((a) => {
      if (cancelled) return;
      setAlerts(a);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [split]);

  return (
    <div className="view">
      <p className="risk-notice">
        These are flagged as <strong>unusual — requires review</strong>, never as a fraud
        determination. Actions here are limited to reviewing the evidence or escalating; nothing
        here blocks or restricts the agent.
      </p>
      {loading ? (
        <Loading />
      ) : (
        <>
          <p className="muted result-count">{alerts.length} unusual_activity alert(s)</p>
          {alerts.length === 0 && <EmptyState title="No unusual-activity alerts right now" />}
          {alerts.map((a) => (
            <AlertCard
              key={a.alert_id}
              alert={a}
              availableActions={["acknowledge", "escalate"]}
              split={split}
            />
          ))}
        </>
      )}
    </div>
  );
}
