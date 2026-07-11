"""Injected scenarios A-D and the labeled anomaly / data-fault patterns (spec section 5).

Scenario A (hidden shortage) and B (pressure + anomaly) are injected as real,
valid transactions *before* balance replay, so they still reconcile like any
other transaction -- the "hidden" part is that cash_out concentrated on one
provider drains shared cash while that provider's own balance rises, so a
naive per-provider view looks fine while the shared-cash view does not.

Scenario C (data inconsistency) is applied *after* reconciliation has been
verified, as an export-time transformation on a copy of the clean ledger --
it deliberately breaks the replay invariant, which is the point of a data
fault, so it must never be fed back into the reconciliation check.

Scenario D (coordination) needs no special data -- it is a routing/case-
lifecycle concern for a later stage.
"""
import numpy as np
import pandas as pd

from . import config
from .simulate import draw_amount


def inject_pressure(rng, events, agent_id, area, day, provider,
                     start_hour, end_hour, cash_out_prob, rate_multiplier,
                     scenario_tag):
    """Replace a window of an agent's baseline events with a cash-out-heavy burst."""
    day_date = day["date"].date()
    events = [
        e for e in events
        if not (e["provider"] == provider
                and e["timestamp"].date() == day_date
                and start_hour <= e["timestamp"].hour < end_hour)
    ]

    hour_slice = config.HOUR_WEIGHTS[start_hour:end_hour]
    hour_slice = hour_slice / hour_slice.sum()
    daily_count = config.BASE_TXNS_PER_AGENT_PER_DAY * rate_multiplier
    hourly_counts = rng.poisson(daily_count * hour_slice)

    new_events = []
    for offset, count in enumerate(hourly_counts):
        hour = start_hour + offset
        for _ in range(int(count)):
            minute = int(rng.integers(0, 60))
            second = int(rng.integers(0, 60))
            txn_type = "cash_out" if rng.random() < cash_out_prob else "cash_in"
            new_events.append({
                "agent_id": agent_id,
                "area": area,
                "provider": provider,
                "timestamp": day["date"].replace(hour=hour, minute=minute, second=second),
                "txn_type": txn_type,
                "amount": round(draw_amount(rng), 2),
                "status": "failed" if rng.random() < config.FAILURE_RATE else "success",
                "customer_id": f"cust_{int(rng.integers(0, config.CUSTOMER_POOL_SIZE)):05d}",
                "day_type": day["day_type"],
                "split": day["split"],
                "event_flag": day["day_type"],
                "is_injected_anomaly": False,
                "is_injected_data_fault": False,
                "injected_scenario": scenario_tag,
            })
    return events + new_events


def inject_anomaly_burst(rng, agent_id, area, provider, day, hour, scenario_tag,
                          n_txns=5, window_minutes=12, pct_variation=0.03, n_accounts=3):
    """Near-identical repeated amounts from a few accounts in a short window (spec 5)."""
    base_amount = draw_amount(rng)
    accounts = [
        f"cust_{int(rng.integers(0, config.CUSTOMER_POOL_SIZE)):05d}"
        for _ in range(n_accounts)
    ]
    start_minute = int(rng.integers(0, max(60 - window_minutes, 1)))

    events = []
    for _ in range(n_txns):
        minute = (start_minute + int(rng.integers(0, window_minutes))) % 60
        second = int(rng.integers(0, 60))
        amount = round(base_amount * (1 + rng.uniform(-pct_variation, pct_variation)), 2)
        events.append({
            "agent_id": agent_id,
            "area": area,
            "provider": provider,
            "timestamp": day["date"].replace(hour=hour, minute=minute, second=second),
            "txn_type": "cash_out",
            "amount": amount,
            "status": "success",
            "customer_id": accounts[int(rng.integers(0, n_accounts))],
            "day_type": day["day_type"],
            "split": day["split"],
            "event_flag": "injected_anomaly",
            "is_injected_anomaly": True,
            "is_injected_data_fault": False,
            "injected_scenario": scenario_tag,
        })
    return events


def inject_data_faults(rng, df, provider, day_date, scenario_tag="C",
                        delay_frac=0.4, duplicate_frac=0.15, corrupt_frac=0.15):
    """Delay/duplicate/corrupt a provider's feed for one day, on a copy of the clean ledger.

    Must only be called after reconcile.check() has passed on `df` -- this
    function deliberately breaks the replay invariant for the affected rows.
    """
    df = df.copy()
    mask = (df["provider"] == provider) & (df["timestamp"].dt.date == day_date)
    idx = df[mask].index.to_numpy()
    rng.shuffle(idx)

    n = len(idx)
    n_delay = int(n * delay_frac)
    n_dup = int(n * duplicate_frac)
    n_corrupt = int(n * corrupt_frac)
    delay_idx = idx[:n_delay]
    dup_idx = idx[n_delay:n_delay + n_dup]
    corrupt_idx = idx[n_delay + n_dup:n_delay + n_dup + n_corrupt]
    affected = np.concatenate([delay_idx, dup_idx, corrupt_idx])

    df.loc[delay_idx, "timestamp"] += pd.to_timedelta(
        rng.integers(6, 20, size=len(delay_idx)), unit="h"
    )
    df.loc[corrupt_idx, "agent_provider_balance_after"] = np.nan

    df.loc[affected, "event_flag"] = "injected_data_fault"
    df.loc[affected, "is_injected_data_fault"] = True
    df.loc[affected, "injected_scenario"] = scenario_tag

    dup_rows = df.loc[dup_idx].copy()
    dup_rows["transaction_id"] = dup_rows["transaction_id"].astype(str) + "_dup"
    df = pd.concat([df, dup_rows], ignore_index=True)

    return df
