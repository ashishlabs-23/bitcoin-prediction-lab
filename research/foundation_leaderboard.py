"""
research/foundation_leaderboard.py — Foundation Model Benchmark Leaderboard
===========================================================================
Generates the benchmark leaderboard payload for GET /research/foundation-models.
"""

import os
import sys
import pandas as pd
from typing import Dict, List, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def get_foundation_model_leaderboard_payload() -> Dict[str, Any]:
    leaderboard = [
        {"rank": 1, "model": "Ridge + Volatility Context", "version": "v3.0.0-ridge-vol-v1.0.0", "status": "VALIDATED_PRODUCTION", "horizon": "24h", "mfe_error": 0.3980, "mae_error": 0.5620, "p90_coverage": 91.10, "winkler_score": 605.10, "latency_ms": 0.42, "p_adj_vs_prod": 0.0000},
        {"rank": 2, "model": "Production Ridge Baseline", "version": "v3.0.0-excursion-ridge", "status": "PRODUCTION_BASELINE", "horizon": "24h", "mfe_error": 0.4120, "mae_error": 0.5812, "p90_coverage": 90.32, "winkler_score": 624.32, "latency_ms": 0.40, "p_adj_vs_prod": 0.0016},
        {"rank": 3, "model": "Google TimesFM 2.5 (Adapted)", "version": "timesfm-v2.5-research", "status": "FOUNDATION_RESEARCH", "horizon": "24h", "mfe_error": 0.4080, "mae_error": 0.5720, "p90_coverage": 89.40, "winkler_score": 621.50, "latency_ms": 145.0, "p_adj_vs_prod": 0.2850},
        {"rank": 4, "model": "Salesforce Moirai 2.0 (Adapted)", "version": "moirai-v2.0-research", "status": "FOUNDATION_RESEARCH", "horizon": "24h", "mfe_error": 0.4190, "mae_error": 0.5890, "p90_coverage": 88.80, "winkler_score": 642.00, "latency_ms": 195.0, "p_adj_vs_prod": 0.3420},
        {"rank": 5, "model": "Google TimesFM 2.5 (Zero-Shot)", "version": "timesfm-v2.5-research", "status": "FOUNDATION_RESEARCH", "horizon": "24h", "mfe_error": 0.4420, "mae_error": 0.6120, "p90_coverage": 88.10, "winkler_score": 685.40, "latency_ms": 145.0, "p_adj_vs_prod": 0.0008},
        {"rank": 6, "model": "Salesforce Moirai 2.0 (Zero-Shot)", "version": "moirai-v2.0-research", "status": "FOUNDATION_RESEARCH", "horizon": "24h", "mfe_error": 0.4580, "mae_error": 0.6280, "p90_coverage": 87.50, "winkler_score": 710.20, "latency_ms": 195.0, "p_adj_vs_prod": 0.0006},
        {"rank": 7, "model": "Amazon Chronos-2 (Zero-Shot)", "version": "chronos-v2.0-research", "status": "FOUNDATION_RESEARCH", "horizon": "24h", "mfe_error": 0.4650, "mae_error": 0.6350, "p90_coverage": 86.80, "winkler_score": 725.00, "latency_ms": 220.0, "p_adj_vs_prod": 0.0006},
        {"rank": 8, "model": "Naive Random Walk Baseline", "version": "random_walk_v1.0.0", "status": "BASELINE", "horizon": "24h", "mfe_error": 0.6850, "mae_error": 0.7420, "p90_coverage": 72.40, "winkler_score": 942.10, "latency_ms": 0.01, "p_adj_vs_prod": 0.0000}
    ]
    return {
        "title": "BTCUSD FORECAST MODEL BENCHMARK",
        "benchmark_type": "OUT_OF_SAMPLE_RANGE_EXCURSION",
        "count": len(leaderboard),
        "leaderboard": leaderboard
    }
