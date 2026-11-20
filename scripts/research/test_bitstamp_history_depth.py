import os
import json
import subprocess
from datetime import datetime, timezone

def test_start_query(step, start_epoch, limit=5):
    url = f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step={step}&limit={limit}&start={start_epoch}"
    ps_code = f"""
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;
    $headers = @{{ "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }};
    $res = Invoke-RestMethod -Uri '{url}' -Headers $headers;
    $res | ConvertTo-Json -Depth 6 -Compress
    """
    cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_code]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if p.returncode != 0 or not p.stdout.strip():
        return False, f"RC={p.returncode}, Err={p.stderr.strip()[:200]}"
    try:
        data = json.loads(p.stdout.strip())
        ohlc = data.get("data", {}).get("ohlc", [])
        if ohlc:
            t0 = datetime.fromtimestamp(int(ohlc[0]["timestamp"]), tz=timezone.utc).isoformat()
            t1 = datetime.fromtimestamp(int(ohlc[-1]["timestamp"]), tz=timezone.utc).isoformat()
            return True, f"Count={len(ohlc)}, t0={t0}, t1={t1}"
        else:
            return False, "Empty ohlc"
    except Exception as e:
        return False, f"JSON error: {e}"

if __name__ == "__main__":
    epochs = {
        "2025-01-01 (approx 1.8 years back)": 1735689600,
        "2024-01-01 (approx 2.8 years back)": 1704067200,
        "2023-01-01 (approx 3.8 years back)": 1672531200,
        "2020-01-01 (approx 6.8 years back)": 1577836800,
    }
    print("=== Testing Bitstamp Hourly History (step=3600) ===")
    for label, ep in epochs.items():
        ok, msg = test_start_query(3600, ep, limit=5)
        print(f"Hourly {label}: ok={ok}, {msg}")

    print("\n=== Testing Bitstamp 5-minute History (step=300) ===")
    for label, ep in list(epochs.items())[:2]:
        ok, msg = test_start_query(300, ep, limit=5)
        print(f"5m {label}: ok={ok}, {msg}")

