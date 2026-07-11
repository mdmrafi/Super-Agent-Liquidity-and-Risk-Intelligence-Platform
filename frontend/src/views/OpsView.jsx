import { useEffect, useState } from "react";
import { getAlerts } from "../api";
import AlertCard from "../components/AlertCard";
import Filters from "../components/Filters";
import Loading from "../components/Loading";
import EmptyState from "../components/EmptyState";

export default function OpsView({ meta, split }) {
  const [filters, setFilters] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getAlerts(split, filters).then((a) => {
      if (cancelled) return;
      setAlerts(a);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [split, filters]);

  return (
    <div className="view">
      <Filters meta={meta} value={filters} onChange={setFilters} />
      {loading ? (
        <Loading />
      ) : (
        <>
          <p className="muted result-count">{alerts.length} alert(s) match the current filters</p>
          {alerts.length === 0 && <EmptyState title="No alerts match these filters" hint="Try clearing a filter." />}
          {alerts.map((a) => (
            <AlertCard
              key={a.alert_id}
              alert={a}
              availableActions={["acknowledge", "escalate", "resolve"]}
              split={split}
            />
          ))}
        </>
      )}
    </div>
  );
}
