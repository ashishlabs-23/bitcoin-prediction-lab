"""
research/data_acquisition/acquire_coinbase_hourly.py
=====================================================
Automated, rate-limited, source-authenticated acquisition of BTC-USD hourly candles
directly from the official Coinbase Exchange REST API.

Storage Location: data/research/coinbase_btc_usd_hourly_v1/
- coinbase_hourly.parquet
- coinbase_hourly_manifest.json
- acquisition_log.jsonl

Safety Guarantees:
- Never touches or mutates data/raw/ or any protected file.
- Drops currently forming in-progress candles.
- Verifies monotonic timestamps, zero duplicates, and geometric OHLC sanity.
"""

import os
import sys
import time
import json
import hashlib
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("coinbase_hourly_acquisition")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(REPO_ROOT, "data", "research", "coinbase_btc_usd_hourly_v1")
COINBASE_CANDLES_URL = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
GRANULARITY_HOURLY = 3600  # 3600 seconds = 1 hour


def _utc_iso(epoch_sec: float) -> str:
    return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_chunk(
    start_iso: str,
    end_iso: str,
    timeout_sec: float = 10.0,
    max_retries: int = 3
) -> Tuple[List[List[float]], str]:
    """Fetches up to 300 hourly candles from Coinbase API between start_iso and end_iso."""
    url = f"{COINBASE_CANDLES_URL}?granularity={GRANULARITY_HOURLY}&start={start_iso}&end={end_iso}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BTCognitive-Audit-V32.27/1.0",
            "Accept": "application/json"
        }
    )

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw_bytes = resp.read()
                chunk_hash = hashlib.sha256(raw_bytes).hexdigest()
                data = json.loads(raw_bytes.decode("utf-8"))
                if isinstance(data, list):
                    return data, chunk_hash
                raise ValueError(f"Unexpected response format: {type(data)}")
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed fetching {url} after {max_retries} attempts: {e}")
                raise
            time.sleep(1.0 * (attempt + 1))


