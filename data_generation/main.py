"""Stage 1 orchestration: generate, inject scenarios, reconcile, export.

Run with: python -m data_generation.main
"""
import numpy as np
import pandas as pd

from . import config, reconcile, scenarios, simulate

CALENDAR = {d["day_index"]: d for d in simulate.day_calendar()}

# Named scenarios A-C (spec section 5), placed on calibration days so they're
# available for engine-tuning in Stage 2. Scenario D needs no data (routing/
# case-lifecycle concern, out of scope for Stage 1).
#
# day_index values are scaled by NUM_DAYS / 14 from the original 14-day design
# (rounded) so each injection keeps its original relative position -- and,
# critically, keeps landing on the same side of the calibration/holdout split
# -- after NUM_DAYS grew to 30.
SCENARIO_A = dict(agent_id="agent_07", provider="bKash", day_index=17,
                   start_hour=10, end_hour=16, cash_out_prob=0.88, rate_multiplier=3.0)
SCENARIO_B_PRESSURE = dict(agent_id="agent_14", provider="Nagad", day_index=11,
                            start_hour=9, end_hour=15, cash_out_prob=0.85, rate_multiplier=2.5)
SCENARIO_B_ANOMALY = dict(agent_id="agent_14", provider="Nagad", day_index=11, hour=13)
SCENARIO_C = dict(provider="Rocket", day_index=13)

# General anomaly bursts beyond Scenario B's, spread across both splits so
# Stage 2 has enough labeled examples for precision/recall (spec section 11).
GENERAL_ANOMALIES = [
    dict(agent_id="agent_02", provider="bKash", day_index=4, hour=19, scenario_tag=None),
    dict(agent_id="agent_09", provider="Nagad", day_index=21, hour=12, scenario_tag=None),
    dict(agent_id="agent_03", provider="Rocket", day_index=24, hour=18, scenario_tag=None),
    dict(agent_id="agent_18", provider="bKash", day_index=28, hour=13, scenario_tag=None),
]

# General data faults beyond Scenario C's, spread across both splits.
GENERAL_DATA_FAULTS = [
    dict(provider="bKash", day_index=6, scenario_tag=None),
    dict(provider="Nagad", day_index=30, scenario_tag=None),
]

# General (unnamed) liquidity-pressure injection on a holdout day, so Stage 2's
# shortage-detection-lead-time metric has something to measure on held-out data --
# Scenario A alone (calibration only) left holdout with no shortage event to detect.
GENERAL_LIQUIDITY_PRESSURE = [
    # rate_multiplier/cash_out_prob bumped slightly vs. the original 14-day
    # design: over 30 days agents' natural cash balance drifts higher before
    # day 26, so the same relative pressure fell just short (ratio 0.803 vs.
    # the 0.80 safety threshold) of actually crossing -- this restores a real
    # crossing event for evaluate.shortage_lead_time to measure.
    dict(agent_id="agent_11", provider="Nagad", day_index=26,
         start_hour=10, end_hour=19, cash_out_prob=0.95, rate_multiplier=5.0, scenario_tag=None),
]


