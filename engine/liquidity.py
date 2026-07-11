"""Liquidity forecast (spec 6.1): EWMA burn_rate, time_to_shortage, confidence.

Computed at two levels, both needed to catch a "hidden shortage" (Scenario A):
cash_out concentrated on one provider drains an agent's *shared cash* while
that same provider's own balance rises -- a provider-only forecast would miss
it entirely, so cash is forecast per-agent (provider=None) alongside each
per-(agent, provider) balance forecast.
"""
import numpy as np
import pandas as pd

from . import config


def _build_hourly_series(df, group_cols, before_col, after_col):
    """One row per (group, hour_slot) with net balance change and data-quality signals."""
    d = df.sort_values("timestamp", kind="stable").copy()
    d["delta"] = (d[after_col] - d[before_col]).fillna(0)
    d["is_dup"] = d.duplicated(subset=["transaction_id"], keep=False)
    d["is_null_balance"] = d[after_col].isna()

    agg = d.groupby(group_cols + ["hour_slot"], sort=True).agg(
        net_change=("delta", "sum"),
        n_txns=("transaction_id", "count"),
        has_duplicate=("is_dup", "any"),
        has_null_balance=("is_null_balance", "any"),
        area=("area", "first"),
        day_type=("day_type", "first"),
    ).reset_index()

    # last known (non-null) balance observed in each hour, so a corrupted
    # final reading in an hour doesn't silently propagate a NaN balance
    last_balance = (
        d[d[after_col].notna()]
        .groupby(group_cols + ["hour_slot"], sort=True)[after_col]
        .last()
        .rename("last_balance")
    )
    agg = agg.merge(last_balance, on=group_cols + ["hour_slot"], how="left")
    agg["hour_bucket"] = agg["hour_slot"].dt.hour

    # forward-fill balance level across hours per group when an hour's only
    # readings were corrupted (null) -- track that it happened, it's a
    # genuine data-quality signal, not something to hide
    agg = agg.sort_values(group_cols + ["hour_slot"], kind="stable")
    agg["balance_was_filled"] = agg["last_balance"].isna()
    agg["last_balance"] = agg.groupby(group_cols, sort=False)["last_balance"].ffill()

    return agg


def _staleness_minutes(agg, group_cols):
    agg = agg.sort_values(group_cols + ["hour_slot"], kind="stable").copy()
    prev_slot = agg.groupby(group_cols, sort=False)["hour_slot"].shift(1)
    gap = (agg["hour_slot"] - prev_slot).dt.total_seconds() / 60
    agg["gap_minutes"] = gap.fillna(0)
    return agg


def _confidence(row):
    cv = abs(row["ewm_std"]) / (abs(row["ewm_mean"]) + 1e-6)
    variance_penalty = min(cv, 2.0) / 2.0 * 0.35

    gap_hours = row["gap_minutes"] / 60.0
    staleness_penalty = 0.0
    if gap_hours > config.STALENESS_PENALTY_START_HOURS:
        staleness_penalty = min((gap_hours - config.STALENESS_PENALTY_START_HOURS) / 12.0, 1.0) * 0.25

    quality_penalty = 0.0
    if row["has_duplicate"] or row["balance_was_filled"]:
        quality_penalty = 0.20

    confidence = 0.90 - variance_penalty - staleness_penalty - quality_penalty
    return float(np.clip(confidence, 0.05, 0.95))


def confidence_label(c):
    if c >= 0.7:
        return "high"
    if c >= 0.4:
        return "medium"
    return "low"


def compute_forecast(df, group_cols, before_col, after_col, safety_fraction):
    agg = _build_hourly_series(df, group_cols, before_col, after_col)
    agg = _staleness_minutes(agg, group_cols)
    agg = agg.sort_values(group_cols + ["hour_slot"], kind="stable")

    # relative safety threshold: a fraction of this agent's own *recent* peak
    # balance (trailing window, causal -- no lookahead), not a flat
    # platform-wide figure and not an all-time cummax. An all-time max is a
    # bad reference: a single early lucky peak sets a permanent ceiling that
    # ordinary multi-day random-walk drift repeatedly dips below, and it's
    # especially unstable in an agent's first few hours of history (a
    # near-zero-sample "peak"). min_periods holds off producing a threshold
    # at all until there's enough history to trust it -- see the cap fallback
    # below. Window is row-count-based (hourly-bucketed rows have gaps), an
    # approximation of a true wall-clock trailing window.
    rolling_max = agg.groupby(group_cols, sort=False)["last_balance"].transform(
        lambda s: s.rolling(window=24, min_periods=6).max()
    )
    safety_threshold = safety_fraction * rolling_max
    agg["safety_threshold"] = safety_threshold

    span = config.EWMA_SPAN_HOURS
    ewm = agg.groupby(group_cols, sort=False)["net_change"]
    agg["ewm_mean"] = ewm.transform(lambda s: s.ewm(span=span, adjust=False).mean())
    agg["ewm_std"] = ewm.transform(lambda s: s.ewm(span=span, adjust=False).std()).fillna(0)

    agg["burn_rate"] = agg["ewm_mean"]  # net BDT/hour; negative = depleting
    burn_per_minute = agg["burn_rate"] / 60.0

    depleting = burn_per_minute < -1e-9
    minutes_to_threshold = (agg["last_balance"] - safety_threshold) / (-burn_per_minute.where(depleting))
    minutes_to_threshold = minutes_to_threshold.clip(lower=0)
    agg["time_to_shortage_minutes"] = minutes_to_threshold.where(
        depleting, config.TIME_TO_SHORTAGE_CAP_MINUTES
    ).fillna(config.TIME_TO_SHORTAGE_CAP_MINUTES)

    agg["confidence"] = agg.apply(_confidence, axis=1)
    agg["confidence_label"] = agg["confidence"].apply(confidence_label)

    return agg


def compute_cash_forecast(df):
    out = compute_forecast(
        df, group_cols=["agent_id"],
        before_col="agent_cash_before", after_col="agent_cash_after",
        safety_fraction=config.CASH_SAFETY_FRACTION,
    )
    out["provider"] = None
    out["metric_level"] = "cash"
    return out


def compute_provider_forecast(df):
    out = compute_forecast(
        df, group_cols=["agent_id", "provider"],
        before_col="agent_provider_balance_before", after_col="agent_provider_balance_after",
        safety_fraction=config.PROVIDER_SAFETY_FRACTION,
    )
    out["metric_level"] = "provider"
    return out
