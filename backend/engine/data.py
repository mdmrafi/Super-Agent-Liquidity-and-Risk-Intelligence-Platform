"""Load Stage 1 output, adding the hour-level fields the engine operates on."""
import pandas as pd


def load_split(split):
    df = pd.read_csv(f"data/transactions_{split}.csv", parse_dates=["timestamp"])
    df["hour_slot"] = df["timestamp"].dt.floor("h")
    df["hour_bucket"] = df["timestamp"].dt.hour
    return df.sort_values("timestamp", kind="stable").reset_index(drop=True)
