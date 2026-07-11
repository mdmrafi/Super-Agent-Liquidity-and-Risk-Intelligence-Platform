"""Orchestrates liquidity + cohort + anomaly + routing into the Stage 2 output contract.

{
  "agent_id", "provider", "area", "timestamp",
  "burn_rate", "time_to_shortage_minutes",
  "confidence", "confidence_label",
  "cohort_z", "cohort_context",
  "is_anomalous", "anomaly_evidence",
  "recommended_owner"
}

Deviation flagged: "provider" is null on shared-cash rows. The contract has
one row shape for both per-provider balance forecasts and the per-agent
shared-cash forecast (needed so Scenario A's hidden shortage -- cash draining
while one provider's own balance rises -- is even representable). Using
provider=null for cash rows keeps the field set identical without adding a
new field, at the cost of "provider" no longer being strictly the section
4.2 enum on every row.
"""
import pandas as pd

from . import anomaly, cohort, liquidity, routing

# Spec 6.2: "fewer than 3 peers -> fall back to self-history, mark confidence
# as lower." The liquidity forecast computes confidence before cohort_context
# is known, so the fallback penalty is applied here, after cohort scoring.
SELF_HISTORY_CONFIDENCE_PENALTY = 0.20

CONTRACT_COLUMNS = [
    "agent_id", "provider", "area", "timestamp",
    "burn_rate", "time_to_shortage_minutes",
    "confidence", "confidence_label",
    "cohort_z", "cohort_context",
    "is_anomalous", "anomaly_evidence",
    "recommended_owner",
]


def _attach_anomalies(forecast_df, anomaly_windows):
    forecast_df = forecast_df.copy()
    forecast_df["is_anomalous"] = False
    forecast_df["anomaly_evidence"] = [[] for _ in range(len(forecast_df))]

    if anomaly_windows.empty:
        return forecast_df

    key = anomaly_windows.set_index(["agent_id", "provider", "hour_slot"])["anomaly_evidence"]
    for (agent_id, provider, hour_slot), evidence in key.items():
        mask = (
            (forecast_df["agent_id"] == agent_id)
            & (forecast_df["provider"] == provider)
            & (forecast_df["hour_slot"] == hour_slot)
        )
        forecast_df.loc[mask, "is_anomalous"] = True
        idx = forecast_df.index[mask]
        for i in idx:
            forecast_df.at[i, "anomaly_evidence"] = forecast_df.at[i, "anomaly_evidence"] + [evidence]
    return forecast_df


def run_split(df, locked_anomaly_params):
    """Full Stage 2 computation for one split's transaction DataFrame."""
    cash = liquidity.compute_cash_forecast(df)
    provider = liquidity.compute_provider_forecast(df)
    combined = pd.concat([cash, provider], ignore_index=True)

    scored = cohort.compute_cohort(combined)

    fallback = scored["cohort_context"] == "self_history_fallback"
    scored.loc[fallback, "confidence"] = (
        scored.loc[fallback, "confidence"] - SELF_HISTORY_CONFIDENCE_PENALTY
    ).clip(lower=0.05)
    scored["confidence_label"] = scored["confidence"].apply(liquidity.confidence_label)

    anomaly_windows, _ = anomaly.detect(df, **{
        k: locked_anomaly_params[k]
        for k in ("min_txns", "window_minutes", "pct_variation", "max_accounts")
    })
    scored = _attach_anomalies(scored, anomaly_windows)

    scored["recommended_owner"] = scored.apply(
        lambda r: routing.recommend_owner(r["cohort_context"], r["is_anomalous"]), axis=1
    )
    scored["timestamp"] = scored["hour_slot"]

    return scored[CONTRACT_COLUMNS + ["hour_slot", "last_balance", "net_change"]].sort_values(
        "timestamp", kind="stable"
    ).reset_index(drop=True)
