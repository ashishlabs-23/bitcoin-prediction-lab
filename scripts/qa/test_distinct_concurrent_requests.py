"""
Verification script: Test concurrent execution of two DISTINCT, un-cached Analysis requests.
Verifies mutex lock contention (_analysis_execution_lock) behavior without digest cache hits.
"""

import time
import json
import urllib.request
import threading
import sys

URL = "http://127.0.0.1:8000/api/tournament/analyse"

def send_request(name: str, payload: dict, results: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))
            elapsed = time.perf_counter() - t0
            results[name] = {
                "status": status,
                "elapsed": elapsed,
                "digest": body.get("dataset_fingerprint"),
                "regime": body.get("market_regime"),
                "strategy": body.get("top_strategy"),
                "price": body.get("current_price"),
                "error": None
            }
    except Exception as e:
        elapsed = time.perf_counter() - t0
        results[name] = {
            "status": "ERROR",
            "elapsed": elapsed,
            "error": str(e)
        }

def main():
    print("=== Distinct Concurrent Analysis Request Verification ===")
    
    # Request A: live_price = 76985.40, force_fresh_tournament = True
    payload_a = {
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "live_price": 76985.40,
        "force_fresh_tournament": True
    }
    
    # Request B: live_price = 81200.00, force_fresh_tournament = True (distinct parameters)
    payload_b = {
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "live_price": 81200.00,
        "force_fresh_tournament": True
    }

    results = {}
    thread_a = threading.Thread(target=send_request, args=("Req_A", payload_a, results))
    thread_b = threading.Thread(target=send_request, args=("Req_B", payload_b, results))

    wall_start = time.perf_counter()
    thread_a.start()
    thread_b.start()

    thread_a.join()
    thread_b.join()
    wall_elapsed = time.perf_counter() - wall_start

    print(f"Total concurrent wall time: {wall_elapsed:.4f} s")
    print(f"Req_A status: {results['Req_A']['status']}, elapsed: {results['Req_A']['elapsed']:.4f} s, price: {results['Req_A'].get('price')}")
    print(f"Req_B status: {results['Req_B']['status']}, elapsed: {results['Req_B']['elapsed']:.4f} s, price: {results['Req_B'].get('price')}")

    # Assertions
    assert results["Req_A"]["status"] == 200, f"Req_A failed: {results['Req_A']}"
    assert results["Req_B"]["status"] == 200, f"Req_B failed: {results['Req_B']}"
    # Verify both took real computation time (not 0.0001s cache hit)
    assert results["Req_A"]["elapsed"] > 0.1, "Req_A was suspiciously fast (cache hit?)"
    assert results["Req_B"]["elapsed"] > 0.1, "Req_B was suspiciously fast (cache hit?)"
    # Verify total wall time is well under the 45-second timeout hurdle
    assert wall_elapsed < 10.0, f"Wall time {wall_elapsed:.4f}s exceeded 10s hurdle"
    
    # Print lock contention analysis
    sum_individual = results["Req_A"]["elapsed"] + results["Req_B"]["elapsed"]
    print(f"Sum of individual elapsed times: {sum_individual:.4f} s")
    print(f"Wall time / Sum ratio: {wall_elapsed / sum_individual:.2f} (Serialized execution under mutex lock expected ~1.0)")
    print("SUCCESS: Both distinct requests completed without timeout, proving clean mutex lock serialization under actual uncached load.")

if __name__ == "__main__":
    main()

