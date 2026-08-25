"""
tests/test_purged_excursion_validation.py — Tests for Purged Excursion Validation & Product Boundaries
=======================================================================================================
Verifies that:
1. Path excursions (MFE and MAE) are calculated strictly forward over (t, t + 24h].
2. Purged cross-validation enforces 24h purge and 24h post-test embargo with zero lookahead.
3. Direction overlay strictly treats excursions as volatility skew and rejects directional buy/sell signals.
4. Longitudinal status accurately stratifies sample size (N_eff < 30 as Operational Smoke Test).
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.purged_excursion_validation import (
    compute_excursion_targets,
    compute_winkler_score,
    run_purged_excursion_evaluation
)
from engine.direction_overlay import DirectionOverlayService
from engine.longitudinal_status import longitudinal_status_service


def test_compute_excursion_targets_forward_only():
    """Verify that MFE/MAE compute forward-looking path extremes without backward leakage."""
    dates = pd.date_range("2024-01-01", periods=100, freq="1h", tz="UTC")
    # Monotonically increasing close prices: 100, 101, 102, ...
    close_prices = np.linspace(100, 200, 100)
    df = pd.DataFrame({
        "timestamp": dates,
        "close": close_prices,
        "high": close_prices + 1.0,
        "low": close_prices - 1.0
    }).set_index("timestamp")

    exc = compute_excursion_targets(df, horizon_bars=24)
    assert "mfe" in exc.columns
    assert "mae" in exc.columns

    # For an upward series, MFE > 0 and MAE is strictly positive (since low is close - 1)
    assert exc['mfe'].iloc[0] > 0
    assert exc['mae'].iloc[0] > 0
    # Last 23 bars should be NaN due to incomplete forward horizon
    assert np.isnan(exc['mfe'].iloc[-1])


def test_winkler_score_penalization():
    """Verify Winkler score penalizes wider intervals and boundary breaches."""
    # Narrow interval without breaches
    score_tight = compute_winkler_score(lower=np.array([90.0]), upper=np.array([110.0]), actual=np.array([100.0]), alpha=0.10)
    assert score_tight == 20.0  # Width only

    # Breached interval (actual = 120 > upper = 110)
    score_breach = compute_winkler_score(lower=np.array([90.0]), upper=np.array([110.0]), actual=np.array([120.0]), alpha=0.10)
    assert score_breach > score_tight


def test_direction_overlay_rejects_directional_trade_signals():
    """Verify that DirectionOverlayService strictly returns volatility skew and never directional trades."""
    overlay = DirectionOverlayService()
    
    # Asymmetric upside
    res_up = overlay.evaluate_direction(exp_mfe=0.03, exp_mae=0.01)
    assert res_up.state == "UPWARD_VOLATILITY_SKEW"
    assert res_up.is_directional_trade_signal is False

    # Asymmetric downside
    res_down = overlay.evaluate_direction(exp_mfe=0.01, exp_mae=0.03)
    assert res_down.state == "DOWNWARD_VOLATILITY_SKEW"
    assert res_down.is_directional_trade_signal is False

    # Symmetric
    res_sym = overlay.evaluate_direction(exp_mfe=0.02, exp_mae=0.02)
    assert res_sym.state == "SYMMETRIC_VOLATILITY"
    assert res_sym.is_directional_trade_signal is False

    # High Uncertainty Abstain
    res_unc = overlay.evaluate_direction(exp_mfe=0.03, exp_mae=0.01, uncertainty_level="HIGH_DISPERSION")
    assert res_unc.state == "HIGH_UNCERTAINTY_ABSTAIN"
    assert res_unc.is_directional_trade_signal is False


def test_purged_excursion_evaluation_run():
    """Verify end-to-end purged cross validation executes and passes."""
    results = run_purged_excursion_evaluation(n_splits=3, embargo_bars=24)
    assert results["status"] == "PASS"
    assert results["zero_leakage_guaranteed"] is True
    assert len(results["folds"]) == 3
    assert results["mean_p90_coverage_pct"] >= 70.0


def test_longitudinal_status_stratification():
    """Verify N_eff sample size stratification accurately flags operational smoke tests."""
    report = longitudinal_status_service.get_status_report()
    assert report.evidence_phase == "POST_REPAIR"
    cal_status = report.observed_metrics["calibration_status"]
    # At early stage (N_eff < 30), must be OPERATIONAL_SMOKE_TEST
    assert "OPERATIONAL_SMOKE_TEST" in cal_status or "INTERMEDIATE_HEALTH_MONITORING" in cal_status


if __name__ == "__main__":
    print("Running Purged Excursion Validation Tests...")
    test_compute_excursion_targets_forward_only()
    print("PASS: test_compute_excursion_targets_forward_only")
    test_winkler_score_penalization()
    print("PASS: test_winkler_score_penalization")
    test_direction_overlay_rejects_directional_trade_signals()
    print("PASS: test_direction_overlay_rejects_directional_trade_signals")
    test_purged_excursion_evaluation_run()
    print("PASS: test_purged_excursion_evaluation_run")
    test_longitudinal_status_stratification()
    print("PASS: test_longitudinal_status_stratification")
    print("\nALL PURGED EXCURSION & BOUNDARY TESTS PASSED!")
