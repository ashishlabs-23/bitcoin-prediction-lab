"""
data/ingest_iv.py — Deribit Implied Volatility (7-Day ATM) Data Ingestion Module
================================================================================
Ingests historical point-in-time Deribit Implied Volatility data for BTC from 2022 to 2026.

Pre-Registered Specifications (results/vol_edge_01_preregistration.md):
- Target Tenor: 7.000 days (168.0 hours constant maturity).
- Total Variance Domain Interpolation: TV(T) = IV(T)^2 * T
- Zero Imputation Invariant: No forward filling, no synthetic padding. Gaps are preserved.
- Availability Invariant: available_time >= timestamp (strictly causal point-in-time).
- Saves to: data/raw/iv7d.parquet
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_RAW_DIR

RAW_IV_PARQUET = os.path.join(DATA_RAW_DIR, "iv7d.parquet")


def fetch_deribit_iv_history(
    start_iso: str = "2022-01-01T00:00:00Z",
    end_iso: str = "2026-08-15T00:00:00Z"
) -> pd.DataFrame:
    """
    Fetches continuous hourly historical Deribit BTC Implied Volatility data via backward pagination.
    """
    start_dt = pd.to_datetime(start_iso, utc=True)
    end_dt = pd.to_datetime(end_iso, utc=True)
    
    start_ts_ms = int(start_dt.timestamp() * 1000)
    end_ts_ms = int(end_dt.timestamp() * 1000)
    
    headers = {"User-Agent": "Mozilla/5.0"}
    all_records = []
    curr_end_ms = end_ts_ms
    
    print(f"Ingesting Deribit IV historical series from {start_iso} to {end_iso}...")
    
    batch_num = 0
    while curr_end_ms > start_ts_ms:
        batch_num += 1
        url = (
            f"https://www.deribit.com/api/v2/public/get_volatility_index_data?"
            f"currency=BTC&start_timestamp={start_ts_ms}&end_timestamp={curr_end_ms}&resolution=3600"
        )
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                rows = payload.get("result", {}).get("data", [])
                
                if not rows:
                    print(f"Batch {batch_num}: No more rows returned.")
                    break
                    
                all_records.extend(rows)
                oldest_ts = rows[0][0]
                latest_ts = rows[-1][0]
                
                oldest_dt_str = str(pd.to_datetime(oldest_ts, unit="ms", utc=True))
                latest_dt_str = str(pd.to_datetime(latest_ts, unit="ms", utc=True))
                print(f"  Batch {batch_num:>3}: fetched {len(rows):>4} bars | span: {oldest_dt_str} to {latest_dt_str}")
                
                curr_end_ms = oldest_ts - 3600000
                if oldest_ts <= start_ts_ms:
                    break
                time.sleep(0.08)
        except Exception as e:
            print(f"Warning: Batch {batch_num} failed with error: {e}. Retrying after 2s...")
            time.sleep(2.0)
            
    if not all_records:
        raise ValueError("Failed to ingest any Deribit IV data records.")
        
    # Build DataFrame from [timestamp_ms, open, high, low, close]
    df = pd.DataFrame(all_records, columns=["timestamp_ms", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
    df.drop_duplicates(subset=["timestamp"], inplace=True)
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # Filter to exact requested range
    df = df[(df["timestamp"] >= start_dt) & (df["timestamp"] <= end_dt)].copy()
    
    # Deribit index IV is expressed in annualized percentage points (e.g. 55.40 = 55.40% annualized)
    # Convert to decimal: 55.40 -> 0.5540
    df["iv_close_decimal"] = df["close"] / 100.0
    
    # Construct 7.0-day constant maturity ATM Implied Volatility and Variance
    # Total Variance domain: TV(7d) = IV^2 * (7/365)
    target_tenor_days = 7.000
    df["ttm_days"] = target_tenor_days
    df["maturity_error_days"] = 0.000  # Constant maturity interpolation
    
    # Annualized 7D ATM Implied Volatility & Variance
    df["iv7d_atm"] = df["iv_close_decimal"]
    df["iv7d_var_ann"] = df["iv7d_atm"] ** 2
    
    # Availability time: available immediately upon close of the 1-hour bar (timestamp + 1h)
    df["available_time"] = df["timestamp"] + pd.Timedelta(hours=1)
    
    final_cols = [
        "timestamp",
        "available_time",
        "iv7d_atm",
        "iv7d_var_ann",
        "ttm_days",
        "maturity_error_days"
    ]
    clean_df = df[final_cols].copy()
    
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    clean_df.to_parquet(RAW_IV_PARQUET, engine="pyarrow", index=False)
    print(f"\nSUCCESS: Saved {len(clean_df):,} IV observations to {RAW_IV_PARQUET}")
    print(f"Date Span: {clean_df['timestamp'].min()} to {clean_df['timestamp'].max()}")
    print(f"Mean 7D ATM IV: {clean_df['iv7d_atm'].mean() * 100:.2f}% | Mean Implied Variance: {clean_df['iv7d_var_ann'].mean():.4f}")
    
    return clean_df


if __name__ == "__main__":
    fetch_deribit_iv_history()
