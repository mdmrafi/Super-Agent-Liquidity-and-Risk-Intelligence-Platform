import unittest
from types import SimpleNamespace

import pandas as pd
from fastapi import HTTPException

from alerts import lifecycle
from alerts.build import (
    _base_alert,
    _debounced_liquidity_keys,
    _observable_fault_counts_by_hour,
)
from auth.scope import alert_is_visible, project_balance, require_assignment
from chat.answer import _grounded_fallback
from db.models import UserRole
from engine.anomaly import detect
from explain.explain import _fallback_explanation


def _user(role, *, area=None, provider=None, agent_id=None):
    return SimpleNamespace(
        role=role,
        area=area,
        provider=provider,
        agent_id=agent_id,
    )


def _physical_cash_alert(area="Shibganj"):
    row = {
        "agent_id": "agent_14",
        "provider": None,
        "area": area,
        "timestamp": "2026-01-11T11:00:00",
        "confidence": 0.72,
        "confidence_label": "high",
        "cohort_context": "agent_only",
        "cohort_peer_count": 3,
        "recommended_owner": "field_officer",
    }
    return _base_alert(
        row,
        "liquidity_shortage",
        "high",
        ["shared physical cash evidence"],
        liquidity_type="physical_cash",
    )


class RoutingScopeTests(unittest.TestCase):
    def test_area_roles_exist_and_receive_shared_cash_case(self):
        self.assertEqual(UserRole.area_team.value, "area_team")
        alert = _physical_cash_alert()
        self.assertIn("field_officer", alert["audience"])
        self.assertIn("area_team", alert["audience"])
        self.assertTrue(
            alert_is_visible(_user("field_officer", area="Shibganj"), alert)
        )
        self.assertTrue(
            alert_is_visible(_user("area_team", area="Shibganj"), alert)
        )

    def test_provider_employee_cannot_see_shared_cash(self):
        alert = _physical_cash_alert()
        self.assertFalse(
            alert_is_visible(_user("provider_ops", provider="bKash"), alert)
        )

    def test_area_scope_blocks_another_territory_balance(self):
        balance = {
            "agent_id": "agent_01",
            "area": "Zindabazar",
            "cash": 100.0,
            "providers": {},
        }
        with self.assertRaises(HTTPException) as caught:
            project_balance(_user("field_officer", area="Shibganj"), balance)
        self.assertEqual(caught.exception.status_code, 403)


class AssignmentTests(unittest.TestCase):
    def test_assign_records_full_audit_trail_and_owner(self):
        alert = _physical_cash_alert()
        self.assertIsNone(alert["case_owner"])
        assigned = lifecycle.assign(
            alert, actor="Field Officer Lima (field_officer)",
            new_owner="areateam", new_owner_display="Shibganj Area Team",
            reason="Area coordinator to own closure.", at="2026-01-11T11:05:00",
        )
        self.assertEqual(assigned["case_owner"], "areateam")
        self.assertEqual(assigned["case_owner_display"], "Shibganj Area Team")
        event = assigned["case_history"][-1]
        # every audited field is present
        self.assertIsNone(event["previous_owner"])
        self.assertEqual(event["new_owner"], "areateam")
        self.assertEqual(event["reason"], "Area coordinator to own closure.")
        self.assertEqual(event["actor"], "Field Officer Lima (field_officer)")
        self.assertIn("2026-01-11T11:05:00", event["timestamp"])
        # original alert is untouched (append-only, no in-place mutation)
        self.assertIsNone(alert["case_owner"])
        self.assertEqual(len(alert["case_history"]), 1)

    def test_reassign_preserves_prior_history(self):
        alert = _physical_cash_alert()
        first = lifecycle.assign(alert, actor="a", new_owner="fieldofficer",
                                 new_owner_display="Field Officer Lima", reason="taking it",
                                 at="2026-01-11T11:05:00")
        second = lifecycle.assign(first, actor="a", new_owner="areateam",
                                  new_owner_display="Shibganj Area Team", reason="escalating",
                                  at="2026-01-11T12:50:00")
        owners = [h["new_owner"] for h in second["case_history"] if h.get("new_owner")]
        self.assertEqual(owners, ["fieldofficer", "areateam"])
        self.assertEqual(second["case_history"][-1]["previous_owner"], "fieldofficer")

    def test_agent_role_cannot_assign(self):
        alert = _physical_cash_alert()
        actor = _user("agent", agent_id="agent_14")
        assignee = _user("field_officer", area="Shibganj")
        with self.assertRaises(HTTPException) as caught:
            require_assignment(actor, alert, assignee)
        self.assertEqual(caught.exception.status_code, 403)

    def test_cannot_assign_physical_cash_case_to_provider_employee(self):
        # provider boundary: a provider_ops user can't legitimately see a
        # physical-cash alert, so they can't be handed one either.
        alert = _physical_cash_alert()
        actor = _user("field_officer", area="Shibganj")
        assignee = _user("provider_ops", provider="bKash")
        with self.assertRaises(HTTPException) as caught:
            require_assignment(actor, alert, assignee)
        self.assertEqual(caught.exception.status_code, 403)

    def test_valid_in_area_assignment_authorized(self):
        alert = _physical_cash_alert()
        actor = _user("field_officer", area="Shibganj")
        assignee = _user("area_team", area="Shibganj")
        # does not raise
        self.assertIs(require_assignment(actor, alert, assignee), assignee)

    def test_actor_cannot_assign_alert_outside_own_scope(self):
        alert = _physical_cash_alert(area="Zindabazar")
        actor = _user("field_officer", area="Shibganj")
        assignee = _user("area_team", area="Zindabazar")
        with self.assertRaises(HTTPException) as caught:
            require_assignment(actor, alert, assignee)
        # out-of-scope alert is reported as absent (404), not confirmed
        self.assertEqual(caught.exception.status_code, 404)


