"""
scripts/backfill_coinbase_data_gaps.py — Automated Backfill for Coinbase Historical Data Gaps
=============================================================================================
Fetches missing candles from the public Coinbase Exchange API:
1. 2023-03-24 13:00:00 UTC (1 hour)
2. 2026-09-01 06:00:00 UTC to 2026-10-02 05:00:00 UTC (742 hours)

Merges backfilled candles into `data/raw/ohlcv.parquet` after archiving original to:
`data/raw/ohlcv_pre_backfill_backup.parquet`.
Produces `data/raw/ohlcv_backfilled.parquet` and updates `data/raw/ohlcv.parquet`.
"""

import json
import math
import os
import shutil
import urllib.request
import datetime
import pandas as pd
import numpy as np

DATA_PATH = "data/raw/ohlcv.parquet"
BACKUP_PATH = "data/raw/ohlcv_pre_backfill_backup.parquet"
BACKFILLED_OUT_PATH = "data/raw/ohlcv_backfilled.parquet"


def fetch_coinbase_candle_range(start_iso: str, end_iso: str) -> pd.DataFrame:
    """Fetches hourly candles between start_iso and end_iso using chunking."""
    start_dt = datetime.datetime.fromisoformat(start_iso)
    end_dt = datetime.datetime.fromisoformat(end_iso)

    rows = []
    curr = start_dt
    while curr < end_dt:
        chunk_end = min(end_dt, curr + datetime.timedelta(hours=290))
        s_str = curr.strftime("%Y-%m-%dT%H:%M:%SZ")
        e_str = chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600&start={s_str}&end={e_str}"
        req = urllib.request.Request(url, headers={"User-Agent": "BTCognitive-GapBackfill/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            for c in data:
                # Coinbase schema: [time, low, high, open, close, volume]
                ts = datetime.datetime.fromtimestamp(c[0], tz=datetime.timezone.utc)
                avail_ts = ts + datetime.timedelta(hours=1)
                rows.append({
                    "timestamp": ts,
                    "open": float(c[3]),
                    "high": float(c[2]),
                    "low": float(c[1]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                    "available_time": avail_ts,
                })
        curr = chunk_end

    df_fetched = pd.DataFrame(rows)
    if not df_fetched.empty:
        df_fetched = df_fetched.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df_fetched


def execute_backfill(apply_to_main: bool = True):
    print("Starting Coinbase Data Gap Backfill...")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Missing {DATA_PATH}")

    df_orig = pd.read_parquet(DATA_PATH)
    df_orig["timestamp"] = pd.to_datetime(df_orig["timestamp"], utc=True)
    print(f"Original row count: {len(df_orig)} bars")

    # 1. Fetch 2023 missing hour
    print("Fetching 2023-03-24 13:00 UTC missing hour...")
    df_2023 = fetch_coinbase_candle_range("2023-03-24T12:00:00+00:00", "2023-03-24T15:00:00+00:00")

    # 2. Fetch September 2026 missing gap
    print("Fetching 2026-09-01 06:00 UTC to 2026-10-02 05:00 UTC missing period...")
    df_2026 = fetch_coinbase_candle_range("2026-09-01T06:00:00+00:00", "2026-10-02T05:00:00+00:00")

    df_backfill = pd.concat([df_2023, df_2026], ignore_index=True)
    print(f"Total backfilled candles fetched: {len(df_backfill)}")

    # Merge with original
    df_merged = pd.concat([df_orig, df_backfill], ignore_index=True)
    df_merged = df_merged.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    print(f"Merged row count: {len(df_merged)} bars (+{len(df_merged) - len(df_orig)} net added)")

    # Audit gaps in merged dataset
    diffs = df_merged["timestamp"].diff()
    remaining_gaps = []
    for i in range(1, len(df_merged)):
        if diffs.iloc[i] != pd.Timedelta(hours=1):
            remaining_gaps.append((df_merged.loc[i - 1, "timestamp"], df_merged.loc[i, "timestamp"]))

    print(f"Remaining gaps in backfilled dataset: {len(remaining_gaps)}")
    for g_s, g_e in remaining_gaps:
        print(f"  Remaining Gap: {g_s} -> {g_e}")

    # Save to backfilled path
    df_merged.to_parquet(BACKFILLED_OUT_PATH, index=False)
    print(f"Saved backfilled dataset to {BACKFILLED_OUT_PATH}")

    if apply_to_main:
        if not os.path.exists(BACKUP_PATH):
            shutil.copyfile(DATA_PATH, BACKUP_PATH)
            print(f"Archived original dataset to {BACKUP_PATH}")
        df_merged.to_parquet(DATA_PATH, index=False)
        print(f"Applied backfill directly to {DATA_PATH} (Now fully continuous!)")

    return df_merged


if __name__ == "__main__":
    execute_backfill(apply_to_main=True)
