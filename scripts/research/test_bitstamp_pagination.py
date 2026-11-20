"""
Bitstamp Historical OHLC Pagination & Retention Investigation Script.
Tests documented Bitstamp OHLC query parameters:
- step=3600 (1h)
- step=300 (5m)
- start, end, limit parameters
- Pagination bounds, gaps, and retention limits.
"""

import sys
import os
import json
import time
import subprocess
from datetime import datetime, timezone

def fetch_bitstamp(step: int, limit: int = 5, start: int = None, end: int = None):
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
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if p.returncode != 0 or not p.stdout.strip():
        return False, f"RC: {p.returncode}, Stderr: {p.stderr.strip()[:300]}, Stdout: {p.stdout.strip()[:100]}"
    try:
        data = json.loads(p.stdout.strip())
        return True, data
    except Exception as e:
        return False, f"JSON decode error: {e}; raw: {p.stdout[:200]}"

if __name__ == "__main__":
    print("--- 1. Testing step=3600 (1h) with start=1704067200 (2024-01-01) ---")
    ok, res = fetch_bitstamp(step=3600, limit=5, start=1704067200)
    print("Success:", ok)
    if ok:
        ohlc = res.get("data", {}).get("ohlc", [])
        print("Received bars:", len(ohlc))
        for b in ohlc:
            ts = int(b["timestamp"])
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            print(f"  ts={ts} ({dt}) O={b['open']} H={b['high']} L={b['low']} C={b['close']}")
    else:
        print("Error:", res)

    print("\n[Sleeping 3.0s to respect Incapsula rate limit...]")
    time.sleep(3.0)

    print("\n--- 2. Testing step=300 (5m) with limit=5 ---")
    ok5, res5 = fetch_bitstamp(step=300, limit=5)
    print("Success:", ok5)
    if ok5:
        ohlc5 = res5.get("data", {}).get("ohlc", [])
        print("Received bars:", len(ohlc5))
        for b in ohlc5:
            ts = int(b["timestamp"])
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            print(f"  ts={ts} ({dt}) O={b['open']} H={b['high']} L={b['low']} C={b['close']}")
    else:
        print("Error:", res5)

    print("\n[Sleeping 3.0s to respect Incapsula rate limit...]")
    time.sleep(3.0)

    print("\n--- 3. Testing step=300 (5m) with start=1704067200 (2024-01-01) retention check ---")
    ok5_hist, res5_hist = fetch_bitstamp(step=300, limit=5, start=1704067200)
    print("Success:", ok5_hist)
    if ok5_hist:
        ohlc5_h = res5_hist.get("data", {}).get("ohlc", [])
        print("Received bars:", len(ohlc5_h))
        for b in ohlc5_h:
            ts = int(b["timestamp"])
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            print(f"  ts={ts} ({dt}) O={b['open']} H={b['high']} L={b['low']} C={b['close']}")
    else:
        print("Error:", res5_hist)
