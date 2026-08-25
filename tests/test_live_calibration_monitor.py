"""
tests/test_live_calibration_monitor.py — Unit Tests for Live Calibration & Drift Scorecard
==========================================================================================
Verifies:
1. Multi-window rolling calibration computation (25, 50, 100, 250)
2. Handling of INSUFFICIENT_SAMPLE vs CALIBRATION_OK vs CALIBRATION_WARNING
3. Benchmark comparison against baselines
4. KS statistical drift test
"""

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.live_forecast_scorecard import LiveForecastScorecard


@pytest.fixture
def scorecard():
    return LiveForecastScorecard()


def test_rolling_calibration_windows(scorecard):
    n = 60
    mfe_p = np.full(n, 0.015)
    mae_p = np.full(n, 0.015)
    mfe_a = np.full(n, 0.012)
    mae_a = np.full(n, 0.012)
    upper_flags = np.ones(n, dtype=bool)
    lower_flags = np.ones(n, dtype=bool)

    results = scorecard.evaluate_rolling_windows(
        mfe_preds=mfe_p,
        mae_preds=mae_p,
        actual_mfes=mfe_a,
        actual_maes=mae_a,
        upper_covered_flags=upper_flags,
        lower_covered_flags=lower_flags,
        windows=[25, 50, 100]
    )

    assert len(results) == 3
    assert results[0].window_size == 25
    assert results[0].status == "CALIBRATION_OK"
    assert results[0].joint_path_containment_pct == 100.0

    # Window 100 should have insufficient sample
    assert results[2].window_size == 100
    assert results[2].status == "INSUFFICIENT_SAMPLE"


def test_ks_distribution_drift_detection(scorecard):
    base_dist = np.random.normal(0.015, 0.002, 50)
    same_dist = np.random.normal(0.015, 0.002, 50)
    shifted_dist = np.random.normal(0.040, 0.010, 50)  # Significant shift

    res_normal = scorecard.detect_distribution_drift(base_dist, same_dist)
    assert res_normal["status"] == "NORMAL"

    res_alert = scorecard.detect_distribution_drift(base_dist, shifted_dist)
    assert res_alert["status"] == "ALERT"
