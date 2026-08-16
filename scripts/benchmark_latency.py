#!/usr/bin/env python3
"""
Benchmark Latency Tool
======================
Measures round-trip API and WebSocket latency across endpoints.
"""

import time
import urllib.request
import json


def benchmark_endpoint(url: str, n_trials: int = 10):
    latencies = []
    print(f"Benchmarking {url} ({n_trials} requests)...")
    for i in range(n_trials):
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BenchmarkTool/1.0"})
            with urllib.request.urlopen(req, timeout=5) as res:
                _ = res.read()
            dt = (time.perf_counter() - t0) * 1000.0
            latencies.append(dt)
        except Exception as e:
            print(f"  [Error] Request {i+1} failed: {e}")

    if latencies:
        avg_ms = sum(latencies) / len(latencies)
        min_ms = min(latencies)
        max_ms = max(latencies)
        p95_ms = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f"  -> Avg: {avg_ms:.2f}ms | Min: {min_ms:.2f}ms | Max: {max_ms:.2f}ms | P95: {p95_ms:.2f}ms\n")


if __name__ == "__main__":
    benchmark_endpoint("http://localhost:8000/health", 10)
    benchmark_endpoint("http://localhost:8000/prediction/latest", 10)
    benchmark_endpoint("http://localhost:8000/regime/latest", 10)
