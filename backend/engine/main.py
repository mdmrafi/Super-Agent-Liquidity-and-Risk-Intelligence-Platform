"""Stage 2 orchestration: forecast + cohort + anomaly engine.

Run with (from backend/): python -m engine.main
"""
import json
import time

import pandas as pd

from . import anomaly, data, evaluate, pipeline
from .pipeline import CONTRACT_COLUMNS


def _to_jsonable(records):
    out = []
    for r in records:
        r = dict(r)
        ts = r["timestamp"]
        r["timestamp"] = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        if r["provider"] is None or (isinstance(r["provider"], float) and pd.isna(r["provider"])):
            r["provider"] = None
        for k in ("burn_rate", "time_to_shortage_minutes", "confidence", "cohort_z"):
            r[k] = float(r[k])
        r["cohort_peer_count"] = int(r["cohort_peer_count"])
        r["is_anomalous"] = bool(r["is_anomalous"])
        out.append(r)
    return out


def main():
    start = time.perf_counter()

    calibration_raw = data.load_split("calibration")
    holdout_raw = data.load_split("holdout")

    print("Calibrating anomaly thresholds on calibration split only...")
    locked = anomaly.calibrate(calibration_raw)
    print(f"Locked anomaly params: {locked}")

    calibration_scored = pipeline.run_split(calibration_raw, locked)
    holdout_scored = pipeline.run_split(holdout_raw, locked)

    for split_name, scored in (("calibration", calibration_scored), ("holdout", holdout_scored)):
        contract_only = scored[CONTRACT_COLUMNS].to_dict(orient="records")
        with open(f"data/forecast_{split_name}.json", "w") as f:
            json.dump(_to_jsonable(contract_only), f, indent=2)
        print(f"Wrote data/forecast_{split_name}.json: {len(contract_only)} rows")

    elapsed = time.perf_counter() - start

    print("\n=== Section 11 held-out metrics ===")
    print("Provider-level balance error:", evaluate.provider_balance_error(calibration_scored, holdout_scored))
    print("Shortage detection lead time (agent_11, holdout Nagad pressure window):",
          evaluate.shortage_lead_time(holdout_raw, holdout_scored, "agent_11"))

    anomaly_metrics, flagged_ids = evaluate.anomaly_metrics_holdout(holdout_raw, locked)
    print("Anomaly precision/recall (holdout, locked params):", anomaly_metrics)
    print("False-positive rate on eid spike (holdout, no true anomaly):",
          evaluate.false_positive_rate_on_spike(holdout_raw, flagged_ids, day_type="eid"))
    print("Alert explanation coverage (holdout):", evaluate.explanation_coverage(holdout_scored))
    print(f"Processing latency: {elapsed:.2f}s for {len(calibration_raw) + len(holdout_raw)} transactions")

    print("\n=== Required verification checks ===")

    thin = calibration_scored[calibration_scored["cohort_context"] == "self_history_fallback"]
    print(f"\nThin-cohort fallback rows: {len(thin)}")
    print("  confidence_label distribution:", thin["confidence_label"].value_counts().to_dict())
    if not thin.empty:
        row = thin[thin["confidence_label"] == "low"].iloc[0] if (thin["confidence_label"] == "low").any() else thin.iloc[0]
        print(f"  example -> agent={row['agent_id']} provider={row['provider']} "
              f"cohort_context={row['cohort_context']} confidence={row['confidence']:.2f} "
              f"({row['confidence_label']})")
        normal_conf_mean = calibration_scored[
            calibration_scored["cohort_context"] != "self_history_fallback"
        ]["confidence"].mean()
        print(f"  mean confidence elsewhere: {normal_conf_mean:.2f} vs fallback mean: {thin['confidence'].mean():.2f}")

    c_day = calibration_raw[calibration_raw["injected_scenario"] == "C"]
    if not c_day.empty:
        c_provider = c_day["provider"].iloc[0]
        c_hour_slots = pd.to_datetime(c_day["timestamp"]).dt.floor("h").unique()
        fault_rows = calibration_scored[
            (calibration_scored["provider"] == c_provider)
            & (pd.to_datetime(calibration_scored["timestamp"]).isin(c_hour_slots))
        ]
        clean_rows = calibration_scored[
            (calibration_scored["provider"] == c_provider)
            & (~pd.to_datetime(calibration_scored["timestamp"]).isin(c_hour_slots))
        ]
        print(f"\nScenario C (data fault, {c_provider}) hours -> mean confidence: "
              f"{fault_rows['confidence'].mean():.2f} vs other {c_provider} hours: {clean_rows['confidence'].mean():.2f}")

    print("\nHand-check: Scenario A (agent_07, bKash, calibration day 8)")
    a7 = calibration_scored[(calibration_scored["agent_id"] == "agent_07")].sort_values("timestamp")
    a7_window = a7[(pd.to_datetime(a7["timestamp"]) >= "2026-01-08 09:00") & (pd.to_datetime(a7["timestamp"]) <= "2026-01-08 17:00")]
    print(a7_window[["provider", "timestamp", "burn_rate", "time_to_shortage_minutes", "confidence", "cohort_z", "cohort_context", "recommended_owner"]].to_string(index=False))

    print("\nHand-check: Scenario B anomaly (agent_14, Nagad, calibration day 5)")
    b14 = calibration_scored[
        (calibration_scored["agent_id"] == "agent_14") & (calibration_scored["is_anomalous"])
    ]
    print(b14[["provider", "timestamp", "is_anomalous", "anomaly_evidence", "recommended_owner"]].to_string(index=False))


if __name__ == "__main__":
    main()