class ObservableDataQualityTests(unittest.TestCase):
    def test_detection_does_not_depend_on_injected_labels(self):
        rows = [
            {
                "transaction_id": "txn_1",
                "agent_id": "agent_01",
                "provider": "bKash",
                "timestamp": pd.Timestamp("2026-01-01T10:00:00"),
                "txn_type": "cash_out",
                "amount": 100.0,
                "status": "success",
                "customer_id": "cust_1",
                "agent_cash_before": 500.0,
                "agent_cash_after": 400.0,
                "agent_provider_balance_before": 1000.0,
                "agent_provider_balance_after": 1100.0,
                "is_injected_data_fault": False,
            },
            {
                "transaction_id": "txn_1_dup",
                "agent_id": "agent_01",
                "provider": "bKash",
                "timestamp": pd.Timestamp("2026-01-01T10:00:00"),
                "txn_type": "cash_out",
                "amount": 100.0,
                "status": "success",
                "customer_id": "cust_1",
                "agent_cash_before": 500.0,
                "agent_cash_after": 400.0,
                "agent_provider_balance_before": 1000.0,
                "agent_provider_balance_after": 1100.0,
                "is_injected_data_fault": False,
            },
            {
                "transaction_id": "txn_2",
                "agent_id": "agent_01",
                "provider": "bKash",
                "timestamp": pd.Timestamp("2026-01-01T11:00:00"),
                "txn_type": "cash_in",
                "amount": 50.0,
                "status": "success",
                "customer_id": "cust_2",
                "agent_cash_before": 400.0,
                "agent_cash_after": 450.0,
                "agent_provider_balance_before": 1100.0,
                "agent_provider_balance_after": None,
                "is_injected_data_fault": False,
            },
        ]
        clean_labels = pd.DataFrame(rows)
        false_labels = clean_labels.copy()
        false_labels["is_injected_data_fault"] = True
        observed = _observable_fault_counts_by_hour(clean_labels)
        relabeled = _observable_fault_counts_by_hour(false_labels)
        self.assertGreater(int(observed.sum()), 0)
        pd.testing.assert_series_equal(observed, relabeled)


