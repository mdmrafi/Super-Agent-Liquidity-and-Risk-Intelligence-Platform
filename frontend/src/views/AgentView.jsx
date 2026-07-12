import { useEffect, useMemo, useState } from "react";
import { getAgentBalances, getAlerts } from "../api";
import AlertCard from "../components/AlertCard";
import DisplayStatusBanner from "../components/DisplayStatusBanner";
import Loading from "../components/Loading";
import EmptyState from "../components/EmptyState";
import { formatBDT, formatDateTime, PROVIDER_COLORS, PROVIDER_TEXT, CASH_COLOR, SEVERITY_BG, SEVERITY_TEXT } from "../lib/format";

/* ---------------------------------------------------------------------------
   Multi-provider Agent cockpit
   ---------------------------------------------------------------------------
   Replaces the older single-column layout with a bento-style multi-provider
   view: a hero portfolio balance + operational status, a channel grid
   (physical cash + bKash + Nagad + Rocket), a unified cross-provider alerts
   feed, and an AI insight panel explaining the most material signal.

   Data plumbing is unchanged -- everything is read from /api/agents/{id}/balances
   and /api/alerts, so it stays in lockstep with the rest of the platform.
   Super Agent never executes a transaction or disables operations because of
   an alert; the Quick actions row below demonstrates only normal agent
   workflows (request cash pickup, open history, add a note, contact support).
------------------------------------------------------------------------- */

const PROVIDER_NAME = {
  bKash: "bKash",
  Nagad: "Nagad",
  Rocket: "Rocket",
};

function ProviderChip({ provider }) {
  return (
    <span className="mpa-chip" style={{ background: PROVIDER_COLORS[provider] || CASH_COLOR, color: PROVIDER_TEXT }}>
      {PROVIDER_NAME[provider] || provider}
    </span>
  );
}

function CashChip() {
  return (
    <span className="mpa-chip mpa-chip--cash" style={{ background: CASH_COLOR, color: PROVIDER_TEXT }}>
      Cash
    </span>
  );
}

/* ---------- hero ---------------------------------------------------------- */
function PortfolioHero({ balances, total, alertCount, alertCritical }) {
  return (
    <section className="mpa-hero">
      <div className="mpa-hero__balance">
        <p className="eyebrow">Arithmetic balance snapshot — not transferable</p>
        <div className="mpa-hero__totalRow">
          <span className="mpa-hero__total">{formatBDT(total)}</span>
        </div>
        <p className="mpa-hero__caption">
          Physical cash plus separately held provider e-money as observed at {formatDateTime(balances.cash_as_of)}.
          This arithmetic summary is not a transferable pool; operational decisions must use the channel breakdown below.
        </p>
      </div>

      <div className={`mpa-hero__status ${alertCount ? "mpa-hero__status--attention" : ""}`}>
        <p className="eyebrow">Operational status</p>
        <div className="mpa-hero__statusRow">
          <span className={`mpa-hero__dot ${alertCount ? "mpa-hero__dot--attention" : ""}`} aria-hidden="true" />
          <h3>{alertCount ? "Material signal detected" : "Operating normally"}</h3>
        </div>
        <p className="mpa-hero__statusCaption">
          {alertCount
            ? `${alertCount} cross-provider signal${alertCount === 1 ? "" : "s"} need review${alertCritical ? `, ${alertCritical} critical` : ""}.`
            : "No active liquidity signals across any channel right now."}
        </p>
        <div className="mpa-hero__statusFoot">
          <span>Dataset observation: {formatDateTime(balances.cash_as_of)}</span>
          <span className="material-symbols-outlined" aria-hidden="true">history</span>
        </div>
      </div>
    </section>
  );
}

