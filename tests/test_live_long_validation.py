"""
tests/test_live_long_validation.py — Integration & Unit Tests for Long-Horizon Live Validation
==============================================================================================
Verifies:
1. Frozen validation lock manifest integrity
2. Non-overlapping 24h block partitioning and progression
3. Regime and volatility partition stability
4. Paired baseline challenge and bootstrap execution
5. Drift monitor execution
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.independent_block_metrics import run_independent_block_evaluation
from research.range_stability import run_range_stability_audit
from research.baseline_challenge import run_baseline_challenge_test
from research.forecast_drift import run_forecast_drift_audit
from research.live_long_validation import run_full_long_horizon_validation


def test_live_validation_lock_manifest():
    manifest_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results", "live_validation_lock.json"))
    assert os.path.exists(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["frozen_model_version"] == "v3.0.0-excursion-ridge-conformal"
    assert data["lock_status"] == "FROZEN_FOR_LONG_HORIZON_VALIDATION"


def test_independent_block_partitioning():
    df_blocks, df_prog, meta = run_independent_block_evaluation(min_blocks=10)
    assert meta["n_blocks"] >= 10
    assert len(df_blocks) >= 10
    assert "path_contained" in df_blocks.columns
    assert "range_width_pct" in df_blocks.columns


def test_range_stability_partitions():
    df_reg, df_vol, meta = run_range_stability_audit()
    assert len(df_reg) > 0
    assert len(df_vol) > 0
    assert "Stability Status" in df_reg.columns


def test_baseline_challenge_test():
    df_chall, meta = run_baseline_challenge_test(n_bootstrap=100)
    assert meta["n_blocks"] > 0
    assert "ci_lower" in meta and "ci_upper" in meta


def test_forecast_drift_monitor():
    df_drift, meta = run_forecast_drift_audit()
    assert len(df_drift) == 3
    assert meta["overall_status"] in ["NORMAL", "WATCH", "ALERT"]


def test_full_long_horizon_validation_orchestrator():
    manifest = run_full_long_horizon_validation()
    assert manifest["validation_phase"] == "LONG_HORIZON_LIVE_RANGE_VALIDATION"
    assert manifest["independent_blocks_count"] >= 30
    assert manifest["promotion_gate_status"] == "MAINTAIN_PRODUCTION_RIDGE_RANGE_ENGINE"
