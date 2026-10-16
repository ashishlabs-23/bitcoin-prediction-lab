"""
research/download_binance_funding_history.py — Resumable, Rate-Limit-Aware Binance Funding Downloader
=====================================================================================================
Acquires the full historical funding rate series for BTCUSDT from the official Binance USD-M Futures
public endpoint: GET /fapi/v1/fundingRate
Historical window: 2022-01-01 00:00:00 UTC to 2026-09-01 06:00:00 UTC.

Provable Characteristics:
- Free public REST API, weight 1 per request.
- No authentication or private keys required.
- Standard settlement schedule: Every 8 hours (00:00, 08:00, 16:00 UTC).
- Full historical depth supported back to contract inception (September 2019).
- Saves non-destructively to data/raw/binance_funding_2022_2026.parquet (preserving data/raw/funding.parquet).
"""

import os
import sys
import time
import json
import urllib.request
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_PATH = os.path.join(REPO_ROOT, "data", "raw", "binance_funding_2022_2026.parquet")


def download_binance_funding_rates(
    symbol: str = "BTCUSDT",
    start_dt: str = "2022-01-01 00:00:00+00:00",
    end_dt: str = "2026-09-01 06:00:00+00:00",
    max_retries: int = 5,
    sleep_sec: float = 0.3
) -> pd.DataFrame:
    start_ms = int(pd.to_datetime(start_dt).timestamp() * 1000)
    end_ms = int(pd.to_datetime(end_dt).timestamp() * 1000)

    print(f"Downloading historical funding rates for {symbol}...")
    print(f"Time range: {start_dt} to {end_dt} ({start_ms} to {end_ms} ms)")

    all_records = []
    cur_start = start_ms

    while cur_start < end_ms:
        url = (
            f"https://fapi.binance.com/fapi/v1/fundingRate"
            f"?symbol={symbol}&startTime={cur_start}&endTime={end_ms}&limit=1000"
        )
        batch = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "BTCognitive-Research/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        batch = json.loads(resp.read().decode("utf-8"))
                        break
            except Exception as e:
                print(f"  Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying...")
                time.sleep(1.0 * (attempt + 1))

        if batch is None:
            raise RuntimeError(f"Failed to fetch funding rates starting at {cur_start} after {max_retries} attempts.")

        if not batch:
            print("  Empty batch returned. Reached end of historical data.")
            break

        all_records.extend(batch)
        last_time = batch[-1]["fundingTime"]
        last_dt = pd.to_datetime(last_time, unit="ms", utc=True)
        print(f"  Fetched batch of {len(batch)} records | Latest funding timestamp: {last_dt}")

        if len(batch) < 1000 or last_time <= cur_start:
            break

        cur_start = last_time + 1
        time.sleep(sleep_sec)

    print(f"\nTotal raw funding rate records fetched: {len(all_records):,}")
    df = pd.DataFrame(all_records)
    if df.empty:
        raise ValueError("No funding rate records were returned.")

    df["timestamp"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
    df["funding_rate"] = df["fundingRate"].astype(float)
    df["mark_price"] = pd.to_numeric(df.get("markPrice", 0.0), errors="coerce").fillna(0.0)

    # Clean duplicates and sort
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    df = df[["timestamp", "symbol", "funding_rate", "mark_price", "fundingTime"]]

    # Verification of settlement intervals
    diffs = df["timestamp"].diff().dropna()
    print("\nDataset Verification Summary:")
    print(f"  First observation: {df['timestamp'].min()}")
    print(f"  Last observation:  {df['timestamp'].max()}")
    print(f"  Total records:     {len(df):,}")
    print(f"  Step frequencies:\n{diffs.value_counts().to_string()}")

    # Save to parquet
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"\nSaved verified funding history to:\n  {OUTPUT_PATH}")
    return df


if __name__ == "__main__":
    download_binance_funding_rates()
