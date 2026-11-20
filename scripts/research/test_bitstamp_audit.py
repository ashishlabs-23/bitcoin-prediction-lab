import urllib.request
import json
import time
from datetime import datetime, timezone

def fetch_bitstamp_ohlc(step, end_epoch, limit=1000, max_retries=3):
    url = f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step={step}&end={end_epoch}&limit={limit}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ohlc = data.get("data", {}).get("ohlc", [])
                return ohlc
        except Exception as e:
            print(f"  Attempt {attempt+1} failed for end={end_epoch}: {e}")
            time.sleep(4 * (attempt + 1))
    return None

if __name__ == "__main__":
    # Test 1: Check the boundary right before our existing 4,000 bars
    # In V34.1: first candle was 2026-05-20T02:00:00Z -> epoch 1779242400
    # Let's test end_epoch = 1779242400 (which should return candles leading up to 2026-05-20)
    print("Test 1: Query page prior to 2026-05-20T02:00:00Z...")
    ohlc = fetch_bitstamp_ohlc(step=3600, end_epoch=1779242400, limit=10)
    if ohlc:
        t0 = datetime.fromtimestamp(int(ohlc[0]["timestamp"]), tz=timezone.utc).isoformat()
        t1 = datetime.fromtimestamp(int(ohlc[-1]["timestamp"]), tz=timezone.utc).isoformat()
        print(f"Success: retrieved {len(ohlc)} bars: {t0} to {t1}")
    else:
        print("Failed to retrieve.")

    time.sleep(4)

    # Test 2: Check 5-minute candles retention
    print("\nTest 2: Query 5m candles (step=300) from 2026-11-02...")
    ohlc_5m = fetch_bitstamp_ohlc(step=300, end_epoch=1793638800, limit=10)
    if ohlc_5m:
        t0 = datetime.fromtimestamp(int(ohlc_5m[0]["timestamp"]), tz=timezone.utc).isoformat()
        t1 = datetime.fromtimestamp(int(ohlc_5m[-1]["timestamp"]), tz=timezone.utc).isoformat()
        print(f"Success 5m: retrieved {len(ohlc_5m)} bars: {t0} to {t1}")
    else:
        print("Failed 5m.")

