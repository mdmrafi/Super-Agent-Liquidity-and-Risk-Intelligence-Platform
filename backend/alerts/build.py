"""Turn Stage 2 records into formal Alert objects (spec section 7).

Three independent triggers, checked per Stage 2 row -- a row can produce more
than one alert if more than one condition applies (e.g. Scenario B's agent
is under both liquidity pressure and an anomaly burst at once; those are two
distinct concerns with two distinct case lifecycles, not one merged alert):

  time_to_shortage_minutes < LIQUIDITY_TRIGGER_MINUTES,  -> liquidity_shortage
    debounced (2+ consecutive hours, fires once per episode)
  is_anomalous == True                                   -> unusual_activity
  provider-level row overlapping a Stage-1 data fault     -> data_quality

The liquidity trigger is debounced: a single noisy EWMA blip on an otherwise
healthy agent (ordinary random-walk variance dipping under the trigger for one
hour) would otherwise produce a high-severity, replenishment-requesting alert
indistinguishable from genuine sustained pressure. Measured directly against
this dataset: ~58 of ~84 high-severity liquidity episodes were single-hour
noise on agents never touched by any Stage 1 injection. Requiring 2+
consecutive crossings, firing once at confirmation rather than every hour the
episode continues, is a deliberate addition beyond the literal severity table
(which only gates on time_to_shortage/confidence) -- confirmed with the user
before adding it, since it's a real detection-sensitivity tradeoff, not a bug.

recommended_owner is carried through unchanged from Stage 2 -- never
recomputed here, per the master spec's routing-is-deterministic rule.

  data_quality is derived only from observable ledger defects: missing balance
  readings, duplicate transaction fingerprints, and broken provider-balance
  continuity after timestamp delays. Synthetic ground-truth labels are used
  only for evaluation and never participate in alert generation.
Severity and recommended_action for data_quality aren't covered by the given
table (it only covers liquidity/anomaly) -- assumption: severity follows
confidence_label (lower confidence = worse trust = higher severity), action
is always review_evidence (there's no "replenishment" or "contact_agent"
concept for a feed problem).

Additive field: "cohort_peer_count" is not in section 7's literal schema, but
carried through from Stage 2 so Stage 4 can render cohort_context plainly
("similar to 6 nearby agents") instead of the raw enum string.

Additive field: "liquidity_type" ("physical_cash" | "provider_emoney", None for
non-liquidity alerts) makes the mandatory "which provider OR shared cash reserve"
distinction explicit on the object and in the evidence text, instead of leaving
it implicit in whether `provider` is null.

Additive field: "audience" (list of roles who should *see* the alert, distinct
from the single "recommended_owner" who acts on it). A physical-cash shortage is
the agent's own drawer -- agent-side only, never provider operations. An e-money
shortage concerns the provider's float, so it reaches both the agent side and
provider_ops. See _audience() / _effective_owner().
"""
import pandas as pd

from . import config


def _liquidity_severity(minutes):
    if minutes < config.LIQUIDITY_HIGH_MINUTES:
        return "high"
    if minutes < config.LIQUIDITY_MEDIUM_MINUTES:
        return "medium"
    return "low"


_DATA_QUALITY_SEVERITY = {"low": "high", "medium": "medium", "high": "low"}


def _recommended_action(alert_type, severity):
    if severity == "high":
        return "request_replenishment_support" if alert_type == "liquidity_shortage" else "review_evidence"
    if severity == "medium":
        return "contact_agent"
    return "review_evidence"


def _effective_owner(alert_type, liquidity_type, owner):
    """Physical cash is the agent's own drawer, never a provider-operations
    concern -- so a shared-cash shortage never *owns* to provider_ops even if
    the cohort layer had widened it. Documented exception to the "owner carried
    unchanged from Stage 2" rule below: the physical/e-money split is itself a
    Stage 3 concept, so correcting an impossible physical-cash->provider_ops
    routing belongs here."""
    if alert_type == "liquidity_shortage" and liquidity_type == "physical_cash" and owner == "provider_ops":
        return "field_officer"
    return owner


