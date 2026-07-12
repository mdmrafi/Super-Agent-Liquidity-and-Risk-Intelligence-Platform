import unittest
from types import SimpleNamespace

import pandas as pd
from fastapi import HTTPException

from alerts.build import (
    _base_alert,
    _debounced_liquidity_keys,
    _observable_fault_counts_by_hour,
)
from auth.scope import alert_is_visible, project_balance
from chat.answer import _grounded_fallback
from db.models import UserRole
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
