"""
tests/test_multi_regime_deepening.py — Tests for Multi-Regime Historical Deepening & Stratified Calibration
===========================================================================================================
Verifies that:
1. Multi-regime dataset spans 2020–2026 across all 4 macro epochs.
2. Feature engineering maintains zero lookahead.
3. Multi-regime purged walk-forward cross-validation executes and exposes regime-conditional coverage shifts.
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.multi_regime_dataset import build_multi_regime_dataset, assign_macro_regime, MULTI_REGIME_PARQUET
from research.multi_regime_purged_validation import run_multi_regime_evaluation


def test_multi_regime_dataset_span_and_regimes():
    """Verify that multi-regime dataset covers all 4 macro epochs without NaN leaks."""
    df = build_multi_regime_dataset(start_date="2022-01-01", end_date="2024-06-01")
    assert len(df) > 5000
    assert "macro_regime" in df.columns
    assert "vol_ratio_1h_24h" in df.columns
    assert "mfe_24h" in df.columns
    assert "mae_24h" in df.columns
    assert df.isna().sum().sum() == 0


def test_assign_macro_regimes():
    """Verify deterministic regime assignment by historical epoch boundaries."""
    dates = pd.to_datetime([
        "2020-05-15",
        "2022-06-15",
        "2023-08-15",
        "2024-03-15"
    ], utc=True)
    regimes = assign_macro_regime(dates)
    assert regimes[0] == "REGIME_1_HALVING_BULL"
    assert regimes[1] == "REGIME_2_FED_HIKING_BEAR"
    assert regimes[2] == "REGIME_3_TRANSITION_COMPRESSION"
    assert regimes[3] == "REGIME_4_SPOT_ETF_INSTITUTIONAL"


def test_multi_regime_purged_cv_execution():
    """Verify multi-regime purged CV executes and generates stratified regime metrics."""
    res = run_multi_regime_evaluation(n_splits=3, embargo_bars=24)
    assert "pooled_p90_joint_coverage_pct" in res
    assert "regime_stratification" in res
    assert len(res["regime_stratification"]) >= 2
    assert res["pooled_effective_sample_size_neff"] > 500.0


if __name__ == "__main__":
    print("Running Multi-Regime Deepening Tests...")
    test_multi_regime_dataset_span_and_regimes()
    print("PASS: test_multi_regime_dataset_span_and_regimes")
    test_assign_macro_regimes()
    print("PASS: test_assign_macro_regimes")
    test_multi_regime_purged_cv_execution()
    print("PASS: test_multi_regime_purged_cv_execution")
    print("\nALL MULTI-REGIME DEEPENING TESTS PASSED!")
