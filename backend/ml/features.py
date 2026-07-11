"""Stage 2b feature table: per-(agent, provider) hourly rows for the ML liquidity
comparison model (see ml/train.py). Built entirely on top of Stage 2's own
hourly aggregation (engine.liquidity, engine.cohort) so the comparison against
the EWMA baseline is apples-to-apples -- same rows, same burn_rate, same
cohort_z -- rather than a separately-aggregated feature set.
"""
import pandas as pd

from engine import cohort, liquidity

# Forecast horizon: predict balance this many hourly buckets ahead. 3h keeps
# a meaningful number of training rows per agent/provider (long horizons
# shrink the usable tail of every group) while still being far enough out
# that a naive "same as now" guess is a weak baseline.
HORIZON_HOURS = 3
ROLLING_WINDOW_HOURS = 3
LAG_HOURS = (1, 2)

NUMERIC_FEATURES = [
    "last_balance", "burn_rate", "ewm_std",
    "net_change_roll_mean", "net_change_roll_std", "n_txns_roll_mean",
    "hour_bucket", "cohort_z", "cohort_peer_count",
    "confidence", "gap_minutes", "balance_to_threshold_ratio",
    "has_duplicate", "balance_was_filled",
] + [f"last_balance_lag{h}" for h in LAG_HOURS]
CATEGORICAL_FEATURES = ["agent_id", "provider", "area", "day_type"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET_COLUMN = "balance_at_t_plus_h"
BASELINE_COLUMN = "baseline_pred"


def build_provider_features(raw_df, horizon_hours=HORIZON_HOURS):
    """One row per (agent_id, provider, hour_slot) with model features, the
    forward target, and the EWMA-extrapolation baseline prediction -- all
    derived from one split's transactions only (no cross-split leakage)."""
    cash = liquidity.compute_cash_forecast(raw_df)
    provider = liquidity.compute_provider_forecast(raw_df)
    combined = pd.concat([cash, provider], ignore_index=True)
    scored = cohort.compute_cohort(combined)

    prov = scored[scored["metric_level"] == "provider"].copy()
    prov = prov.sort_values(["agent_id", "provider", "hour_slot"], kind="stable")

    g = prov.groupby(["agent_id", "provider"], sort=False)
    prov["net_change_roll_mean"] = g["net_change"].transform(
        lambda s: s.rolling(ROLLING_WINDOW_HOURS, min_periods=1).mean()
    )
    prov["net_change_roll_std"] = g["net_change"].transform(
        lambda s: s.rolling(ROLLING_WINDOW_HOURS, min_periods=1).std()
    ).fillna(0)
    prov["n_txns_roll_mean"] = g["n_txns"].transform(
        lambda s: s.rolling(ROLLING_WINDOW_HOURS, min_periods=1).mean()
    )
    for h in LAG_HOURS:
        prov[f"last_balance_lag{h}"] = g["last_balance"].shift(h)

    # How close this row already is to its own (causal) safety threshold --
    # the one nonlinear signal neither burn_rate nor last_balance alone give:
    # a big burn_rate far from the threshold behaves very differently than
    # the same burn_rate right on top of it.
    prov["balance_to_threshold_ratio"] = prov["last_balance"] / prov["safety_threshold"]

    prov["has_duplicate"] = prov["has_duplicate"].astype(int)
    prov["balance_was_filled"] = prov["balance_was_filled"].astype(int)

    # Target: the actual realized balance `horizon_hours` buckets ahead in the
    # same (agent, provider) series. NaN (and dropped) for each group's last
    # `horizon_hours` rows, where that future isn't in this split.
    prov[TARGET_COLUMN] = g["last_balance"].shift(-horizon_hours)

    # Baseline: linear extrapolation of Stage 2's own EWMA burn_rate --
    # exactly what "burn_rate BDT/hour" already implies about the near
    # future, just carried out `horizon_hours` instead of left as a rate.
    prov[BASELINE_COLUMN] = prov["last_balance"] + prov["burn_rate"] * horizon_hours

    return prov


def build_training_frame(raw_df, horizon_hours=HORIZON_HOURS):
    """Feature table restricted to rows usable for training/evaluation:
    a real target and no missing feature values."""
    prov = build_provider_features(raw_df, horizon_hours)
    cols = FEATURE_COLUMNS + [TARGET_COLUMN, BASELINE_COLUMN, "hour_slot"]
    prov = prov.dropna(subset=cols)
    return prov
