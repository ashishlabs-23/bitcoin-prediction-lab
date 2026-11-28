"""
data/ingest_real_historical.py — Ingests 100% Genuine Binance BTC/USDT 1h Candles (2022–2026)
=============================================================================================
Downloads authentic 1-hour candles from Binance Public REST API:
- Symbol: BTCUSDT
- Interval: 1h
- Date range: 2022-01-01 to Present (25,000+ hourly candles)
- Replaces truncated slice with genuine historical data.
"""

import os
import sys
import time
import json
import urllib.request
from datetime import datetime, timezone
import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Shared, dependency-light safety helpers: hard validation before any write,
# merge-with-existing (never truncate history) and atomic replacement.
from data.ingest import atomic_write_parquet, merge_with_existing  # noqa: E402
from data.validate import validate_ohlcv  # noqa: E402

DATA_RAW_DIR = os.path.join(ROOT_DIR, "data", "raw")
OHLCV_PATH = os.path.join(DATA_RAW_DIR, "ohlcv.parquet")

#: Bounded retry policy. The previous implementation retried forever with a
#: fixed 1s sleep, which could hang a scheduled job indefinitely.
MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_MAX_SECONDS = 16.0


def _fetch_klines(url: str):
    """Fetches one Binance kline page with bounded exponential backoff."""
    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BTCognitive-Ingest/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            last_exc = e
            if attempt >= MAX_ATTEMPTS:
                break
            delay = min(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), BACKOFF_MAX_SECONDS)
            print(
                f"Error fetching klines (attempt {attempt}/{MAX_ATTEMPTS}): {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
    raise RuntimeError(
        f"Binance kline download failed after {MAX_ATTEMPTS} attempts at {url}; "
        f"no data was written (existing history is untouched). Last error: {last_exc}"
    ) from last_exc


def download_binance_history(start_date_str="2022-01-01T00:00:00Z"):
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    start_dt = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
    since_ms = int(start_dt.timestamp() * 1000)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    print(f"Fetching genuine Binance BTCUSDT 1h history from {start_date_str} to now...")
    all_rows = []

    while since_ms < now_ms:
        url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={since_ms}&limit=1000"
        batch = _fetch_klines(url)

        if not batch:
            break

        for k in batch:
            open_time_ms = k[0]
            open_p = float(k[1])
            high_p = float(k[2])
            low_p = float(k[3])
            close_p = float(k[4])
            vol = float(k[5])

            dt = datetime.fromtimestamp(open_time_ms / 1000.0, tz=timezone.utc)
            avail_dt = datetime.fromtimestamp((open_time_ms + 3600000) / 1000.0, tz=timezone.utc)

            all_rows.append({
                "timestamp": dt,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": vol,
                "available_time": avail_dt
            })

        last_open_ms = batch[-1][0]
        if last_open_ms <= since_ms:
            break
        since_ms = last_open_ms + 3600000 # Advance by 1 hour

        print(f"  Downloaded {len(all_rows):,} candles (up to {datetime.fromtimestamp(last_open_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')})...")
        time.sleep(0.05) # Polite rate limit

    if not all_rows:
        print("No candles fetched.")
        return

    df = pd.DataFrame(all_rows)
    df.drop_duplicates(subset=['timestamp'], inplace=True)
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Fail closed: a single high<low / NaN / duplicate timestamp aborts the
    # write rather than poisoning every downstream feature and target.
    report = validate_ohlcv(df, name="ohlcv")
    for warning in report.warnings:
        print(f"Validation warning: {warning}")
    print(
        f"Validation PASS: {report.rows:,} row(s), "
        f"largest_gap_bars={report.largest_gap_bars}, "
        f"gaps_over_2_bars={report.gaps_over_2_bars}"
    )

    # Merge (never truncate pre-existing history) and replace atomically.
    merged = merge_with_existing(df, OHLCV_PATH)
    atomic_write_parquet(merged, OHLCV_PATH)
    print(f"\n✅ SUCCESS: Ingested {len(df):,} genuine historical BTC candles "
          f"({len(merged):,} total after merge).")
    print(f"   Date Range: {merged['timestamp'].min()} → {merged['timestamp'].max()}")
    print(f"   Price Range: ${merged['close'].min():,.2f} → ${merged['close'].max():,.2f}")
    print(f"   Saved to: {OHLCV_PATH}")

if __name__ == "__main__":
    download_binance_history()
