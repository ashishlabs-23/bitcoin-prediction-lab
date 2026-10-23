"""
scripts/benchmark_v17_endpoints.py — Reproducible Endpoint Latency Benchmark
=============================================================================
Measures Median, P95, P99, and Max latency across N>=100 requests per route
under controlled warmup and local workstation conditions.
"""

import os
import sys
import time
import json
import statistics
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from api.server import app


def run_endpoint_benchmark(n_requests: int = 100, n_warmup: int = 10):
    client = TestClient(app)
    endpoints = [
        ("Liveness (/health)", "/health"),
        ("Readiness (/api/readiness)", "/api/readiness"),
        ("Tournament Leaderboard (/api/tournament/latest)", "/api/tournament/latest?cost_scenario=COINBASE_RETAIL_87BPS"),
        ("Regime Invariants (/api/tournament/regime)", "/api/tournament/regime"),
        ("Setup Evaluation (/api/tournament/setup)", "/api/tournament/setup/SHORT_HORIZON_MEAN_REVERSION?cost_scenario=COINBASE_RETAIL_87BPS"),
    ]

    print("=" * 80)
    print("BTCognitive V17 Endpoint Latency & Responsiveness Benchmark")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Sample Count: N={n_requests} (Warmup: {n_warmup} requests per endpoint)")
    print(f"Environment: Python {sys.version.split()[0]} on Windows x86_64")
    print("=" * 80)

    results = {}

    for label, path in endpoints:
        # Warmup requests
        for _ in range(n_warmup):
            r = client.get(path)
            assert r.status_code == 200, f"Warmup failed on {path} with status {r.status_code}"

        latencies_ms = []
        errors = 0

        for _ in range(n_requests):
            t0 = time.perf_counter()
            resp = client.get(path)
            dt = (time.perf_counter() - t0) * 1000.0  # ms
            if resp.status_code != 200:
                errors += 1
            latencies_ms.append(dt)

        latencies_ms.sort()
        median_ms = statistics.median(latencies_ms)
        p95_idx = int(0.95 * len(latencies_ms))
        p99_idx = int(0.99 * len(latencies_ms))
        p95_ms = latencies_ms[p95_idx]
        p99_ms = latencies_ms[p99_idx]
        min_ms = latencies_ms[0]
        max_ms = latencies_ms[-1]

        results[label] = {
            "path": path,
            "samples": n_requests,
            "errors": errors,
            "min_ms": round(min_ms, 2),
            "median_ms": round(median_ms, 2),
            "p95_ms": round(p95_ms, 2),
            "p99_ms": round(p99_ms, 2),
            "max_ms": round(max_ms, 2),
        }

        print(f"\nEndpoint: {label}")
        print(f"  Path:       {path}")
        print(f"  Min:        {min_ms:6.2f} ms")
        print(f"  Median:     {median_ms:6.2f} ms")
        print(f"  P95:        {p95_ms:6.2f} ms")
        print(f"  P99:        {p99_ms:6.2f} ms")
        print(f"  Max:        {max_ms:6.2f} ms")
        print(f"  Errors:     {errors} / {n_requests}")

    print("\n" + "=" * 80)
    print("Benchmark Complete. Writing results to experiments/results/v17_latency_benchmark.json")
    os.makedirs(os.path.join("experiments", "results"), exist_ok=True)
    out_path = os.path.join("experiments", "results", "v17_latency_benchmark.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved: {out_path}")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_endpoint_benchmark(n_requests=100, n_warmup=10)