def _audience(alert_type, liquidity_type, owner):
    """Who the warning should be *visible* to -- distinct from who owns/acts on
    it. Mirrors a real agent shop:

      - the agent always sees alerts about their own shop;
      - the routed agent-side owner (field_officer / area_team / risk_team) sees it;
      - provider operations see a liquidity alert ONLY when it concerns their
        provider's e-money float -- never the agent's physical cash drawer.

    So a physical_cash shortage is agent-side only; a provider_emoney shortage
    reaches both the agent (side) and provider_ops.
    """
    audience = ["agent", owner]
    if owner == "field_officer":
        audience.append("area_team")
    if alert_type == "liquidity_shortage" and liquidity_type == "provider_emoney":
        audience.append("provider_ops")
    deduped = []
    for role in audience:
        if role and role not in deduped:
            deduped.append(role)
    return deduped


def _display_status(action):
    return "constrained — replenishment requested" if action == "request_replenishment_support" else "normal"


def _liquidity_type(provider):
    """Which pool is under pressure: the agent's shared physical cash drawer
    (provider is None -- the __cash__ forecast series) or one provider's
    e-money float. Kept explicit so the alert states the type, rather than
    leaving it implicit in whether `provider` happens to be null."""
    return "physical_cash" if provider is None else "provider_emoney"


def _liquidity_evidence(row, liquidity_type):
    scope = (
        "shared physical cash reserve"
        if liquidity_type == "physical_cash"
        else f"{row['provider']} e-money balance"
    )
    return [
        f"{scope}: burn_rate {row['burn_rate']:,.0f} BDT/hour, "
        f"time_to_shortage {row['time_to_shortage_minutes']:.0f} minutes, "
        f"confidence {row['confidence']:.0%}"
    ]


def _data_quality_evidence(n_fault_signals, confidence):
    return [
        f"{n_fault_signals} observable ledger issue(s) in this window: missing "
        f"balance, duplicate record, or broken balance continuity; confidence "
        f"reduced to {confidence:.0%}"
    ]


def _base_alert(row, alert_type, severity, evidence, liquidity_type=None):
    action = _recommended_action(alert_type, severity)
    owner = _effective_owner(alert_type, liquidity_type, row["recommended_owner"])
    return {
        "alert_id": None,  # assigned by build_alerts once the alert is confirmed
        "agent_id": row["agent_id"],
        "provider": row["provider"],
        "area": row["area"],
        "timestamp": row["timestamp"],
        "alert_type": alert_type,
        "liquidity_type": liquidity_type,  # set only for liquidity_shortage; None otherwise
        "severity": severity,
        "evidence": evidence,
        "confidence": row["confidence"],
        "confidence_label": row["confidence_label"],
        "cohort_context": row["cohort_context"],
        "cohort_peer_count": row["cohort_peer_count"],
        "recommended_owner": owner,
        "audience": _audience(alert_type, liquidity_type, owner),
        "recommended_action": action,
        "display_status": _display_status(action),
        "case_status": "new",
        "case_history": [
            {"timestamp": row["timestamp"], "actor": "system", "action": "created (new)"}
        ],
    }


_DUPLICATE_FINGERPRINT = [
    "agent_id", "provider", "timestamp", "txn_type", "amount", "status",
    "customer_id", "agent_cash_before", "agent_cash_after",
    "agent_provider_balance_before", "agent_provider_balance_after",
]