/* ---------- bento channels ------------------------------------------------ */
function ChannelsBento({ balances }) {
  const entries = [
    {
      key: "cash",
      label: "Physical cash drawer",
      subtitle: "Shared across all providers",
      value: balances.cash,
      trend: "neutral",
      asOf: balances.cash_as_of,
      Chip: CashChip,
    },
    ...Object.entries(balances.providers || {}).map(([provider, item]) => ({
      key: provider,
      label: `${provider} e-money float`,
      subtitle: "Provider ledger balance",
      value: item.balance,
      trend: "neutral",
      asOf: item.as_of,
      Chip: () => <ProviderChip provider={provider} />,
    })),
  ];

  return (
    <section className="mpa-channels" aria-label="Per-channel balances">
      {entries.map((item) => (
        <article className={`mpa-channel mpa-channel--${item.trend}`} key={item.key}>
          <div className="mpa-channel__top">
            <item.Chip />
            <span className="mpa-channel__more" aria-hidden="true">•••</span>
          </div>
          <p className="mpa-channel__label">{item.label}</p>
          <strong className="mpa-channel__value">{formatBDT(item.value)}</strong>
          <small className="mpa-channel__sub">{item.subtitle}</small>
          <small className="mpa-channel__asOf">Updated {formatDateTime(item.asOf)}</small>
        </article>
      ))}
    </section>
  );
}

/* ---------- unified alerts feed ------------------------------------------- */
const TYPE_BADGE = {
  liquidity_shortage: { label: "Liquidity pressure", tone: "soft" },
  unusual_activity: { label: "Unusual activity", tone: "soft" },
  data_quality: { label: "Data quality", tone: "soft" },
};

function severityIcon(level) {
  if (level === "high") return { icon: "error", cls: "critical" };
  if (level === "medium") return { icon: "warning", cls: "warn" };
  return { icon: "info", cls: "info" };
}

