"""Peer-cohort layer (spec 6.2): cohort_z against peers, with self-history fallback.

Compared metric is net_change (the realized hourly balance delta), not the
EWMA-smoothed burn_rate -- burn_rate already blends each agent's own past, so
comparing it cross-agent at a single hour would mix unevenly-aged history.
net_change is the apples-to-apples same-hour value.

Cohort stats are pooled including the row's own agent (a simplification --
true leave-one-out would exclude it) since with >=3 peers required this bias
is minor at this dataset's scale.
"""
import numpy as np
import pandas as pd

from . import config

PROVIDER_COHORT_KEY = ["provider", "area", "hour_bucket", "day_type"]
CASH_COHORT_KEY = ["area", "hour_bucket", "day_type"]


def _score_level(sub, cohort_key_cols, self_key_cols):
    cohort_group = sub.groupby(cohort_key_cols)["net_change"]
    cohort_mean = cohort_group.transform("mean")
    cohort_std = cohort_group.transform("std").fillna(0)
    peer_count = sub.groupby(cohort_key_cols)["agent_id"].transform("nunique") - 1

    self_group = sub.groupby(self_key_cols)["net_change"]
    self_mean = self_group.transform("mean")
    self_std = self_group.transform("std").fillna(0)

    use_fallback = peer_count < config.MIN_COHORT_PEERS
    ref_mean = np.where(use_fallback, self_mean, cohort_mean)
    ref_std = np.where(use_fallback, self_std, cohort_std)
    floor = np.maximum(np.abs(ref_mean) * 0.1, 50.0)
    z = (sub["net_change"].to_numpy() - ref_mean) / np.maximum(ref_std, floor)

    sub = sub.copy()
    sub["cohort_z"] = z
    sub["cohort_peer_count"] = peer_count.to_numpy()
    sub["cohort_context"] = np.where(use_fallback, "self_history_fallback", "agent_only")
    return sub


def _resolve_shared_context(df):
    df = df.copy()
    df["flagged"] = df["cohort_z"].abs() > config.Z_THRESHOLD
    flagged = df[df["flagged"]]

    area_counts = flagged.groupby(["area", "hour_bucket", "day_type"])["agent_id"].nunique()
    df["_area_flagged"] = pd.Series(
        list(zip(df["area"], df["hour_bucket"], df["day_type"]))
    ).map(area_counts.to_dict()).fillna(0).to_numpy()

    provider_flagged = flagged[flagged["metric_level"] == "provider"]
    provider_counts = provider_flagged.groupby(["provider", "hour_bucket", "day_type"])["agent_id"].nunique()
    df["_provider_flagged"] = pd.Series(
        list(zip(df["provider"], df["hour_bucket"], df["day_type"]))
    ).map(provider_counts.to_dict()).fillna(0).to_numpy()

    def resolve(row):
        if row["cohort_context"] == "self_history_fallback" or not row["flagged"]:
            return row["cohort_context"] if row["cohort_context"] == "self_history_fallback" else "agent_only"
        other_area = row["_area_flagged"] - 1
        other_provider = (row["_provider_flagged"] - 1) if row["metric_level"] == "provider" else 0
        if other_area >= config.MIN_SHARED_PEERS_FOR_WIDE:
            return "area_wide"
        if other_provider >= config.MIN_SHARED_PEERS_FOR_WIDE:
            return "provider_wide"
        return "agent_only"

    df["cohort_context"] = df.apply(resolve, axis=1)
    return df.drop(columns=["_area_flagged", "_provider_flagged", "flagged"])


def compute_cohort(df):
    provider_rows = _score_level(
        df[df["metric_level"] == "provider"],
        PROVIDER_COHORT_KEY,
        ["agent_id", "provider", "hour_bucket", "day_type"],
    )
    cash_rows = _score_level(
        df[df["metric_level"] == "cash"],
        CASH_COHORT_KEY,
        ["agent_id", "hour_bucket", "day_type"],
    )
    combined = pd.concat([provider_rows, cash_rows]).sort_index()
    return _resolve_shared_context(combined)
