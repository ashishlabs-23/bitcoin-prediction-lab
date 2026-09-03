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
DATA_RAW_DIR = os.path.join(ROOT_DIR, "data", "raw")
OHLCV_PATH = os.path.join(DATA_RAW_DIR, "ohlcv.parquet")

def download_binance_history(start_date_str="2022-01-01T00:00:00Z"):
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    start_dt = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
    since_ms = int(start_dt.timestamp() * 1000)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    print(f"Fetching genuine Binance BTCUSDT 1h history from {start_date_str} to now...")
    all_rows = []

    while since_ms < now_ms:
        url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={since_ms}&limit=1000"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BTCognitive-Ingest/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                batch = json.loads(resp.read().decode())
        except Exception as e:
            print(f"Error fetching at {since_ms}: {e}. Retrying in 1s...")
            time.sleep(1.0)
            continue

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

    # Save to parquet
    df.to_parquet(OHLCV_PATH, index=False)
    print(f"\n✅ SUCCESS: Ingested {len(df):,} genuine historical BTC candles.")
    print(f"   Date Range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"   Price Range: ${df['close'].min():,.2f} → ${df['close'].max():,.2f}")
    print(f"   Saved to: {OHLCV_PATH}")

if __name__ == "__main__":
    download_binance_history()
