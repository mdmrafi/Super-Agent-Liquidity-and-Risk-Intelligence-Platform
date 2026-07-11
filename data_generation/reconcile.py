"""Verify every balance is replayable from opening balance + transaction history.

Must be run on the clean ledger *before* Scenario C data-fault injection --
faults deliberately break this invariant, which is the point of them.
"""

TOLERANCE = 1e-6


def _expected_cash_after(row):
    if row["status"] == "failed":
        return row["agent_cash_before"]
    if row["txn_type"] == "cash_out":
        return row["agent_cash_before"] - row["amount"]
    return row["agent_cash_before"] + row["amount"]


def _expected_balance_after(row):
    if row["status"] == "failed":
        return row["agent_provider_balance_before"]
    if row["txn_type"] == "cash_out":
        return row["agent_provider_balance_before"] + row["amount"]
    return row["agent_provider_balance_before"] - row["amount"]


def check(df):
    """Return a list of human-readable error strings; empty means fully reconciled."""
    errors = []

    for agent_id, g in df.groupby("agent_id", sort=False):
        g = g.sort_values("timestamp", kind="stable")
        prev_cash_after = None
        for _, row in g.iterrows():
            if prev_cash_after is not None and abs(row["agent_cash_before"] - prev_cash_after) > TOLERANCE:
                errors.append(f"{agent_id}: cash chain break at {row['transaction_id']}")
            prev_cash_after = row["agent_cash_after"]

            expected = _expected_cash_after(row)
            if abs(row["agent_cash_after"] - expected) > TOLERANCE:
                errors.append(f"{agent_id}: cash delta wrong at {row['transaction_id']}")

    for (agent_id, provider), g in df.groupby(["agent_id", "provider"], sort=False):
        g = g.sort_values("timestamp", kind="stable")
        prev_bal_after = None
        for _, row in g.iterrows():
            if prev_bal_after is not None and abs(row["agent_provider_balance_before"] - prev_bal_after) > TOLERANCE:
                errors.append(f"{agent_id}/{provider}: balance chain break at {row['transaction_id']}")
            prev_bal_after = row["agent_provider_balance_after"]

            expected = _expected_balance_after(row)
            if abs(row["agent_provider_balance_after"] - expected) > TOLERANCE:
                errors.append(f"{agent_id}/{provider}: balance delta wrong at {row['transaction_id']}")

    return errors
