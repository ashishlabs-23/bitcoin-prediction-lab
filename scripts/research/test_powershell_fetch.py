import json
import subprocess
import time
from datetime import datetime, timezone

def fetch_bitstamp_ohlc_powershell(step, end_epoch, limit=1000):
    url = f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step={step}&end={end_epoch}&limit={limit}"
    ps_cmd = (
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; "
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        f"(Invoke-RestMethod -Uri '{url}' -UserAgent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)') | ConvertTo-Json -Depth 6 -Compress"
    )
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        return None, proc.stderr.strip()
    raw = proc.stdout.strip()
    if not raw:
        return None, "empty output"
    data = json.loads(raw)
    ohlc = data.get("data", {}).get("ohlc", [])
    return ohlc, None

if __name__ == "__main__":
    # Test 1: Query 1h candles from 2026-05-20 (epoch 1779242400)
    print("Testing 1h query before 2026-05-20...")
    ohlc, err = fetch_bitstamp_ohlc_powershell(3600, 1779242400, limit=10)
    if ohlc:
        t0 = datetime.fromtimestamp(int(ohlc[0]["timestamp"]), tz=timezone.utc).isoformat()
        t1 = datetime.fromtimestamp(int(ohlc[-1]["timestamp"]), tz=timezone.utc).isoformat()
        print(f"Success 1h: {len(ohlc)} candles from {t0} to {t1}")
    else:
        print(f"Error 1h: {err}")

    time.sleep(3)
    # Test 2: Query 5m candles
    print("Testing 5m query...")
    ohlc_5m, err = fetch_bitstamp_ohlc_powershell(300, 1793638800, limit=10)
    if ohlc_5m:
        t0 = datetime.fromtimestamp(int(ohlc_5m[0]["timestamp"]), tz=timezone.utc).isoformat()
        t1 = datetime.fromtimestamp(int(ohlc_5m[-1]["timestamp"]), tz=timezone.utc).isoformat()
        print(f"Success 5m: {len(ohlc_5m)} candles from {t0} to {t1}")
    else:
        print(f"Error 5m: {err}")