function UnifiedAlertsFeed({ alerts, onSelect, selectedId }) {
  if (!alerts.length) {
    return <EmptyState title="No cross-provider alerts right now" hint="Signals will appear here as soon as any channel shows pressure or unusual activity." />;
  }

  return (
    <div className="mpa-alertsList">
      {alerts.map((a) => {
        const sev = severityIcon(a.severity);
        const type = TYPE_BADGE[a.alert_type] || { label: a.alert_type, tone: "soft" };
        const isProvider = !!a.provider;
        return (
          <button
            type="button"
            key={a.alert_id}
            className={`mpa-alertRow${selectedId === a.alert_id ? " mpa-alertRow--selected" : ""}`}
            onClick={() => onSelect(a.alert_id)}
            aria-pressed={selectedId === a.alert_id}
          >
            <span className={`material-symbols-outlined mpa-alertRow__icon mpa-alertRow__icon--${sev.cls}`} aria-hidden="true">
              {sev.icon}
            </span>
            <div className="mpa-alertRow__body">
              <div className="mpa-alertRow__head">
                <h4>{type.label}{isProvider ? ` · ${a.provider}` : " · shared cash"}</h4>
                <span className="mpa-alertRow__time">{formatDateTime(a.timestamp)}</span>
              </div>
              <p className="mpa-alertRow__evidence">{(a.evidence && a.evidence[0]) || "AI-detected signal"}</p>
              <div className="mpa-alertRow__meta">
                <span className="mpa-pill" style={{ background: SEVERITY_BG[a.severity], color: SEVERITY_TEXT[a.severity] }}>
                  {a.severity}
                </span>
                <span className="mpa-alertRow__conf">AI {(a.confidence * 100).toFixed(0)}%</span>
                <span className="mpa-alertRow__route">→ {a.recommended_owner}</span>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

/* ---------- AI insight panel --------------------------------------------- */
function AIInsightPanel({ alert, totals, split }) {
  const totalProviders = totals.totalProviders;
  const providerTotal = totals.providerTotal;
  const cashTotal = totals.cashTotal;
  const portfolioShare = alert && alert.provider && totals.providerByName?.[alert.provider] != null
    ? Math.round((totals.providerByName[alert.provider] / Math.max(1, providerTotal)) * 100)
    : null;
  const tone = alert && alert.severity === "high" ? "critical" : alert && alert.severity === "medium" ? "warn" : "info";

  return (
    <aside className="mpa-aiPanel" aria-label="AI analysis detail">
      <div className="mpa-aiPanel__bar">
        <div className="mpa-aiPanel__barLeft">
          <span className="material-symbols-outlined" aria-hidden="true">smart_toy</span>
          <span className="mpa-aiPanel__barTitle">AI analysis detail</span>
        </div>
        <div className="mpa-aiPanel__barRight">
          {alert && (
            <span className={`mpa-pill mpa-pill--${tone}`}>
              {alert.alert_type === "liquidity_shortage" ? "Liquidity" : alert.alert_type === "unusual_activity" ? "Activity" : "Quality"}
            </span>
          )}
          <span className="mpa-aiPanel__id">{alert?.alert_id || "—"}</span>
        </div>
      </div>

      {!alert ? (
        <div className="mpa-aiPanel__empty">
          <span className="material-symbols-outlined" aria-hidden="true">psychology</span>
          <p>Select a signal on the left to see a per-provider breakdown, AI reasoning and recommended action.</p>
        </div>
      ) : (
        <div className="mpa-aiPanel__body">
          <div className="mpa-aiPanel__head">
            <div>
              <div className="mpa-aiPanel__chips">
                <span className="mpa-pill mpa-pill--severity" style={{ background: SEVERITY_BG[alert.severity], color: SEVERITY_TEXT[alert.severity] }}>
                  {alert.severity}
                </span>
                <span className="mpa-aiPanel__area">
                  <span className="material-symbols-outlined" aria-hidden="true">location_on</span>
                  {alert.area}
                </span>
              </div>
              <h3>
                {alert.alert_type === "liquidity_shortage"
                  ? `Provider pressure · ${alert.provider || "cash drawer"}`
                  : "Unusual transactional pattern"}
              </h3>
              <p className="mpa-aiPanel__sub">
                {alert.recommended_action === "review_evidence" ? "Evidence review recommended" : alert.recommended_action} · routed to {alert.recommended_owner}
              </p>
            </div>
            {alert.provider && <ProviderChip provider={alert.provider} />}
            {!alert.provider && alert.liquidity_type === "physical_cash" && <CashChip />}
          </div>

          <div className="mpa-aiPanel__grid">
            <div className="mpa-aiPanel__reason">
              <h4><span className="material-symbols-outlined" aria-hidden="true">psychology</span> Why this occurred</h4>
              <p>{(alert.evidence && alert.evidence[0]) || "Cross-channel pattern flagged by the engine."}</p>
              <div className="mpa-confidence">
                <div className="mpa-confidence__head">
                  <span className="eyebrow">Model confidence</span>
                  <span className="mpa-confidence__value">{Math.round((alert.confidence || 0) * 100)}% <small>({alert.confidence_label})</small></span>
                </div>
                <div className="mpa-confidence__bar" aria-hidden="true">
                  <span style={{ width: `${Math.round((alert.confidence || 0) * 100)}%` }} />
                </div>
              </div>
            </div>

            <div className="mpa-aiPanel__evidence">
              <h4><span className="material-symbols-outlined" aria-hidden="true">troubleshoot</span> Channel footprint</h4>
              <dl>
                <div>
                  <dt>Channels</dt>
                  <dd>{totalProviders}</dd>
                </div>
                <div>
                  <dt>Provider float</dt>
                  <dd>{formatBDT(providerTotal)}</dd>
                </div>
                <div>
                  <dt>Cash drawer</dt>
                  <dd>{formatBDT(cashTotal)}</dd>
                </div>
                {portfolioShare != null && (
                  <div>
                    <dt>Focus share</dt>
                    <dd>{portfolioShare}%</dd>
                  </div>
                )}
              </dl>
              <p className="mpa-aiPanel__evidenceNote">
                Evidence reflects Stage 3's per-alert computation. Lifecycle actions below are advisory only — Super Agent never disables operations.
              </p>
            </div>
          </div>

          <div className="mpa-aiPanel__footer">
            <div className="mpa-aiPanel__stakeholder">
              <span className="mpa-aiPanel__avatar" aria-hidden="true">
                {(alert.recommended_owner || "??").slice(0, 2).toUpperCase()}
              </span>
              <div>
                <p className="eyebrow">Routed to</p>
                <strong>{alert.recommended_owner}</strong>
              </div>
            </div>
            <div className="mpa-aiPanel__status">
              <span className="mpa-pill mpa-pill--soft">Status · Human review recommended</span>
              <span className="mpa-pill mpa-pill--ghost">No action taken</span>
            </div>
          </div>

          <details className="mpa-aiPanel__detail">
            <summary>Show full evidence &amp; lifecycle</summary>
            <div className="mpa-aiPanel__fullCard">
              <AlertCard alert={alert} availableActions={[]} split={split} />
            </div>
          </details>
        </div>
      )}
    </aside>
  );
}

/* ---------- quick actions ------------------------------------------------ */
function AgentActions() {
  const [note, setNote] = useState("");
  return (
    <section className="mpa-actions">
      <div className="mpa-actions__heading">
        <div>
          <p className="eyebrow">Operations</p>
          <h3>Quick actions</h3>
        </div>
        <p>These are normal agent workflows only; Super Agent never executes a transaction or disables operations because of an alert.</p>
      </div>
      <div className="mpa-actions__row">
        <button type="button" onClick={() => setNote("Cash pickup requested.")}>Request cash pickup</button>
        <button type="button" onClick={() => setNote("Transaction history opened.")}>View transaction history</button>
        <button type="button" onClick={() => setNote("Note saved.")}>Add a note</button>
        <button type="button" onClick={() => setNote("Support contacted.")}>Contact support</button>
      </div>
      {note && <p className="hint-text">{note}</p>}
    </section>
  );
}

/* ---------- root view ---------------------------------------------------- */
export default function AgentView({ meta, split, user }) {
  const lockedToSelf = user?.role === "agent" && user.agent_id;
  const [agentId, setAgentId] = useState(lockedToSelf ? user.agent_id : meta.agents[0]?.agent_id);
  const [balances, setBalances] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAlertId, setSelectedAlertId] = useState(null);

  useEffect(() => {
    if (!agentId) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([getAgentBalances(split, agentId), getAlerts(split, { agent_id: agentId })]).then(([b, a]) => {
      if (cancelled) return;
      setBalances(b);
      setAlerts(a);
      setSelectedAlertId((prev) => (prev && a.some((x) => x.alert_id === prev) ? prev : a[0]?.alert_id || null));
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [agentId, split]);

  const constrained = alerts.find((alert) => alert.display_status !== "normal");
  const selectedAlert = alerts.find((a) => a.alert_id === selectedAlertId) || null;
  const alertCriticalCount = alerts.filter((a) => a.severity === "high").length;

  const totals = useMemo(() => {
    if (!balances) return { total: 0, providerTotal: 0, cashTotal: 0, totalProviders: 0, providerByName: {} };
    const providerTotal = Object.values(balances.providers || {}).reduce((sum, p) => sum + (p.balance || 0), 0);
    const cashTotal = balances.cash || 0;
    const total = providerTotal + cashTotal;
    const providerByName = {};
    for (const [name, info] of Object.entries(balances.providers || {})) providerByName[name] = info.balance || 0;
    return { total, providerTotal, cashTotal, totalProviders: Object.keys(balances.providers || {}).length, providerByName };
  }, [balances]);

  return (
    <div className="view mpa-dashboard">
      <div className="view__toolbar">
        {lockedToSelf ? (
          <div className="agent-identity">
            <span className="eyebrow">Agent workspace</span>
            <p className="locked-agent-label">{user.agent_id} — {user.area}</p>
          </div>
        ) : (
          <label>
            Agent
            <select value={agentId} onChange={(e) => setAgentId(e.target.value)}>
              {meta.agents.map((agent) => (
                <option key={agent.agent_id} value={agent.agent_id}>{agent.agent_id} — {agent.area}</option>
              ))}
            </select>
          </label>
        )}
        <span className="mpa-toolbar__hint">Multi-provider cockpit · {totals.totalProviders} provider{totals.totalProviders === 1 ? "" : "s"} linked</span>
      </div>

      {loading ? <Loading /> : (
        <>
          <DisplayStatusBanner status={constrained ? constrained.display_status : "normal"} />

          <PortfolioHero
            balances={balances}
            total={totals.total}
            alertCount={alerts.length}
            alertCritical={alertCriticalCount}
          />

          <ChannelsBento balances={balances} />

          <div className="mpa-split">
            <section className="mpa-feed" aria-label="Cross-provider signals">
              <header className="mpa-feed__header">
                <div>
                  <h3>Cross-provider dataset signals</h3>
                  <p>{alerts.length} active · sorted by most recent</p>
                </div>
                <span className="mpa-feed__badge">Model/rule detected</span>
              </header>
              <UnifiedAlertsFeed
                alerts={alerts}
                onSelect={setSelectedAlertId}
                selectedId={selectedAlertId}
              />
              <AgentActions />
            </section>

            <AIInsightPanel alert={selectedAlert} totals={totals} split={split} />
          </div>
        </>
      )}
    </div>
  );
}
