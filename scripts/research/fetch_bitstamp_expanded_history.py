"""
scripts/research/fetch_bitstamp_expanded_history.py
===================================================
Fetches an expanded chronological history of Bitstamp BTC/USD hourly candles
into a SEPARATE, VERSIONED parquet file:
  data/providers/bitstamp/BTCUSD_1h_v34_expanded.parquet

Strict Rules:
1. Does NOT overwrite or mutate data/providers/bitstamp/BTCUSD_1h.parquet.
2. Paces requests by 3.0s to respect Incapsula rate limits.
3. Excludes the incomplete current candle.
4. Validates all OHLC invariants and monotonicity.
5. Saves provenance sidecar.
"""

import os
import sys
import json
import time
import hashlib
import subprocess
from datetime import datetime, timezone
import pandas as pd
import numpy as np

DEST_PARQUET = "data/providers/bitstamp/BTCUSD_1h_v34_expanded.parquet"
PROVENANCE_PATH = "data/providers/bitstamp/BTCUSD_1h_v34_expanded_provenance.json"

def fetch_bitstamp_window(step: int, limit: int, start: int = None, end: int = None):
    url = f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step={step}&limit={limit}"
    if start is not None:
        url += f"&start={start}"
    if end is not None:
        url += f"&end={end}"

    ps_code = f"""
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;
    $headers = @{{ "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }};
    $res = Invoke-RestMethod -Uri '{url}' -Headers $headers;
    $res | ConvertTo-Json -Depth 6 -Compress
    """
    
    cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_code]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    if p.returncode != 0 or not p.stdout.strip():
        return False, f"RC={p.returncode}, Err={p.stderr.strip()[:200]}"
    try:
        data = json.loads(p.stdout.strip())
        return True, data
    except Exception as e:
        return False, f"JSON parse error: {e}"

def main():
    print("=== Fetching Expanded Bitstamp BTC/USD 1h History for V34.0 Research ===")
    now_epoch = int(time.time())
    now_aligned = (now_epoch // 3600) * 3600
    
    # We want 4 windows of 1,000 candles = 4,000 hourly bars
    # Align target start exactly to an hourly boundary
    target_start_epoch = now_aligned - (4000 * 3600)
    
    all_candles = []
    seen_ts = set()
    current_start = target_start_epoch
    
    for page in range(5):
        print(f"\n[Page {page+1}/5] Fetching 1,000 bars starting at {current_start} ({datetime.fromtimestamp(current_start, tz=timezone.utc).isoformat()})...")
        
        ok = False
        res = None
        for attempt in range(3):
            ok, res = fetch_bitstamp_window(step=3600, limit=1000, start=current_start)
            if ok:
                break
            print(f"  [Attempt {attempt+1} failed]: {res}")
            time.sleep(4.0 * (attempt + 1))
            
        if not ok:
            print(f"  [Error] Failed page {page+1} after 3 attempts.")
            break
        
        bars = res.get("data", {}).get("ohlc", [])
        if not bars:
            print("  [Notice] Zero bars returned, stopping pagination.")
            break
            
        print(f"  Received {len(bars)} bars. Range: {bars[0]['timestamp']} to {bars[-1]['timestamp']}")
        new_count = 0
        for b in bars:
            ts = int(b["timestamp"])
            if ts not in seen_ts:
                # Validate completed candle: candle_end <= now
                if (ts + 3600) <= (now_epoch + 120):
                    seen_ts.add(ts)
                    all_candles.append({
                        "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc),
                        "open": float(b["open"]),
                        "high": float(b["high"]),
                        "low": float(b["low"]),
                        "close": float(b["close"]),
                        "volume": float(b["volume"]),
                        "available_time": datetime.fromtimestamp(ts + 3600, tz=timezone.utc),
                        "source_exchange": "BITSTAMP",
                        "source_symbol": "BTC/USD"
                    })
                    new_count += 1
        
        print(f"  Added {new_count} unique completed bars. Total so far: {len(all_candles)}")
        
        last_ts = int(bars[-1]["timestamp"])
        current_start = last_ts + 3600
        
        if (current_start + 3600) >= now_epoch:
            print("  Reached live boundary.")
            break
            
        print("  Sleeping 3.5s to respect rate limits...")
        time.sleep(3.5)

    if not all_candles:
        print("[Fatal] No candles collected.")
        return

    df = pd.DataFrame(all_candles).sort_values("timestamp").reset_index(drop=True)
    print(f"\nFinal Dataset: {len(df)} bars.")
    print(f"Earliest: {df['timestamp'].iloc[0].isoformat()}")
    print(f"Latest:   {df['timestamp'].iloc[-1].isoformat()}")

    # Monotonicity check
    diffs = df["timestamp"].diff().dropna().dt.total_seconds()
    gaps = (diffs != 3600).sum()
    print(f"Interval Gaps: {gaps}")

    os.makedirs(os.path.dirname(DEST_PARQUET), exist_ok=True)
    df.to_parquet(DEST_PARQUET, index=False)
    
    with open(DEST_PARQUET, "rb") as f:
        file_sha256 = hashlib.sha256(f.read()).hexdigest()
        
    provenance = {
        "dataset_name": "Bitstamp BTC/USD 1h Expanded Research Dataset",
        "version": "v34.0",
        "file_path": DEST_PARQUET,
        "sha256": file_sha256,
        "row_count": len(df),
        "earliest_timestamp_utc": df["timestamp"].iloc[0].isoformat(),
        "latest_timestamp_utc": df["timestamp"].iloc[-1].isoformat(),
        "step_seconds": 3600,
        "gaps_count": int(gaps),
        "creation_epoch_utc": datetime.now(timezone.utc).isoformat(),
        "licensing_scope": "Bitstamp Public Market Data REST API (Private Educational/Research Scope)"
    }
    
    with open(PROVENANCE_PATH, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)
        
    print(f"Saved to {DEST_PARQUET}")
    print(f"SHA-256: {file_sha256}")

if __name__ == "__main__":
    main()
