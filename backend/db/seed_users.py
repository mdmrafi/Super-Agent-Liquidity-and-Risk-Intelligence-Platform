"""Seed one mock account per role (idempotent -- safe to re-run; skips any
username that already exists rather than erroring or duplicating).

Run with (from backend/): python -m db.seed_users
"""
import asyncio

from auth.security import hash_password
from .connection import init_db
from .models import User, UserRole

# Deliberately simple, memorable passwords -- this is demo/mock data behind
# a hackathon prototype, not a real account system. They're still bcrypt-
# hashed in the database, never stored or transmitted in plain text after
# this point, and shown on the login page itself for the demo.
MOCK_USERS = [
    dict(username="agent01", password="agent123", display_name="Agent 01 · Zindabazar",
         role=UserRole.agent, agent_id="agent_01", area="Zindabazar"),
    dict(username="fieldofficer", password="officer123", display_name="Field Officer Lima",
         role=UserRole.field_officer),
    dict(username="providerops", password="provider123", display_name="Provider Ops",
         role=UserRole.provider_ops),
    dict(username="riskteam", password="risk123", display_name="Risk Analyst",
         role=UserRole.risk_team),
    dict(username="admin", password="admin123", display_name="Platform Admin",
         role=UserRole.admin),
]


async def seed():
    await init_db()
    created, skipped = 0, 0
    for spec in MOCK_USERS:
        existing = await User.find_one(User.username == spec["username"])
        if existing:
            skipped += 1
            continue
        password = spec.pop("password")
        await User(hashed_password=hash_password(password), **spec).insert()
        created += 1
        spec["password"] = password  # restore for the printed summary below

    print(f"Seeded {created} user(s), skipped {skipped} already-existing.")
    print("\nDemo credentials:")
    for spec in MOCK_USERS:
        print(f"  {spec['username']:<14} / {spec['password']:<14} ({spec['role'].value})")


if __name__ == "__main__":
    asyncio.run(seed())
