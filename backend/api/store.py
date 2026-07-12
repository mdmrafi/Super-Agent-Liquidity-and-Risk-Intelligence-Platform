"""File-backed data access for the dashboard API.

Alerts are read from and written back to Stage 3's JSON files (data/alerts_*.json)
-- this stays consistent with the rest of the pipeline's file-based approach.
Balances are derived read-only from Stage 1's raw transactions; nothing here
recomputes evidence, confidence, or routing, which come from Stage 2/3 as-is.
"""
import json
import threading
from datetime import timedelta
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
_TXN_MTIME: dict[str, int] = {}
_TXN_LOCK = threading.Lock()


def _raw_transactions(split):
    if split not in VALID_SPLITS:
        raise ValueError(f"unknown split: {split}")
    # Sync FastAPI endpoints run in a threadpool, so a cold page load can hit
    # this from two threads at once (meta + balances). The lock makes the CSV
    # parse happen exactly once instead of racing two concurrent parses -- the
    # very concurrency that spiked memory before.
    with _TXN_LOCK:
        path = DATA_DIR / f'transactions_{split}.csv'
        mtime = path.stat().st_mtime_ns
        if split in _TXN_CACHE and _TXN_MTIME.get(split) != mtime:
            del _TXN_CACHE[split]
        if split not in _TXN_CACHE:
            path = DATA_DIR / f"transactions_{split}.csv"
            _TXN_CACHE[split] = pd.read_csv(path, parse_dates=["timestamp"])
        _TXN_MTIME[split] = mtime
        return _TXN_CACHE[split]


def list_agents(split):
    df = _raw_transactions(split)
    return (
        df[["agent_id", "area"]]
        .drop_duplicates()
        .sort_values("agent_id")
        .to_dict(orient="records")
    )


def list_providers(split):
    df = _raw_transactions(split)
    return sorted(df["provider"].dropna().unique().tolist())


def _number_or_none(value):
    return None if pd.isna(value) else float(value)


def _analytics_bucket(bucket_start, rows, window_minutes):
    closing_row = rows.iloc[-1]
    provider_balances = {}
    provider_counts = {}

    for provider, provider_rows in rows.groupby('provider', sort=True):
        provider_closing_row = provider_rows.iloc[-1]
        provider_balances[provider] = {
            'balance': _number_or_none(
                provider_closing_row['agent_provider_balance_after']
            ),
            'as_of': provider_closing_row['timestamp'].isoformat(),
        }
        provider_counts[provider] = int(len(provider_rows))

    return {
        'bucket_start': bucket_start.isoformat(),
        'bucket_end': (
            bucket_start + timedelta(minutes=window_minutes)
        ).isoformat(),
        'cash_closing_balance': _number_or_none(
            closing_row['agent_cash_after']
        ),
        'cash_as_of': closing_row['timestamp'].isoformat(),
        'provider_closing_balances': provider_balances,
        'transaction_count': int(len(rows)),
        'provider_transaction_counts': provider_counts,
    }


def agent_analytics(split, agent_id, window_minutes=30, limit=96, provider=None):
    '''Build observed buckets without filling or forecasting missing intervals.

    Provider filtering happens before newest-bucket selection so the limit
    always applies to the caller-visible provider history.
    '''
    if (
        not isinstance(window_minutes, int)
        or isinstance(window_minutes, bool)
        or window_minutes < 1
    ):
        raise ValueError('window_minutes must be a positive integer')
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError('limit must be a positive integer')

    df = _raw_transactions(split)
    all_rows = (
        df[df['agent_id'] == agent_id]
        .sort_values('timestamp', kind='stable')
        .copy()
    )
    if all_rows.empty:
        return None

    result = {
        'agent_id': agent_id,
        'area': all_rows.iloc[-1]['area'],
        'split': split,
        'window_minutes': window_minutes,
        'data_source': 'transaction_ledger',
        'observed_only': True,
        'buckets': [],
    }
    rows = all_rows
    if provider is not None:
        rows = rows[rows['provider'] == provider].copy()
    if rows.empty:
        return result

    rows['_bucket_start'] = rows['timestamp'].dt.floor(
        f'{window_minutes}min'
    )
    newest_starts = (
        rows['_bucket_start']
        .drop_duplicates()
        .sort_values()
        .iloc[-limit:]
    )
    selected = rows[rows['_bucket_start'].isin(newest_starts)]
    result['buckets'] = [
        _analytics_bucket(bucket_start, bucket_rows, window_minutes)
        for bucket_start, bucket_rows
        in selected.groupby('_bucket_start', sort=True)
    ]
    return result


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
