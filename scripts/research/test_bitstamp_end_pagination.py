import json
import subprocess
import time
from datetime import datetime, timezone

def test_end_query(step, end_epoch, limit=5):
    url = f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step={step}&limit={limit}&end={end_epoch}"
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
        return True, ohlc
    except Exception as e:
        return False, f"JSON error: {e}"

if __name__ == "__main__":
    # Test bounded end-only request
    # Let's test with end_epoch = 1735689600 (2025-01-01 00:00:00 UTC)
    test_end = 1735689600
    print(f"Testing end-only query with end={test_end} ({datetime.fromtimestamp(test_end, tz=timezone.utc).isoformat()})...")
    ok, ohlc = test_end_query(3600, test_end, limit=5)
    if ok and isinstance(ohlc, list):
        print(f"Retrieved {len(ohlc)} candles:")
        for idx, b in enumerate(ohlc):
            ts = int(b["timestamp"])
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            print(f"  [{idx}] ts={ts} ({dt}), close={b['close']}")
        first_ts = int(ohlc[0]["timestamp"])
        last_ts = int(ohlc[-1]["timestamp"])
        print(f"\nBoundary Analysis:")
        print(f"  Target end epoch:   {test_end} ({datetime.fromtimestamp(test_end, tz=timezone.utc).isoformat()})")
        print(f"  Actual last candle: {last_ts} ({datetime.fromtimestamp(last_ts, tz=timezone.utc).isoformat()})")
        print(f"  Difference (end - last): {test_end - last_ts}s ({(test_end - last_ts)/3600} hours)")
        print(f"  Is end inclusive? {'YES (last ts == end)' if last_ts == test_end else 'NO (last ts < end or offset)'}")
    else:
        print(f"Failed: {ohlc}")