def build_clean_ledger(rng):
    all_events = []

    for agent_id in config.AGENTS:
        area = config.AGENT_AREA[agent_id]
        events = simulate.generate_agent_events(rng, agent_id, area)

        if agent_id == SCENARIO_A["agent_id"]:
            day = CALENDAR[SCENARIO_A["day_index"]]
            events = scenarios.inject_pressure(
                rng, events, agent_id, area, day, SCENARIO_A["provider"],
                SCENARIO_A["start_hour"], SCENARIO_A["end_hour"],
                SCENARIO_A["cash_out_prob"], SCENARIO_A["rate_multiplier"],
                scenario_tag="A",
            )

        if agent_id == SCENARIO_B_PRESSURE["agent_id"]:
            day = CALENDAR[SCENARIO_B_PRESSURE["day_index"]]
            events = scenarios.inject_pressure(
                rng, events, agent_id, area, day, SCENARIO_B_PRESSURE["provider"],
                SCENARIO_B_PRESSURE["start_hour"], SCENARIO_B_PRESSURE["end_hour"],
                SCENARIO_B_PRESSURE["cash_out_prob"], SCENARIO_B_PRESSURE["rate_multiplier"],
                scenario_tag="B",
            )
            day = CALENDAR[SCENARIO_B_ANOMALY["day_index"]]
            events += scenarios.inject_anomaly_burst(
                rng, agent_id, area, SCENARIO_B_ANOMALY["provider"], day,
                SCENARIO_B_ANOMALY["hour"], scenario_tag="B",
            )

        for spec in GENERAL_ANOMALIES:
            if spec["agent_id"] == agent_id:
                day = CALENDAR[spec["day_index"]]
                events += scenarios.inject_anomaly_burst(
                    rng, agent_id, area, spec["provider"], day, spec["hour"],
                    scenario_tag=spec["scenario_tag"],
                )

        for spec in GENERAL_LIQUIDITY_PRESSURE:
            if spec["agent_id"] == agent_id:
                day = CALENDAR[spec["day_index"]]
                events = scenarios.inject_pressure(
                    rng, events, agent_id, area, day, spec["provider"],
                    spec["start_hour"], spec["end_hour"],
                    spec["cash_out_prob"], spec["rate_multiplier"],
                    scenario_tag=spec["scenario_tag"],
                )

        events.sort(key=lambda e: e["timestamp"])

        opening_cash = rng.uniform(*config.OPENING_CASH_RANGE)
        opening_balances = {
            p: rng.uniform(*config.OPENING_PROVIDER_BALANCE_RANGE)
            for p in config.PROVIDERS
        }
        events = simulate.apply_balances(events, opening_cash, opening_balances)
        all_events.extend(events)

    df = pd.DataFrame(all_events)
    df = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
    df.insert(0, "transaction_id", [f"txn_{i + 1:06d}" for i in range(len(df))])
    df["case_status"] = None
    return df


def apply_named_data_faults(rng, df):
    day = CALENDAR[SCENARIO_C["day_index"]]
    df = scenarios.inject_data_faults(rng, df, SCENARIO_C["provider"], day["date"].date(), scenario_tag="C")
    for spec in GENERAL_DATA_FAULTS:
        day = CALENDAR[spec["day_index"]]
        df = scenarios.inject_data_faults(rng, df, spec["provider"], day["date"].date(),
                                           scenario_tag=spec["scenario_tag"])
    return df


COLUMN_ORDER = [
    "transaction_id", "agent_id", "provider", "area", "timestamp", "txn_type",
    "amount", "status", "agent_cash_before", "agent_cash_after",
    "agent_provider_balance_before", "agent_provider_balance_after",
    "event_flag", "case_status", "day_type", "customer_id", "split",
    "is_injected_anomaly", "is_injected_data_fault", "injected_scenario",
]


def main():
    rng = np.random.default_rng(config.RANDOM_SEED)

    df = build_clean_ledger(rng)

    errors = reconcile.check(df)
    if errors:
        raise AssertionError(
            f"{len(errors)} reconciliation error(s), first 10:\n" + "\n".join(errors[:10])
        )
    print(f"Reconciliation OK: {len(df)} clean transactions across {df['agent_id'].nunique()} agents.")

    df = apply_named_data_faults(rng, df)
    df = df[COLUMN_ORDER].sort_values("timestamp", kind="stable").reset_index(drop=True)

    for split in ("calibration", "holdout"):
        out = df[df["split"] == split]
        path = f"data/transactions_{split}.csv"
        out.to_csv(path, index=False)
        print(f"Wrote {path}: {len(out)} rows")

    print("\nInjected scenario counts:")
    print(df["injected_scenario"].value_counts(dropna=False))
    print("\nis_injected_anomaly:", df["is_injected_anomaly"].sum())
    print("is_injected_data_fault:", df["is_injected_data_fault"].sum())


if __name__ == "__main__":
    main()
