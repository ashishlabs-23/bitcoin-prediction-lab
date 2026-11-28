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
    """Return the benchmark payload.

    Governance note (2026-11-28): this function used to return a hard-coded
    eight-row leaderboard with invented mfe/mae errors, coverage figures, Winkler
    scores and p-values for TimesFM / Moirai / Chronos, including a row stamped
    "VALIDATED_PRODUCTION" for a model that is OFFLINE_RESEARCH_ONLY. None of
    those numbers were ever produced by an executed benchmark, so they are
    removed (AGENTS.md §2.5). The payload stays in the same shape so consumers do
    not break; populate it from a real evaluation run when one exists.
    """
    return {
        "title": "BTCUSD FORECAST MODEL BENCHMARK",
        "benchmark_type": "OUT_OF_SAMPLE_RANGE_EXCURSION",
        "count": 0,
        "status": "UNAVAILABLE_NOT_EXECUTED",
        "authoritative": False,
        "leaderboard": [],
        "reason": (
            "No foundation-model benchmark has been executed on this repository's data. "
            "Previous rows were synthetic placeholders and have been removed."
        ),
    }

