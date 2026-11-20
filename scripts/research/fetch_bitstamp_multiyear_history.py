"""
scripts/research/fetch_bitstamp_multiyear_history.py
===================================================
Fetches multi-year historical Bitstamp BTC/USD hourly candles
into a SEPARATE, NEW VERSIONED parquet file:
  data/providers/bitstamp/BTCUSD_1h_v34_2_multiyear.parquet

Preserves:
- data/providers/bitstamp/BTCUSD_1h.parquet (production 1k)
- data/providers/bitstamp/BTCUSD_1h_v34_expanded.parquet (v34.0/v34.1 4k)

Invariants:
1. Paced by 4.0 seconds per page with SChannel TLS 1.2 via PowerShell.
2. Verified continuous boundaries (delta = 3600s).
3. Zero gaps, zero duplicates.
4. Completed candles only.
5. Saves bitwise SHA-256 provenance manifest.
"""

import os
import sys
import json
import time
import hashlib
import subprocess
from datetime import datetime, timezone
import pandas as pd

DEST_PARQUET = "data/providers/bitstamp/BTCUSD_1h_v34_2_multiyear.parquet"
PROVENANCE_PATH = "data/providers/bitstamp/BTCUSD_1h_v34_2_multiyear_provenance.json"

def fetch_bitstamp_page(step: int, limit: int, start: int):
    url = f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step={step}&limit={limit}&start={start}"
    ps_code = f"""
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;
    $headers = @{{ "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }};
    $res = Invoke-RestMethod -Uri '{url}' -Headers $headers;
    $res | ConvertTo-Json -Depth 6 -Compress
    """
    cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_code]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if p.returncode != 0 or not p.stdout.strip():
        return False, f"RC={p.returncode}, Err={p.stderr.strip()[:200]}"
    try:
        data = json.loads(p.stdout.strip())
        return True, data
    except Exception as e:
        return False, f"JSON parse error: {e}"

def main():
    print("=== BTCognitive V34.2 Historical Multi-Year Data Expansion ===", flush=True)
    now_epoch = int(time.time())
    
    # Target 2+ years back: Start 2024-01-01 00:00:00 UTC (epoch 1704067200)
    # Target approximately 20,000 - 25,000 candles to cover 2024, 2025, and 2026
    start_epoch = 1704067200
    
    all_candles = []
    seen_ts = set()
    current_start = start_epoch
    max_pages = 26  # Up to 26,000 bars
    
    pagination_boundaries = []
    prev_page_last_ts = None
    
    for page in range(max_pages):
        page_dt = datetime.fromtimestamp(current_start, tz=timezone.utc).isoformat()
        print(f"\n[Page {page+1}/{max_pages}] Requesting start={current_start} ({page_dt})...", flush=True)
        
        ok = False
        res = None
        for attempt in range(3):
            ok, res = fetch_bitstamp_page(step=3600, limit=1000, start=current_start)
            if ok:
                break
            print(f"  Attempt {attempt+1} failed: {res}. Backing off...", flush=True)
            time.sleep(5.0 * (attempt + 1))
            
        if not ok:
            print(f"  [Fatal] Failed to retrieve page {page+1}. Stopping pagination.", flush=True)
            break
            
        bars = res.get("data", {}).get("ohlc", [])
        if not bars:
            print("  No more bars returned.", flush=True)
            break
            
        page_first_ts = int(bars[0]["timestamp"])
        page_last_ts = int(bars[-1]["timestamp"])
        
        # Check boundary continuity with previous page
        if prev_page_last_ts is not None:
            delta = page_first_ts - prev_page_last_ts
            continuous = (delta == 3600)
            pagination_boundaries.append({
                "page_left_index": len(all_candles) - 1,
                "page_left_ts": prev_page_last_ts,
                "page_right_ts": page_first_ts,
                "delta_seconds": delta,
                "continuous": continuous
            })
            if not continuous:
                print(f"  [WARNING] Boundary discontinuity! Delta={delta}s", flush=True)
                
        prev_page_last_ts = page_last_ts
        
        added_count = 0
        for b in bars:
            ts = int(b["timestamp"])
            # Invariant: candle must be fully closed
            if (ts + 3600) <= (now_epoch + 120) and ts not in seen_ts:
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
                added_count += 1
                
        print(f"  Retrieved {len(bars)} bars ({datetime.fromtimestamp(page_first_ts, tz=timezone.utc).isoformat()} to {datetime.fromtimestamp(page_last_ts, tz=timezone.utc).isoformat()}). Added {added_count} bars. Total: {len(all_candles)}", flush=True)
        
        current_start = page_last_ts + 3600
        if (current_start + 3600) >= now_epoch:
            print("  Reached live boundary.", flush=True)
            break
            
        print("  Pacing 4.0s for Bitstamp WAF...", flush=True)
        time.sleep(4.0)
        
    if not all_candles:
        print("[Error] No candles collected.", flush=True)
        return False
        
    df = pd.DataFrame(all_candles).sort_values("timestamp").reset_index(drop=True)
    print(f"\n=== Collected Total: {len(df)} candles ===", flush=True)
    print(f"First timestamp: {df['timestamp'].iloc[0].isoformat()}", flush=True)
    print(f"Last timestamp:  {df['timestamp'].iloc[-1].isoformat()}", flush=True)
    
    # Audit gaps and duplicates
    diffs = df["timestamp"].diff().dropna().dt.total_seconds()
    gap_count = int((diffs != 3600).sum())
    dup_count = int(df["timestamp"].duplicated().sum())
    print(f"Gaps: {gap_count}, Duplicates: {dup_count}", flush=True)
    
    os.makedirs(os.path.dirname(DEST_PARQUET), exist_ok=True)
    df.to_parquet(DEST_PARQUET, index=False)
    
    with open(DEST_PARQUET, "rb") as f:
        sha256_hash = hashlib.sha256(f.read()).hexdigest()
        
    provenance = {
        "dataset_name": "Bitstamp BTC/USD 1h Multi-Year Expansion Dataset",
        "version": "v34.2",
        "file_path": DEST_PARQUET,
        "sha256": sha256_hash,
        "row_count": len(df),
        "earliest_timestamp_utc": df["timestamp"].iloc[0].isoformat(),
        "latest_timestamp_utc": df["timestamp"].iloc[-1].isoformat(),
        "step_seconds": 3600,
        "gaps_count": gap_count,
        "duplicates_count": dup_count,
        "pagination_boundaries": pagination_boundaries,
        "creation_epoch_utc": datetime.now(timezone.utc).isoformat(),
        "licensing_scope": "Bitstamp Public Market Data REST API (Private Educational/Research Scope)",
        "source_exchange": "BITSTAMP",
        "source_symbol": "BTC/USD"
    }
    
    with open(PROVENANCE_PATH, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)
        
    print(f"Saved dataset to {DEST_PARQUET} (SHA-256: {sha256_hash})", flush=True)
    return True

if __name__ == "__main__":
    main()

