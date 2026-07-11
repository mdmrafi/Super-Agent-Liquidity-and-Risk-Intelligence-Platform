"""Push Stage 1's synthetic transaction ledger (data/transactions_*.csv) into
MongoDB. The CSVs remain the pipeline's source of truth -- engine/, alerts/,
and ml/ keep reading them directly -- this is a queryable copy for the new
dashboard/API layer, not a replacement.

Idempotent: re-running replaces each split's documents wholesale (delete
then bulk-insert) rather than appending, so it's safe to re-run after
`python -m data_generation.main` regenerates the CSVs.

Run with (from backend/): python -m db.migrate_transactions
"""
import asyncio
import math

import pandas as pd

from .connection import init_db
from .models import Transaction

SPLITS = ("calibration", "holdout")


def _row_to_doc(row: dict) -> dict:
    doc = dict(row)
    for key in ("agent_provider_balance_after", "case_status", "injected_scenario"):
        v = doc.get(key)
        if isinstance(v, float) and math.isnan(v):
            doc[key] = None
    doc["is_injected_anomaly"] = bool(doc["is_injected_anomaly"])
    doc["is_injected_data_fault"] = bool(doc["is_injected_data_fault"])
    return doc


async def migrate_split(split: str):
    df = pd.read_csv(f"data/transactions_{split}.csv", parse_dates=["timestamp"])
    docs = [Transaction(**_row_to_doc(row)) for row in df.to_dict(orient="records")]

    await Transaction.find(Transaction.split == split).delete()
    if docs:
        await Transaction.insert_many(docs)
    print(f"{split}: migrated {len(docs)} transactions")


async def migrate():
    await init_db()
    for split in SPLITS:
        await migrate_split(split)


if __name__ == "__main__":
    asyncio.run(migrate())
