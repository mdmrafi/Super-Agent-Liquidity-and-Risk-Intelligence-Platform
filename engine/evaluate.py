"""Held-out metrics (spec section 11) -- run once, after thresholds are locked."""
import numpy as np
import pandas as pd

from . import anomaly, config


def provider_balance_error(calibration_scored, holdout_scored):
    """MAE of net_change per (provider, hour_bucket, day_type) cell, calibration vs holdout."""
    prov_cal = calibration_scored[calibration_scored["provider"].notna()].copy()
    prov_hold = holdout_scored[holdout_scored["provider"].notna()].copy()
    for d in (prov_cal, prov_hold):
        d["hour_bucket"] = pd.to_datetime(d["timestamp"]).dt.hour

    key = ["provider", "hour_bucket"]
    forecast = prov_cal.groupby(key)["net_change"].mean().rename("forecast")
    actual = prov_hold.groupby(key)["net_change"].mean().rename("actual")
    joined = pd.concat([forecast, actual], axis=1).dropna()
    mae = (joined["forecast"] - joined["actual"]).abs().mean()
    return {"mae_bdt_per_hour": float(mae), "cells_compared": int(len(joined))}


def shortage_lead_time(holdout_raw, holdout_scored, agent_id, safety_fraction=config.CASH_SAFETY_FRACTION):
    """For a known agent, how much earlier did the forecast see the shortage coming
    vs. when cash actually crossed the safety threshold (same relative-threshold
    definition the engine itself uses: a fraction of the agent's own rolling peak,
    applied here at transaction-level granularity rather than hourly)."""
    raw = holdout_raw[holdout_raw["agent_id"] == agent_id].sort_values("timestamp").copy()
    raw["rolling_max_cash"] = raw["agent_cash_after"].cummax()
    crossed = raw[raw["agent_cash_after"] <= safety_fraction * raw["rolling_max_cash"]]
    if crossed.empty:
        return {"status": "no_crossing_observed"}
    actual_cross_time = crossed["timestamp"].iloc[0]

    rows = holdout_scored[
        (holdout_scored["agent_id"] == agent_id) & (holdout_scored["provider"].isna())
    ].sort_values("timestamp")

    for _, row in rows.iterrows():
        ts = pd.Timestamp(row["timestamp"])
        if ts >= actual_cross_time:
            break
        predicted_cross = ts + pd.Timedelta(minutes=row["time_to_shortage_minutes"])
        if row["time_to_shortage_minutes"] < config.TIME_TO_SHORTAGE_CAP_MINUTES and predicted_cross <= actual_cross_time + pd.Timedelta(hours=1):
            lead_minutes = (actual_cross_time - ts).total_seconds() / 60
            return {
                "status": "detected",
                "first_warning_at": str(ts),
                "actual_crossing_at": str(actual_cross_time),
                "lead_time_minutes": lead_minutes,
            }
    return {"status": "not_detected_before_crossing", "actual_crossing_at": str(actual_cross_time)}


def anomaly_metrics_holdout(holdout_raw, locked_params):
    _, flagged_ids = anomaly.detect(holdout_raw, **{
        k: locked_params[k] for k in ("min_txns", "window_minutes", "pct_variation", "max_accounts")
    })
    return anomaly.score(holdout_raw, flagged_ids), flagged_ids


def false_positive_rate_on_spike(holdout_raw, flagged_ids, day_type="eid"):
    subset = holdout_raw[
        (holdout_raw["day_type"] == day_type) & (~holdout_raw["is_injected_anomaly"].astype(bool))
    ]
    if subset.empty:
        return {"status": "no_rows_for_day_type"}
    flagged = subset["transaction_id"].isin(flagged_ids)
    return {
        "day_type": day_type,
        "n_transactions": int(len(subset)),
        "n_false_positives": int(flagged.sum()),
        "false_positive_rate": float(flagged.mean()),
    }


def explanation_coverage(scored):
    has_confidence = scored["confidence"].notna().mean()
    anomalous = scored[scored["is_anomalous"]]
    has_evidence = anomalous["anomaly_evidence"].apply(len).gt(0).mean() if len(anomalous) else 1.0
    return {"confidence_populated_pct": float(has_confidence * 100), "evidence_populated_pct": float(has_evidence * 100)}
