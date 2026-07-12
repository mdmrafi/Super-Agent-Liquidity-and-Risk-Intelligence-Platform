"""Seed one mock account per role (idempotent and migration-friendly).

Existing demo users are updated with their canonical role/provider assignment,
so re-running this after provider scoping was added repairs old users instead
of silently leaving them with unrestricted-looking legacy data.

Run with (from backend/): python -m db.seed_users
"""
import asyncio

from auth.security import hash_password
from .connection import init_db
from .models import MFSProvider, User, UserRole

# Deliberately simple, memorable passwords -- this is demo/mock data behind
# a hackathon prototype, not a real account system. They're still bcrypt-
# hashed in the database, never stored or transmitted in plain text after
# this point, and shown on the login page itself for the demo.
MOCK_USERS = [
    dict(username="agent01", password="agent123", display_name="Agent 01 · Zindabazar",
         role=UserRole.agent, agent_id="agent_01", area="Zindabazar"),
    dict(username="fieldofficer", password="officer123", display_name="Field Officer Lima",
         role=UserRole.field_officer, area="Shibganj"),
    dict(username="areateam", password="area123", display_name="Shibganj Area Team",
         role=UserRole.area_team, area="Shibganj"),
    dict(username="providerops", password="provider123", display_name="Provider Ops",
         role=UserRole.provider_ops, provider=MFSProvider.nagad),
    dict(username="riskteam", password="risk123", display_name="Risk Analyst",
         role=UserRole.risk_team, provider=MFSProvider.bkash),
    dict(username="admin", password="admin123", display_name="Platform Admin",
         role=UserRole.admin),
]


async def seed():
    await init_db()
    created, updated, unchanged = 0, 0, 0
    collection = User.get_pymongo_collection()
    for spec in MOCK_USERS:
        account = {key: value for key, value in spec.items() if key != "password"}
        # Explicitly write nulls too, clearing stale scope fields if a demo
        # username changes roles between seed revisions.
        account.setdefault("agent_id", None)
        account.setdefault("area", None)
        account.setdefault("provider", None)

        # Use the raw collection for the migration lookup. This remains able to
        # repair a legacy row even if a future schema makes that row invalid to
        # instantiate as a User document.
        raw = await collection.find_one({"username": spec["username"]})
        if raw is None:
            await User(
                hashed_password=hash_password(spec["password"]),
                **account,
            ).insert()
            created += 1
            continue

        serialized = {
            key: (value.value if hasattr(value, "value") else value)
            for key, value in account.items()
        }
        changes = {key: value for key, value in serialized.items() if raw.get(key) != value}
        if changes:
            await collection.update_one({"_id": raw["_id"]}, {"$set": changes})
            updated += 1
        else:
            unchanged += 1

    print(f"Seeded {created}, updated {updated}, unchanged {unchanged} user(s).")
    print("\nDemo credentials:")
    for spec in MOCK_USERS:
        provider = spec.get("provider")
        scope_value = provider.value if provider else spec.get("area")
        scope = f", {scope_value}" if scope_value else ""
        print(f"  {spec['username']:<14} / {spec['password']:<14} ({spec['role'].value}{scope})")


if __name__ == "__main__":
    asyncio.run(seed())
