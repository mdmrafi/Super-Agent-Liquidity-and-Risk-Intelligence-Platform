"""File-backed data access for the dashboard API.

Alerts are read from and written back to Stage 3's JSON files (data/alerts_*.json)
-- this stays consistent with the rest of the pipeline's file-based approach.
Balances are derived read-only from Stage 1's raw transactions; nothing here
recomputes evidence, confidence, or routing, which come from Stage 2/3 as-is.
"""
import json
import threading
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


# Parsed once per split and reused. The raw transaction ledger is a Stage 1
# build artifact -- read-only for the lifetime of the server, never written
# back (only alerts_*.json is mutated, by save_alerts). Re-reading and
# re-parsing the ~2 MB CSV on every request was both wasteful and, inside the
# already memory-heavy API worker, enough to trip pandas' C parser into an
# out-of-memory error under load. Callers below only filter / group / sort
# (all of which return new frames), so sharing one cached frame is safe.
_TXN_CACHE: dict[str, "pd.DataFrame"] = {}
_TXN_LOCK = threading.Lock()


def _raw_transactions(split):
    if split not in VALID_SPLITS:
        raise ValueError(f"unknown split: {split}")
    # Sync FastAPI endpoints run in a threadpool, so a cold page load can hit
    # this from two threads at once (meta + balances). The lock makes the CSV
    # parse happen exactly once instead of racing two concurrent parses -- the
    # very concurrency that spiked memory before.
    with _TXN_LOCK:
        if split not in _TXN_CACHE:
            path = DATA_DIR / f"transactions_{split}.csv"
            _TXN_CACHE[split] = pd.read_csv(path, parse_dates=["timestamp"])
        return _TXN_CACHE[split]


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
