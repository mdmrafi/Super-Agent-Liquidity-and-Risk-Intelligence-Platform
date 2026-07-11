import { useState } from "react";
import AlertExplanation from "./AlertExplanation";
import { acknowledgeAlert, escalateAlert, resolveAlert } from "../api";
import { formatDateTime, describeCohortContext, PROVIDER_COLORS, SEVERITY_COLORS } from "../lib/format";

const ACTION_FN = { acknowledge: acknowledgeAlert, escalate: escalateAlert, resolve: resolveAlert };
const ACTION_LABEL = { acknowledge: "Acknowledge", escalate: "Escalate", resolve: "Resolve" };
const NEXT_STATUS = { new: "acknowledge", acknowledged: "escalate", escalated: "resolve" };

const ALERT_TYPE_LABEL = {
  liquidity_shortage: "Liquidity shortage",
  unusual_activity: "Unusual activity — requires review",
  data_quality: "Data quality",
};

const ROLE_LABEL = {
  agent: "Agent",
  field_officer: "Field officer",
  area_team: "Area team",
  provider_ops: "Provider ops",
  risk_team: "Risk team",
};

/** Which pool an alert concerns: a provider's e-money (colored provider badge)
 *  or the agent's shared physical cash drawer (provider is null on the alert). */
function ScopeBadge({ alert }) {
  if (alert.provider) {
    return (
      <span className="badge" style={{ background: PROVIDER_COLORS[alert.provider] }}>
        {alert.provider}
      </span>
    );
  }
  if (alert.liquidity_type === "physical_cash") {
    return <span className="badge" style={{ background: "#495057" }}>Shared physical cash</span>;
  }
  return null;
}

export default function AlertCard({ alert, availableActions = [], split, actor = "dashboard_user", onChange }) {
  const [current, setCurrent] = useState(alert);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const nextAction = NEXT_STATUS[current.case_status];
  const canAct = nextAction && availableActions.includes(nextAction);

  async function runAction(action) {
    setBusy(true);
    setError(null);
    try {
      const updated = await ACTION_FN[action](current.alert_id, actor, split);
      setCurrent(updated);
      onChange?.(updated);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="alert-card">
      <div className="alert-card__header">
        <span className="badge" style={{ background: SEVERITY_COLORS[current.severity] }}>
          {current.severity}
        </span>
        <span className="alert-type">{ALERT_TYPE_LABEL[current.alert_type] || current.alert_type}</span>
        <ScopeBadge alert={current} />
        <span className="muted">{current.agent_id} · {current.area}</span>
        <span className="muted alert-card__time">{formatDateTime(current.timestamp)}</span>
      </div>

      <AlertExplanation alertId={current.alert_id} split={split} />

      <ul className="evidence-list">
        {current.evidence.map((e, i) => (
          <li key={i}>{e}</li>
        ))}
      </ul>

      <div className="alert-card__meta">
        <div>
          <strong>Confidence:</strong> {(current.confidence * 100).toFixed(0)}% ({current.confidence_label})
        </div>
        <div>
          <strong>Cohort:</strong> {describeCohortContext(current.cohort_context, current.cohort_peer_count)}
        </div>
        <div>
          <strong>Routed to:</strong> {current.recommended_owner} · <strong>Recommended:</strong> {current.recommended_action}
        </div>
        {current.audience?.length > 0 && (
          <div className="audience-row">
            <strong>Visible to:</strong>
            {current.audience.map((role) => (
              <span key={role} className={`aud-chip${role === "provider_ops" ? " aud-chip--provider" : ""}`}>
                {ROLE_LABEL[role] || role}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="alert-card__lifecycle">
        <div className="case-status-row">
          <span className={`case-status case-status--${current.case_status}`}>{current.case_status}</span>
          {canAct && (
            <button disabled={busy} onClick={() => runAction(nextAction)} type="button">
              {busy ? "…" : ACTION_LABEL[nextAction]}
            </button>
          )}
        </div>
        {error && <div className="error-text">{error}</div>}
        <ol className="timeline">
          {current.case_history.map((h, i) => (
            <li key={i}>
              <span className="muted">{formatDateTime(h.timestamp)}</span> — {h.actor}: {h.action}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
