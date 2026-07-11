"""Stage 3 orchestration: build alerts, demo the case lifecycle, run required checks.

Run with: python -m alerts.main
"""
import json
import pathlib
import re

import pandas as pd

from . import build, lifecycle


def _load(split):
    with open(f"data/forecast_{split}.json") as f:
        scored = json.load(f)
    raw = pd.read_csv(f"data/transactions_{split}.csv", parse_dates=["timestamp"])
    return scored, raw


def generate_alerts():
    all_alerts = []
    for split, prefix in (("calibration", "c"), ("holdout", "h")):
        scored, raw = _load(split)
        alerts = build.build_alerts(scored, raw, id_prefix=prefix)
        with open(f"data/alerts_{split}.json", "w") as f:
            json.dump(alerts, f, indent=2)
        print(f"Wrote data/alerts_{split}.json: {len(alerts)} alerts")
        all_alerts.extend(alerts)
    print(f"\nTotal alerts: {len(all_alerts)}")
    return all_alerts


def check_severity_distribution(all_alerts):
    print("\n1. Severity distribution (should not be degenerate):")
    print(pd.Series([a["severity"] for a in all_alerts]).value_counts().to_string())
    by_type = pd.DataFrame(all_alerts).groupby(["alert_type", "severity"]).size()
    print(by_type.to_string())


def check_replenishment_gating(all_alerts):
    print("\n2. request_replenishment_support gating:")
    replenish = [a for a in all_alerts if a["recommended_action"] == "request_replenishment_support"]
    bad = [a for a in replenish if not (a["severity"] == "high" and a["alert_type"] == "liquidity_shortage")]
    print(f"   {len(replenish)} alerts recommend request_replenishment_support; "
          f"{len(bad)} violate the high+liquidity_shortage-only rule (should be 0)")
    assert not bad, "request_replenishment_support leaked outside high-severity liquidity alerts"

    print("   Confirming no restriction code path exists (grep alerts/, engine/, data_generation/):")
    restriction_terms = re.compile(r"\b(block|freeze|disable|lock)[_ ]?(agent|account|transact)", re.I)
    hits = [
        str(py_file)
        for base in ("alerts", "engine", "data_generation")
        for py_file in pathlib.Path(base).glob("*.py")
        if restriction_terms.search(py_file.read_text())
    ]
    print(f"   restriction-pattern matches: {hits} (should be [])")
    assert not hits, "found a code path that may restrict agent operation"


def check_hand_check_scenarios():
    print("\n3. Hand-check known Scenario A/B/C agents (calibration):")
    with open("data/alerts_calibration.json") as f:
        cal_alerts = json.load(f)

    for agent, provider, label in [
        ("agent_07", "bKash", "Scenario A (hidden shortage)"),
        ("agent_07", None, "Scenario A shared-cash view"),
        ("agent_14", "Nagad", "Scenario B (pressure + anomaly)"),
    ]:
        matches = [a for a in cal_alerts if a["agent_id"] == agent and a["provider"] == provider]
        print(f"   {label}: {len(matches)} alert(s)")
        for a in matches[:3]:
            print(f"     {a['timestamp']} {a['alert_type']:<18} severity={a['severity']:<6} "
                  f"owner={a['recommended_owner']:<14} action={a['recommended_action']}")

    c_fault_alerts = [a for a in cal_alerts if a["alert_type"] == "data_quality"]
    print(f"   Scenario C (data fault) data_quality alerts in calibration: {len(c_fault_alerts)}")
    for a in c_fault_alerts[:3]:
        print(f"     {a['agent_id']} {a['provider']} {a['timestamp']} severity={a['severity']} "
              f"owner={a['recommended_owner']}")


def check_full_lifecycle_demo(all_alerts):
    print("\n4. Full lifecycle demo (Scenario D) -- end to end on one alert:")
    demo = next(a for a in all_alerts if a["alert_type"] == "liquidity_shortage" and a["severity"] == "high")
    print(f"   Starting alert {demo['alert_id']} ({demo['agent_id']}, {demo['provider']}), "
          f"display_status={demo['display_status']!r}")
    demo = lifecycle.acknowledge(demo, actor="field_officer_lima", at="2026-01-08T12:15:00")
    demo = lifecycle.escalate(demo, actor="field_officer_lima", at="2026-01-08T12:40:00")
    demo = lifecycle.resolve(demo, actor="area_coordinator_zindabazar", at="2026-01-08T14:05:00")
    print(f"   Final case_status={demo['case_status']}, display_status={demo['display_status']!r}")
    print("   case_history:")
    for h in demo["case_history"]:
        print(f"     {h}")


def check_no_banned_language(all_alerts):
    print("\n5. Grepping evidence/alert text for 'fraud' or 'high risk' (should be empty):")
    banned = re.compile(r"fraud|high risk", re.I)
    violations = [
        a["alert_id"] for a in all_alerts
        if any(banned.search(e) for e in a["evidence"])
    ]
    print(f"   violations: {violations}")
    assert not violations, "found banned verdict language in alert evidence"


def main():
    all_alerts = generate_alerts()

    print("\n=== Required verification checks ===")
    check_severity_distribution(all_alerts)
    check_replenishment_gating(all_alerts)
    check_hand_check_scenarios()
    check_full_lifecycle_demo(all_alerts)
    check_no_banned_language(all_alerts)

    print("\nAll Stage 3 checks passed.")


if __name__ == "__main__":
    main()
