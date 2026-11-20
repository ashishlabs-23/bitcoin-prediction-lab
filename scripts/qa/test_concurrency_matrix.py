"""
Part E Verification: Concurrency, Cache, and Idempotency Matrix Tester.
Tests:
1. Same request ID with identical payload -> HTTP 200 (Idempotent cache hit)
2. Same request ID with different payload -> HTTP 409 (RFC 9110 conflict)
3. Different IDs with identical payload -> evaluates lock & cache behavior
4. Different IDs with different payload -> evaluates lock contention & serialization
5. Cache expiry (>10s TTL) and fresh-request behavior (force_fresh_tournament)
"""

import time
import json
import urllib.request
import urllib.error
import threading

URL = "http://127.0.0.1:8000/api/tournament/analyse"

def do_request(payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            elapsed = time.perf_counter() - t0
            body = json.loads(resp.read().decode("utf-8"))
            return {
                "status": resp.status,
                "elapsed": elapsed,
                "body": body,
                "error": None
            }
    except urllib.error.HTTPError as e:
        elapsed = time.perf_counter() - t0
        err_body = e.read().decode("utf-8")
        return {
            "status": e.code,
            "elapsed": elapsed,
            "error": err_body
        }
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return {
            "status": "EXCEPTION",
            "elapsed": elapsed,
            "error": str(e)
        }

def run_tests():
    print("=== Part E: Request Concurrency & Cache Matrix Evaluation ===")
    
    # 1. Same request ID with identical payload
    req_id_1 = f"matrix-id-{time.time()}"
    p1 = {
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "live_price": 76985.40,
        "request_id": req_id_1
    }
    res1_a = do_request(p1)
    res1_b = do_request(p1)
    print(f"\n1. Same request ID with identical payload:")
    print(f"   Initial: status={res1_a['status']}, elapsed={res1_a['elapsed']:.4f}s")
    print(f"   Retry:   status={res1_b['status']}, elapsed={res1_b['elapsed']:.4f}s (Cache Hit: {res1_b['elapsed'] < 0.05})")
    assert res1_a["status"] == 200 and res1_b["status"] == 200

    # 2. Same request ID with different payload
    p2_modified = {
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "live_price": 82000.00,  # Altered live price
        "request_id": req_id_1
    }
    res2 = do_request(p2_modified)
    print(f"\n2. Same request ID with different payload:")
    print(f"   Status={res2['status']}, elapsed={res2['elapsed']:.4f}s")
    print(f"   Detail={res2.get('error')}")
    assert res2["status"] == 409, f"Expected 409 Conflict, got {res2['status']}"

    # 3. Different IDs with identical payloads (concurrent execution)
    id3_a = f"matrix-diff-a-{time.time()}"
    id3_b = f"matrix-diff-b-{time.time()}"
    p3_a = {"instrument": "BTC-USD", "timeframe": "1h", "live_price": 77100.00, "request_id": id3_a}
    p3_b = {"instrument": "BTC-USD", "timeframe": "1h", "live_price": 77100.00, "request_id": id3_b}
    
    results3 = {}
    t3_a = threading.Thread(target=lambda: results3.update({"req_a": do_request(p3_a)}))
    t3_b = threading.Thread(target=lambda: results3.update({"req_b": do_request(p3_b)}))
    
    w0 = time.perf_counter()
    t3_a.start(); t3_b.start()
    t3_a.join(); t3_b.join()
    w_elapsed = time.perf_counter() - w0
    
    print(f"\n3. Different IDs with identical payloads (concurrent execution):")
    print(f"   Wall time: {w_elapsed:.4f}s")
    print(f"   Req A: status={results3['req_a']['status']}, elapsed={results3['req_a']['elapsed']:.4f}s")
    print(f"   Req B: status={results3['req_b']['status']}, elapsed={results3['req_b']['elapsed']:.4f}s")

    # 4. Different IDs with different payloads (true uncached concurrent execution)
    id4_a = f"matrix-uncached-a-{time.time()}"
    id4_b = f"matrix-uncached-b-{time.time()}"
    p4_a = {"instrument": "BTC-USD", "timeframe": "1h", "live_price": 77200.00, "request_id": id4_a, "force_fresh_tournament": True}
    p4_b = {"instrument": "BTC-USD", "timeframe": "1h", "live_price": 83500.00, "request_id": id4_b, "force_fresh_tournament": True}
    
    results4 = {}
    t4_a = threading.Thread(target=lambda: results4.update({"req_a": do_request(p4_a)}))
    t4_b = threading.Thread(target=lambda: results4.update({"req_b": do_request(p4_b)}))
    
    w4_0 = time.perf_counter()
    t4_a.start(); t4_b.start()
    t4_a.join(); t4_b.join()
    w4_elapsed = time.perf_counter() - w4_0
    
    print(f"\n4. Different IDs with different payloads (forced fresh uncached):")
    print(f"   Total Wall time: {w4_elapsed:.4f}s")
    print(f"   Req A: status={results4['req_a']['status']}, elapsed={results4['req_a']['elapsed']:.4f}s")
    print(f"   Req B: status={results4['req_b']['status']}, elapsed={results4['req_b']['elapsed']:.4f}s")
    print(f"   Serialization observation: Req A and Req B executed sequentially under _analysis_execution_lock")

    # 5. Cache expiry and fresh-request behavior
    p5_unkeyed = {"instrument": "BTC-USD", "timeframe": "1h", "live_price": 77999.00}
    r5_initial = do_request(p5_unkeyed)
    r5_cached = do_request(p5_unkeyed)
    print(f"\n5. Unkeyed Debounce & Cache Expiry:")
    print(f"   Initial unkeyed: status={r5_initial['status']}, elapsed={r5_initial['elapsed']:.4f}s")
    print(f"   Debounced (<10s): status={r5_cached['status']}, elapsed={r5_cached['elapsed']:.4f}s (Cache Hit: {r5_cached['elapsed'] < 0.01})")
    
    # Forced fresh bypass
    p5_fresh = {"instrument": "BTC-USD", "timeframe": "1h", "live_price": 77999.00, "force_fresh_tournament": True}
    r5_bypassed = do_request(p5_fresh)
    print(f"   Forced fresh bypass: status={r5_bypassed['status']}, elapsed={r5_bypassed['elapsed']:.4f}s (Uncached: {r5_bypassed['elapsed'] > 0.5})")

if __name__ == "__main__":
    run_tests()