class InterleavedAnomalyClusterTests(unittest.TestCase):
    def test_unrelated_transaction_does_not_break_a_near_identical_cluster(self):
        # Regression test for Scenario B (agent_14/Nagad): 3 near-identical
        # cash-outs from 2 accounts, with an unrelated cash-in from a third
        # customer interleaved. The cluster must still be detected -- an
        # ordinary transaction in between shouldn't hide the pattern.
        rows = [
            {"transaction_id": "t1", "agent_id": "agent_14", "provider": "Nagad",
             "area": "Shibganj", "timestamp": pd.Timestamp("2026-01-11T13:00:00"),
             "txn_type": "cash_out", "amount": 5100.0, "status": "success",
             "customer_id": "cust_a", "day_type": "normal"},
            {"transaction_id": "t2", "agent_id": "agent_14", "provider": "Nagad",
             "area": "Shibganj", "timestamp": pd.Timestamp("2026-01-11T13:01:00"),
             "txn_type": "cash_in", "amount": 4300.0, "status": "success",
             "customer_id": "cust_unrelated", "day_type": "normal"},
            {"transaction_id": "t3", "agent_id": "agent_14", "provider": "Nagad",
             "area": "Shibganj", "timestamp": pd.Timestamp("2026-01-11T13:02:00"),
             "txn_type": "cash_out", "amount": 5130.0, "status": "success",
             "customer_id": "cust_b", "day_type": "normal"},
            {"transaction_id": "t4", "agent_id": "agent_14", "provider": "Nagad",
             "area": "Shibganj", "timestamp": pd.Timestamp("2026-01-11T13:05:00"),
             "txn_type": "cash_out", "amount": 5150.0, "status": "success",
             "customer_id": "cust_a", "day_type": "normal"},
        ]
        df = pd.DataFrame(rows)
        _, flagged_ids = detect(df, min_txns=3, window_minutes=10, pct_variation=0.05, max_accounts=2)
        self.assertEqual(flagged_ids, {"t1", "t3", "t4"})


class SharedCashDebounceTests(unittest.TestCase):
    def test_null_provider_survives_dataframe_normalization(self):
        rows = [
            {
                "agent_id": "agent_14",
                "provider": None,
                "timestamp": "2026-01-11T10:00:00",
                "time_to_shortage_minutes": 100.0,
            },
            {
                "agent_id": "agent_14",
                "provider": None,
                "timestamp": "2026-01-11T11:00:00",
                "time_to_shortage_minutes": 80.0,
            },
            {
                "agent_id": "agent_14",
                "provider": "bKash",
                "timestamp": "2026-01-11T11:00:00",
                "time_to_shortage_minutes": 999999.0,
            },
        ]
        keys = _debounced_liquidity_keys(rows)
        self.assertIn(
            (
                "agent_14",
                "__cash__",
                pd.Timestamp("2026-01-11T11:00:00"),
            ),
            keys,
        )


class CaseNotesTests(unittest.TestCase):
    def test_add_note_appends_without_touching_status(self):
        alert = _physical_cash_alert()
        self.assertEqual(alert["case_notes"], [])

        noted = lifecycle.add_note(
            alert, actor="field_officer_lima", text="Contacted agent, awaiting pickup.",
            at="2026-01-11T12:00:00",
        )

        self.assertEqual(len(noted["case_notes"]), 1)
        self.assertEqual(noted["case_notes"][0]["text"], "Contacted agent, awaiting pickup.")
        self.assertEqual(noted["case_notes"][0]["actor"], "field_officer_lima")
        # notes never change case_status/display_status or mutate the original dict
        self.assertEqual(noted["case_status"], "new")
        self.assertEqual(alert["case_notes"], [])

    def test_add_note_is_append_only_across_multiple_calls(self):
        alert = _physical_cash_alert()
        first = lifecycle.add_note(alert, actor="a", text="first", at="2026-01-11T12:00:00")
        second = lifecycle.add_note(first, actor="b", text="second", at="2026-01-11T12:05:00")
        self.assertEqual([n["text"] for n in second["case_notes"]], ["first", "second"])


class LocalizedFallbackTests(unittest.TestCase):
    def setUp(self):
        self.alert = {
            "alert_type": "liquidity_shortage",
            "agent_id": "agent_14",
            "provider": None,
            "severity": "high",
            "evidence": ["shared physical cash evidence"],
            "recommended_action": "request_replenishment_support",
            "recommended_owner": "field_officer",
        }

    def test_explanation_fallbacks_are_localized(self):
        self.assertIn("সতর্কতা", _fallback_explanation(self.alert, "bn"))
        self.assertIn("Proman", _fallback_explanation(self.alert, "banglish"))

    def test_chat_fallbacks_are_localized(self):
        context = {"open_alerts": [self.alert]}
        self.assertIn("খোলা সতর্কতা", _grounded_fallback(context, "bn"))
        self.assertIn("open alert ache", _grounded_fallback(context, "banglish"))


if __name__ == "__main__":
    unittest.main()
