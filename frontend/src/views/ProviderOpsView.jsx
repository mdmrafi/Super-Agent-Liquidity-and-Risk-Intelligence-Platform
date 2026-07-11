import { useEffect, useState } from "react";
import { getAlerts } from "../api";
import AlertCard from "../components/AlertCard";
import Loading from "../components/Loading";
import EmptyState from "../components/EmptyState";

/** Provider operations / network-coordination inbox.
 *
 *  Provider ops only ever see alerts that concern *their provider's e-money
 *  float* -- audience=provider_ops on the server filters those in. An agent's
 *  shared physical-cash shortage is agent-side only and never appears here, so
 *  the provider never sees a pool it doesn't own. Pick a provider to scope to
 *  a single operations team; "All" shows every provider's e-money pressure. */
export default function ProviderOpsView({ meta, split }) {
  const [provider, setProvider] = useState("");
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const filters = { audience: "provider_ops" };
    if (provider) filters.provider = provider;
    getAlerts(split, filters).then((a) => {
      if (cancelled) return;
      setAlerts(a);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [split, provider]);

  return (
    <div className="view">
      <p className="risk-notice">
        This inbox shows <strong>provider e-money</strong> liquidity pressure and any case routed to
        provider operations — the provider's own float and feed. An agent's <strong>shared physical
        cash</strong> shortage is agent-side and never surfaces here, keeping the provider boundary intact.
      </p>

      <div className="view__toolbar">
        <label>
          Provider operations team
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="">All providers</option>
            {meta.providers.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </label>
      </div>

      {loading ? (
        <Loading />
      ) : (
        <>
          <p className="muted result-count">{alerts.length} alert(s) visible to provider ops</p>
          {alerts.length === 0 && <EmptyState title="No provider-ops alerts right now" />}
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
