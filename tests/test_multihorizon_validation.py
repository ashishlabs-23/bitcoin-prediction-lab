"""
tests/test_multihorizon_validation.py — Unit Tests for Multi-Horizon Benchmark Results
======================================================================================
Verifies:
1. Multi-horizon validation benchmark execution across 7 horizons
2. Final decision CASE A (Different horizons have different optimal models)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.multihorizon_validation import run_multihorizon_validation


def test_multihorizon_validation_benchmark():
    df_results, meta = run_multihorizon_validation()

    assert len(df_results) == 7
    assert meta["verdict"] == "CASE_A_DIFFERENT_HORIZONS_HAVE_DIFFERENT_OPTIMAL_MODELS"
    assert "5m (Hawkes)" in meta["best_short"]
    assert "24h (Ridge)" in meta["best_long"]
