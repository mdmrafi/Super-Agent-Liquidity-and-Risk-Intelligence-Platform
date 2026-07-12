"""Anomaly rule (spec 6.4 / 5): near-identical amounts, few accounts, short window.

Detection is a greedy per-(agent, provider) scan: starting at each unclaimed
transaction, gather every later transaction within window_minutes whose
amount keeps the cluster's spread within tolerance. An interleaved
transaction that doesn't fit the pattern (an ordinary cash-in, an unrelated
cash-out) is skipped rather than treated as a cluster-breaker -- a customer
walking up mid-burst for an unrelated errand shouldn't hide a real pattern
among the surrounding near-identical amounts. Thresholds are calibrated once
on the calibration split (by F1 against is_injected_anomaly), locked, then
run unmodified on held-out.
"""
import pandas as pd

from . import config


def _detect_group(g, min_txns, window_minutes, pct_variation, max_accounts):
    """Return a list of clusters, each a list of row positions into g."""
    n = len(g)
    claimed = [False] * n
    clusters = []
    for i in range(n):
        if claimed[i]:
            continue
        members = [i]
        amounts = [g.loc[i, "amount"]]
        for j in range(i + 1, n):
            gap = (g.loc[j, "timestamp"] - g.loc[i, "timestamp"]).total_seconds() / 60
            if gap > window_minutes:
                break
            if claimed[j]:
                continue
            candidate = amounts + [g.loc[j, "amount"]]
            spread = (max(candidate) - min(candidate)) / (sum(candidate) / len(candidate))
            if spread > pct_variation:
                continue
            members.append(j)
            amounts.append(g.loc[j, "amount"])
        accounts = {g.loc[k, "customer_id"] for k in members}
        if len(members) >= min_txns and len(accounts) <= max_accounts:
            clusters.append(members)
            for k in members:
                claimed[k] = True
    return clusters


def detect(df, min_txns, window_minutes, pct_variation, max_accounts):
    """Return (window_df, flagged_transaction_ids) using only success transactions."""
    rows = []
    flagged_ids = set()
    success = df[df["status"] == "success"].sort_values("timestamp", kind="stable")

    for (agent_id, provider), g in success.groupby(["agent_id", "provider"], sort=False):
        g = g.sort_values("timestamp", kind="stable").reset_index(drop=True)
        for members in _detect_group(g, min_txns, window_minutes, pct_variation, max_accounts):
            window_ids = g.loc[members, "transaction_id"].tolist()
            flagged_ids.update(window_ids)
            amounts = g.loc[members, "amount"].tolist()
            accounts = set(g.loc[members, "customer_id"])
            txn_types = g.loc[members, "txn_type"].unique()
            label = f"{txn_types[0]}s" if len(txn_types) == 1 else "transactions"
            i, j = members[0], members[-1]
            span_minutes = (g.loc[j, "timestamp"] - g.loc[i, "timestamp"]).total_seconds() / 60
            avg_amount = sum(amounts) / len(amounts)
            rows.append({
                "agent_id": agent_id,
                "provider": provider,
                "area": g.loc[i, "area"],
                "timestamp": g.loc[j, "timestamp"],
                "hour_slot": g.loc[j, "timestamp"].floor("h"),
                "day_type": g.loc[i, "day_type"],
                "anomaly_evidence": (
                    f"{len(amounts)} {label}, avg {avg_amount:,.0f} BDT, "
                    f"{len(accounts)} account(s), {span_minutes:.0f}-minute window"
                ),
            })

    return pd.DataFrame(rows), flagged_ids


def score(df, flagged_ids):
    y_true = df["is_injected_anomaly"].astype(bool)
    y_pred = df["transaction_id"].isin(flagged_ids)
    tp = int((y_true & y_pred).sum())
    fp = int((~y_true & y_pred).sum())
    fn = int((y_true & ~y_pred).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def calibrate(df_calibration):
    """Grid-search thresholds on calibration only; return the locked best combo."""
    best = None
    for min_txns in config.ANOMALY_GRID["min_txns"]:
        for window_minutes in config.ANOMALY_GRID["window_minutes"]:
            for pct_variation in config.ANOMALY_GRID["pct_variation"]:
                for max_accounts in config.ANOMALY_GRID["max_accounts"]:
                    _, flagged_ids = detect(
                        df_calibration, min_txns, window_minutes, pct_variation, max_accounts
                    )
                    metrics = score(df_calibration, flagged_ids)
                    candidate = {
                        "min_txns": min_txns, "window_minutes": window_minutes,
                        "pct_variation": pct_variation, "max_accounts": max_accounts,
                        **metrics,
                    }
                    if best is None or candidate["f1"] > best["f1"]:
                        best = candidate
    return best