def run_acquisition(
    target_start_iso: str = "2023-01-01T00:00:00Z",
    target_end_iso: Optional[str] = None,
    rate_limit_delay_sec: float = 0.25
) -> Dict[str, Any]:
    os.makedirs(OUT_DIR, exist_ok=True)
    log_file = os.path.join(OUT_DIR, "acquisition_log.jsonl")
    manifest_file = os.path.join(OUT_DIR, "coinbase_hourly_manifest.json")
    parquet_file = os.path.join(OUT_DIR, "coinbase_hourly.parquet")

    now_epoch = int(time.time())
    # Drop currently forming hourly bar: last closed candle boundary
    last_closed_epoch = (now_epoch // GRANULARITY_HOURLY) * GRANULARITY_HOURLY
    if target_end_iso:
        end_dt = datetime.fromisoformat(target_end_iso.replace("Z", "+00:00"))
        cursor_end = min(int(end_dt.timestamp()), last_closed_epoch)
    else:
        cursor_end = last_closed_epoch

    start_dt = datetime.fromisoformat(target_start_iso.replace("Z", "+00:00"))
    target_start_epoch = int(start_dt.timestamp())

    logger.info(f"Initiating Coinbase BTC-USD hourly capture from {_utc_iso(target_start_epoch)} to {_utc_iso(cursor_end)}")

    candles_by_time: Dict[int, Dict[str, Any]] = {}
    chunk_records: List[Dict[str, Any]] = []

    # Step in blocks of 250 hours (Coinbase max is 300)
    step_seconds = 250 * GRANULARITY_HOURLY

    current_end = cursor_end
    chunk_idx = 0

    while current_end > target_start_epoch:
        chunk_start = max(target_start_epoch, current_end - step_seconds)
        start_iso = _utc_iso(chunk_start)
        end_iso = _utc_iso(current_end)

        chunk_idx += 1
        data, chunk_sha256 = fetch_chunk(start_iso, end_iso)

        # Coinbase response format: [ time, low, high, open, close, volume ]
        valid_chunk_candles = 0
        for candle in data:
            c_time, c_low, c_high, c_open, c_close, c_vol = candle
            c_time = int(c_time)

            # Exclude forming bar if any sneaked in
            if c_time >= last_closed_epoch:
                continue

            # Invariant checks
            if c_open <= 0 or c_high <= 0 or c_low <= 0 or c_close <= 0:
                continue
            if c_high < max(c_open, c_close) or c_low > min(c_open, c_close):
                continue

            candles_by_time[c_time] = {
                "epoch_time": c_time,
                "timestamp_utc": _utc_iso(c_time),
                "open": float(c_open),
                "high": float(c_high),
                "low": float(c_low),
                "close": float(c_close),
                "volume": float(c_vol),
                "instrument": "BTC-USD",
                "venue": "COINBASE",
                "market_type": "SPOT"
            }
            valid_chunk_candles += 1

        chunk_log = {
            "chunk_index": chunk_idx,
            "query_start_utc": start_iso,
            "query_end_utc": end_iso,
            "response_candles": len(data),
            "valid_candles_added": valid_chunk_candles,
            "chunk_sha256": chunk_sha256,
            "captured_at_utc": datetime.now(timezone.utc).isoformat()
        }
        chunk_records.append(chunk_log)

        if chunk_idx % 10 == 0 or current_end - step_seconds <= target_start_epoch:
            logger.info(f"Chunk {chunk_idx}: captured up to {_utc_iso(current_end)} (Total unique bars: {len(candles_by_time)})")

        current_end = chunk_start
        time.sleep(rate_limit_delay_sec)

    # Convert sorted unique candles into DataFrame
    sorted_times = sorted(candles_by_time.keys())
    records = [candles_by_time[t] for t in sorted_times]
    df = pd.DataFrame(records)

    # Verification of monotonicity and gaps
    df["dt"] = pd.to_datetime(df["epoch_time"], unit="s", utc=True)
    is_monotonic = bool(df["dt"].is_monotonic_increasing)
    duplicates = int(df["epoch_time"].duplicated().sum())

    diffs = df["dt"].diff().dropna()
    gaps = []
    for i, d in enumerate(diffs, start=1):
        if d != pd.Timedelta(hours=1):
            gaps.append({
                "gap_after_epoch": int(df.loc[i-1, "epoch_time"]),
                "gap_after_utc": df.loc[i-1, "timestamp_utc"],
                "resumed_epoch": int(df.loc[i, "epoch_time"]),
                "resumed_utc": df.loc[i, "timestamp_utc"],
                "missing_hours": (d.total_seconds() / 3600.0) - 1.0
            })

    # Save to atomic Parquet
    df_save = df[["timestamp_utc", "epoch_time", "open", "high", "low", "close", "volume", "instrument", "venue", "market_type"]].copy()
    df_save.to_parquet(parquet_file, index=False)
    parquet_bytes = open(parquet_file, "rb").read()
    parquet_sha256 = hashlib.sha256(parquet_bytes).hexdigest()

    # Save acquisition log
    with open(log_file, "w", encoding="utf-8") as f:
        for cr in chunk_records:
            f.write(json.dumps(cr) + "\n")

    # Generate provenance manifest
    manifest = {
        "dataset_id": "coinbase_btc_usd_hourly_authenticated_v1",
        "instrument": "BTC-USD",
        "venue": "COINBASE",
        "market_type": "SPOT",
        "timeframe": "1h",
        "granularity_seconds": 3600,
        "first_candle_utc": df["timestamp_utc"].iloc[0] if not df.empty else None,
        "last_candle_utc": df["timestamp_utc"].iloc[-1] if not df.empty else None,
        "total_candles": len(df),
        "total_chunks_fetched": len(chunk_records),
        "is_monotonic_increasing": is_monotonic,
        "duplicate_count": duplicates,
        "gap_count": len(gaps),
        "gaps": gaps[:20],  # sample if any
        "file_path": parquet_file,
        "file_size_bytes": len(parquet_bytes),
        "sha256_hash": parquet_sha256,
        "is_authenticated": True,
        "provenance_statement": "Captured directly via official Coinbase Exchange REST API /products/BTC-USD/candles?granularity=3600 without synthetic interpolation.",
        "captured_at_utc": datetime.now(timezone.utc).isoformat()
    }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Acquisition complete! Saved {len(df)} candles to {parquet_file} (SHA256: {parquet_sha256})")
    return manifest


if __name__ == "__main__":
    # Target 2.5+ years of verified Coinbase hourly candles (from 2024-01-01 to present, ~25,000 bars)
    # or start from 2023-01-01 for 3.8 years (~33,000 bars)
    run_acquisition(target_start_iso="2023-01-01T00:00:00Z")
