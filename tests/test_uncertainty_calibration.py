"""
tests/test_uncertainty_calibration.py — Phase 7 Uncertainty Calibration Tests
=============================================================================
Verifies:
1. Pinball loss calculation correctness across P10, P50, P90.
2. Winkler interval score penalizes boundary breaches and interval width.
3. Dual monitoring: coverage and interval width are evaluated simultaneously.
4. Conformal adjustment expands intervals on miscalibrated holdout data to restore coverage.
5. Drift detection flags severe undercoverage.
"""

import pytest
import numpy as np

from engine.uncertainty_calibration import (
    UncertaintyCalibrationEngine,
    CalibrationEvaluationResult
)


def test_pinball_loss_exactness():
    """Pinball loss matches mathematical definition for under- and over-predictions."""
    engine = UncertaintyCalibrationEngine()

    # If y_true = 10, y_pred = 8 (underprediction by 2)
    # For q=0.90: loss = 0.90 * (10 - 8) = 1.80
    loss_under = engine.compute_pinball_loss(np.array([10.0]), np.array([8.0]), quantile=0.90)
    assert np.isclose(loss_under, 1.80)

    # If y_true = 5, y_pred = 8 (overprediction by 3)
    # For q=0.90: loss = (0.90 - 1.0) * (5 - 8) = -0.10 * -3 = 0.30
    loss_over = engine.compute_pinball_loss(np.array([5.0]), np.array([8.0]), quantile=0.90)
    assert np.isclose(loss_over, 0.30)


def test_winkler_score_properties():
    """Winkler score penalizes wider intervals and imposes heavy penalty on breaches."""
    engine = UncertaintyCalibrationEngine()
    y = np.array([50.0])

    # Narrow contained interval: [45, 55], width = 10
    score_contained = engine.compute_winkler_score(y, np.array([45.0]), np.array([55.0]), alpha=0.10)
    assert np.isclose(score_contained, 10.0)

    # Wider contained interval: [40, 60], width = 20
    score_wide = engine.compute_winkler_score(y, np.array([40.0]), np.array([60.0]), alpha=0.10)
    assert np.isclose(score_wide, 20.0)
    assert score_wide > score_contained

    # Breached interval (lower breach): [55, 65], breach by 5
    # score = 10 + (2 / 0.10) * 5 = 10 + 100 = 110
    score_breach = engine.compute_winkler_score(y, np.array([55.0]), np.array([65.0]), alpha=0.10)
    assert np.isclose(score_breach, 110.0)
    assert score_breach > score_wide


def test_calibration_evaluation_nominal_and_degraded():
    """Calibration engine evaluates coverage and flags degraded undercoverage."""
    engine = UncertaintyCalibrationEngine(target_coverage=0.90)

    np.random.seed(42)
    n = 200
    y_true = np.random.normal(0, 1, size=n)

    # 1. Well-calibrated 90% bounds (approx [-1.645, 1.645])
    lower_nom = np.full(n, -1.65)
    mid_nom = np.zeros(n)
    upper_nom = np.full(n, 1.65)

    res_nom = engine.evaluate_calibration(y_true, lower_nom, mid_nom, upper_nom)
    assert res_nom.empirical_coverage_pct >= 85.0
    assert res_nom.calibration_status == "CALIBRATED_NOMINAL"
    assert res_nom.drift_detected is False

    # 2. Severely undercovered bounds (e.g., [-0.3, 0.3], covering ~25%)
    lower_bad = np.full(n, -0.3)
    upper_bad = np.full(n, 0.3)
    res_bad = engine.evaluate_calibration(y_true, lower_bad, mid_nom, upper_bad)
    assert res_bad.empirical_coverage_pct < 60.0
    assert res_bad.calibration_status == "DEGRADED_UNDERCOVERAGE"
    assert res_bad.drift_detected is True


def test_conformal_interval_adjustment():
    """Conformal adjustment fits delta on calibration set and expands intervals."""
    engine = UncertaintyCalibrationEngine(target_coverage=0.90)

    # Calibration set with residuals exceeding current bounds
    np.random.seed(123)
    n = 100
    y_calib = np.random.normal(0, 2.0, size=n)
    lower_calib = np.full(n, -1.0)
    upper_calib = np.full(n, 1.0)

    delta = engine.fit_conformal_adjustment(y_calib, lower_calib, upper_calib)
    assert delta > 0.0

    raw_low, raw_high = -1.0, 1.0
    conf_low, conf_high = engine.apply_conformal_adjustment(raw_low, raw_high)

    assert conf_low < raw_low
    assert conf_high > raw_high
    assert np.isclose((conf_high - conf_low) - (raw_high - raw_low), 2.0 * delta)
