"""File-backed data access for the dashboard API.

Alerts are read from and written back to Stage 3's JSON files (data/alerts_*.json)
-- this stays consistent with the rest of the pipeline's file-based approach.
Balances are derived read-only from Stage 1's raw transactions; nothing here
recomputes evidence, confidence, or routing, which come from Stage 2/3 as-is.
"""
import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

VALID_SPLITS = ("calibration", "holdout")


def _alerts_path(split):
    if split not in VALID_SPLITS:
        raise ValueError(f"unknown split: {split}")
    return DATA_DIR / f"alerts_{split}.json"


def load_alerts(split):
    with open(_alerts_path(split), encoding="utf-8") as f:
        return json.load(f)


def save_alerts(split, alerts):
    with open(_alerts_path(split), "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2, ensure_ascii=False)


def find_alert(split, alert_id):
    alerts = load_alerts(split)
    for a in alerts:
        if a["alert_id"] == alert_id:
            return alerts, a
    return alerts, None


def _raw_transactions(split):
    path = DATA_DIR / f"transactions_{split}.csv"
    return pd.read_csv(path, parse_dates=["timestamp"])


def list_agents(split):
    df = _raw_transactions(split)
    return (
        df[["agent_id", "area"]]
        .drop_duplicates()
        .sort_values("agent_id")
        .to_dict(orient="records")
    )


def agent_balances(split, agent_id):
    df = _raw_transactions(split)
    a = df[df["agent_id"] == agent_id].sort_values("timestamp")
    if a.empty:
        return None

    latest_cash_row = a.iloc[-1]
    providers = {}
    for provider, g in a.groupby("provider"):
        providers[provider] = {
            "balance": float(g.iloc[-1]["agent_provider_balance_after"]),
            "as_of": g.iloc[-1]["timestamp"].isoformat(),
        }

    return {
        "agent_id": agent_id,
        "area": latest_cash_row["area"],
        "cash": float(latest_cash_row["agent_cash_after"]),
        "cash_as_of": latest_cash_row["timestamp"].isoformat(),
        "providers": providers,
    }
