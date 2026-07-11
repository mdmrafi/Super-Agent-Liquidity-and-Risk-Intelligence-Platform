import { useEffect, useState } from "react";
import { getAlerts } from "../api";
import AlertCard from "../components/AlertCard";
import Filters from "../components/Filters";

export default function OpsView({ meta, split }) {
  const [filters, setFilters] = useState({});
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    getAlerts(split, filters).then(setAlerts);
  }, [split, filters]);

  return (
    <div className="view">
      <Filters meta={meta} value={filters} onChange={setFilters} />
      <p className="muted">{alerts.length} alert(s) match the current filters</p>
      {alerts.map((a) => (
        <AlertCard
          key={a.alert_id}
          alert={a}
          availableActions={["acknowledge", "escalate", "resolve"]}
          split={split}
        />
      ))}
    </div>
  );
}
