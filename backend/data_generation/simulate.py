"""Baseline transaction simulation: arrival process, amounts, and balance replay.

Balance mechanics (spec 4.3) are never generated directly -- every before/after
value is derived by replaying transactions in chronological order from an
opening balance, so the result is reconcilable by construction.
"""
from datetime import datetime, timedelta

import numpy as np

from . import config


def day_calendar():
    start = datetime.fromisoformat(config.START_DATE)
    days = []
    for i in range(config.NUM_DAYS):
        date = start + timedelta(days=i)
        days.append({
            "day_index": i + 1,
            "date": date,
            "day_type": config.DAY_TYPES[i],
            "split": "calibration" if i < config.CALIBRATION_DAYS else "holdout",
        })
    return days


def draw_amount(rng):
    mu = np.log(config.AMOUNT_MEDIAN_BDT)
    return float(rng.lognormal(mu, config.AMOUNT_SIGMA))


def _random_timestamp_in_hour(rng, date, hour):
    minute = int(rng.integers(0, 60))
    second = int(rng.integers(0, 60))
    return date.replace(hour=hour, minute=minute, second=second)


def generate_agent_events(rng, agent_id, area):
    """Raw (pre-balance) event stream for one agent across all days/providers."""
    events = []
    for day in day_calendar():
        multiplier = 1.0
        if day["day_type"] in ("salary_day", "eid"):
            multiplier = rng.uniform(*config.DAY_TYPE_MULTIPLIER_RANGE)
        daily_count = config.BASE_TXNS_PER_AGENT_PER_DAY * multiplier
        hourly_counts = rng.poisson(daily_count * config.HOUR_WEIGHTS)

        for hour, count in enumerate(hourly_counts):
            for _ in range(int(count)):
                provider = rng.choice(
                    config.PROVIDERS,
                    p=[config.PROVIDER_WEIGHTS[p] for p in config.PROVIDERS],
                )
                txn_type = "cash_in" if rng.random() < config.CASH_IN_PROB else "cash_out"
                events.append({
                    "agent_id": agent_id,
                    "area": area,
                    "provider": provider,
                    "timestamp": _random_timestamp_in_hour(rng, day["date"], hour),
                    "txn_type": txn_type,
                    "amount": round(draw_amount(rng), 2),
                    "status": "failed" if rng.random() < config.FAILURE_RATE else "success",
                    "customer_id": f"cust_{int(rng.integers(0, config.CUSTOMER_POOL_SIZE)):05d}",
                    "day_type": day["day_type"],
                    "split": day["split"],
                    "event_flag": day["day_type"],
                    "is_injected_anomaly": False,
                    "is_injected_data_fault": False,
                    "injected_scenario": None,
                })
    events.sort(key=lambda e: e["timestamp"])
    return events


def apply_balances(events, opening_cash, opening_provider_balances):
    """Replay events in chronological order, filling before/after fields.

    Failed transactions never move money: before == after for both fields.
    Cash is shared across providers; provider_balance is per-provider.
    """
    cash = opening_cash
    provider_balances = dict(opening_provider_balances)

    for e in events:
        provider = e["provider"]
        cash_before = cash
        bal_before = provider_balances[provider]

        if e["status"] == "success":
            if e["txn_type"] == "cash_out":
                cash -= e["amount"]
                provider_balances[provider] += e["amount"]
            else:  # cash_in
                cash += e["amount"]
                provider_balances[provider] -= e["amount"]

        e["agent_cash_before"] = cash_before
        e["agent_cash_after"] = cash
        e["agent_provider_balance_before"] = bal_before
        e["agent_provider_balance_after"] = provider_balances[provider]

    return events
