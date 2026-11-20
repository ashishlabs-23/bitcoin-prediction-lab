import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import json
import threading
import pandas as pd
from api.routes_tournament import _post_analyse_market, AnalyseRequestModel
from engine.regime_strategy_tournament import _closed_candle_window_hash

def run_verification():
    print("=== BTCognitive V33.4C Phase 1 Verification ===")
    
    # 1. First Execution (Cold Run)
    req1 = AnalyseRequestModel(live_price=76985.40, auto_tournament=True)
    t0 = time.perf_counter()
    res1 = _post_analyse_market(req1)
    t1 = time.perf_counter()
    cold_time = t1 - t0
    print(f"1. Cold Execution Time: {cold_time:.4f}s")
    
    expected_sha = "142f759ff02d50f7156c2f9d1d9b2d4bab7388c250c81ac9a9db458e43cf9248"
    actual_sha = res1.get("candle_watermark", {}).get("candle_window_sha256")
    print(f"   SHA-256 Match: {actual_sha == expected_sha} ({actual_sha})")
    assert actual_sha == expected_sha, f"SHA mismatch! Expected {expected_sha}, got {actual_sha}"
    
    # 2. Repeated Execution (Idempotent Cached Run)
    t0 = time.perf_counter()
    res2 = _post_analyse_market(req1)
    t1 = time.perf_counter()
    cached_time = t1 - t0
    print(f"2. Idempotent Repeat Time: {cached_time:.4f}s")
    assert cached_time < 0.1, f"Cached run took too long: {cached_time}s"
    assert res2.get("candle_watermark", {}).get("candle_window_sha256") == expected_sha
    
    # 3. Concurrent Threads Execution Test
    print("3. Testing Concurrent Execution Under Lock...")
    results = [None, None]
    timings = [0.0, 0.0]
    
    def worker(idx):
        start = time.perf_counter()
        results[idx] = _post_analyse_market(AnalyseRequestModel(live_price=76985.40, auto_tournament=True))
        timings[idx] = time.perf_counter() - start
        
    th1 = threading.Thread(target=worker, args=(0,))
    th2 = threading.Thread(target=worker, args=(1,))
    
    wall_start = time.perf_counter()
    th1.start()
    th2.start()
    th1.join()
    th2.join()
    wall_total = time.perf_counter() - wall_start
    
    print(f"   Concurrent Wall Total: {wall_total:.4f}s")
    print(f"   Thread 0 Latency: {timings[0]:.4f}s")
    print(f"   Thread 1 Latency: {timings[1]:.4f}s")
    assert wall_total < 5.0, f"Concurrent execution took too long: {wall_total}s"
    assert results[0]["candle_watermark"]["candle_window_sha256"] == expected_sha
    assert results[1]["candle_watermark"]["candle_window_sha256"] == expected_sha
    
    print("\nALL PHASE 1 VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_verification()
