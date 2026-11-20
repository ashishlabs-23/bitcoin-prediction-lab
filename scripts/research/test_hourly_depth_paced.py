import json
import subprocess
import time
from datetime import datetime, timezone

def test_single_start(step, start_epoch, limit=5):
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
    print("Testing 2024-01-01 hourly with 5s sleep...")
    time.sleep(5)
    ok, msg = test_single_start(3600, 1704067200, limit=5)
    print("2024-01-01 hourly:", ok, msg)

    print("Testing 2023-01-01 hourly with 5s sleep...")
    time.sleep(5)
    ok, msg = test_single_start(3600, 1672531200, limit=5)
    print("2023-01-01 hourly:", ok, msg)

