"""Beanie (async, Pydantic-based) document schemas -- the Python equivalent
of a Mongoose model: one class per collection, validated on read and write.

Two collections:
- users: mock accounts, one role each, seeded by db/seed_users.py.
- transactions: Stage 1's synthetic ledger, migrated from
  data/transactions_{calibration,holdout}.csv by db/migrate_transactions.py.
  This is a copy for read/query purposes -- the CSVs remain the source of
  truth the rest of the pipeline (engine/, alerts/, ml/) reads from.
"""
from datetime import datetime, timezone
from enum import Enum

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class UserRole(str, Enum):
    """One role per dashboard tab, plus admin as the only multi-tab role.
    Matches the owner/actor vocabulary already used across alerts/routing.py
    and AlertCard.jsx's ROLE_LABEL."""
    agent = "agent"
    field_officer = "field_officer"
    area_team = "area_team"
    provider_ops = "provider_ops"
    risk_team = "risk_team"
    admin = "admin"


class MFSProvider(str, Enum):
    """Canonical provider identifiers used by transactions and alerts."""

    bkash = "bKash"
    nagad = "Nagad"
    rocket = "Rocket"


class User(Document):
    username: str
    display_name: str
    hashed_password: str
    role: UserRole

    # Authorization scope, not a UI preference:
    # - agent accounts require agent_id and may see that agent's cash and every
    #   provider balance/alert;
    # - field_officer/area_team accounts require area and may see agent-side
    #   data only in that territory;
    # - provider_ops/risk_team accounts require provider and may see only that
    #   provider's data;
    # - admin is deliberately unscoped.
    #
    # The role/field combination is checked at login and on every authenticated
    # request (auth/scope.py). Keeping that check at the authorization boundary
    # also makes legacy pre-provider JWTs fail with a controlled 403 instead of
    # turning an old Mongo document into a Pydantic read-time 500.
    agent_id: str | None = None
    area: str | None = None
    provider: MFSProvider | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        indexes = [IndexModel("username", unique=True)]


class Transaction(Document):
    transaction_id: str
    agent_id: str
    provider: str
    area: str
    timestamp: datetime
    txn_type: str
    amount: float
    status: str
    agent_cash_before: float
    agent_cash_after: float
    agent_provider_balance_before: float
    # Null on rows Scenario C's data-fault injection corrupted -- see
    # data_generation/scenarios.py:inject_data_faults. Never fed back into
    # reconcile.check(), so a null here is a genuine "bad reading", not a bug.
    agent_provider_balance_after: float | None = None
    event_flag: str
    case_status: str | None = None
    day_type: str
    customer_id: str
    split: str
    is_injected_anomaly: bool
    is_injected_data_fault: bool
    injected_scenario: str | None = None

    class Settings:
        name = "transactions"
        indexes = [
            IndexModel("transaction_id"),
            IndexModel([("split", 1), ("agent_id", 1)]),
            IndexModel([("split", 1), ("timestamp", 1)]),
        ]