def _observable_fault_counts_by_hour(raw_df):
    """Count data-quality signals without consulting injected truth labels."""
    d = raw_df.copy()
    d["hour_slot"] = pd.to_datetime(d["timestamp"]).dt.floor("h")
    d["duplicate_record"] = d.duplicated(
        subset=_DUPLICATE_FINGERPRINT, keep=False
    )
    d["missing_balance"] = d[
        ["agent_provider_balance_before", "agent_provider_balance_after"]
    ].isna().any(axis=1)

    ordered = d.sort_values(
        ["agent_id", "provider", "timestamp", "transaction_id"],
        kind="stable",
    )
    previous_balance = ordered.groupby(
        ["agent_id", "provider"], sort=False
    )["agent_provider_balance_after"].shift()
    ordered["broken_continuity"] = (
        previous_balance.notna()
        & ordered["agent_provider_balance_before"].notna()
        & (
            ordered["agent_provider_balance_before"] - previous_balance
        ).abs().gt(0.01)
    )
    d["broken_continuity"] = ordered["broken_continuity"].reindex(
        d.index, fill_value=False
    )
    d["observable_fault_count"] = d[
        ["duplicate_record", "missing_balance", "broken_continuity"]
    ].sum(axis=1)
    faults = d[d["observable_fault_count"] > 0]
    return faults.groupby(
        ["agent_id", "provider", "hour_slot"]
    )["observable_fault_count"].sum()


_CASH_KEY = "__cash__"


def _provider_key(provider):
    return _CASH_KEY if provider is None or pd.isna(provider) else provider


def _debounced_liquidity_keys(scored_records):
    """(agent_id, provider_key, timestamp) keys where a liquidity episode is
    confirmed -- 2+ consecutive contiguous hourly crossings -- returning only
    the confirming row of each episode, not every row while it continues."""
    df = pd.DataFrame(scored_records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["provider_key"] = df["provider"].apply(_provider_key)
    df["crossed"] = df["time_to_shortage_minutes"] < config.LIQUIDITY_TRIGGER_MINUTES

    confirmed = set()
    for (agent_id, provider_key), g in df.groupby(["agent_id", "provider_key"], sort=False):
        g = g.sort_values("timestamp")
        streak = 0
        prev_ts = None
        alerted_this_episode = False
        for _, r in g.iterrows():
            contiguous = prev_ts is not None and (r["timestamp"] - prev_ts) <= pd.Timedelta(hours=1.5)
            if r["crossed"]:
                streak = streak + 1 if contiguous else 1
            else:
                streak = 0
                alerted_this_episode = False
            if r["crossed"] and streak >= 2 and not alerted_this_episode:
                confirmed.add((agent_id, provider_key, r["timestamp"]))
                alerted_this_episode = True
            prev_ts = r["timestamp"]
    return confirmed


def _maybe_liquidity_alert(row, ts, liquidity_keys):
    key = (row["agent_id"], _provider_key(row["provider"]), ts)
    if key not in liquidity_keys:
        return None
    severity = _liquidity_severity(row["time_to_shortage_minutes"])
    liquidity_type = _liquidity_type(row["provider"])
    evidence = _liquidity_evidence(row, liquidity_type)
    return _base_alert(row, "liquidity_shortage", severity, evidence, liquidity_type=liquidity_type)


def _maybe_anomaly_alert(row):
    if not row["is_anomalous"]:
        return None
    severity = row["confidence_label"]
    evidence = row["anomaly_evidence"] or ["unusual transaction pattern detected"]
    return _base_alert(row, "unusual_activity", severity, evidence)


def _maybe_data_quality_alert(row, ts, fault_counts):
    if row["provider"] is None:
        return None
    n_faults = fault_counts.get((row["agent_id"], row["provider"], ts), 0)
    if n_faults <= 0:
        return None
    severity = _DATA_QUALITY_SEVERITY[row["confidence_label"]]
    return _base_alert(row, "data_quality", severity, _data_quality_evidence(n_faults, row["confidence"]))


def build_alerts(scored_records, raw_df, id_prefix=""):
    fault_counts = _observable_fault_counts_by_hour(raw_df)
    liquidity_keys = _debounced_liquidity_keys(scored_records)
    alerts = []
    counter = 1

    for row in scored_records:
        ts = pd.Timestamp(row["timestamp"])
        candidates = (
            _maybe_liquidity_alert(row, ts, liquidity_keys),
            _maybe_anomaly_alert(row),
            _maybe_data_quality_alert(row, ts, fault_counts),
        )
        for candidate in candidates:
            if candidate is not None:
                candidate["alert_id"] = f"alert_{id_prefix}{counter:05d}"
                alerts.append(candidate)
                counter += 1

    return alerts
