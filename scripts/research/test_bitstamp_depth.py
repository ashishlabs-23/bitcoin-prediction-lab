import urllib.request
import json
import time
from datetime import datetime, timezone

def test_query(step, end_epoch, limit=5):
    url = f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step={step}&end={end_epoch}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ohlc = data.get("data", {}).get("ohlc", [])
            if ohlc:
                t0 = datetime.fromtimestamp(int(ohlc[0]["timestamp"]), tz=timezone.utc).isoformat()
                t1 = datetime.fromtimestamp(int(ohlc[-1]["timestamp"]), tz=timezone.utc).isoformat()
                print(f"step={step}, end={end_epoch} -> count={len(ohlc)}, first={t0}, last={t1}")
                return True, ohlc
            else:
                print(f"step={step}, end={end_epoch} -> empty ohlc")
                return False, []
    except Exception as e:
        print(f"step={step}, end={end_epoch} -> error: {e}")
        return False, []

if __name__ == "__main__":
    # In V34.1, last candle was 2026-11-02T17:00:00Z -> epoch 1793638800
    last_known_epoch = 1793638800
    one_year_ago = last_known_epoch - (365 * 86400)
    two_years_ago = last_known_epoch - (2 * 365 * 86400)
    three_years_ago = last_known_epoch - (3 * 365 * 86400)

    print("Testing 1h candles (step=3600):")
    test_query(3600, last_known_epoch)
    time.sleep(2)
    test_query(3600, one_year_ago)
    time.sleep(2)
    test_query(3600, two_years_ago)
    time.sleep(2)
    test_query(3600, three_years_ago)

    print("\nTesting 5m candles (step=300):")
    time.sleep(2)
    test_query(300, last_known_epoch)
    time.sleep(2)
    test_query(300, one_year_ago)
    time.sleep(2)
    test_query(300, two_years_ago)

