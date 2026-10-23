"""
tests/test_canonical_metric_contracts.py — Hand-Computed Fixture Verification for Canonical Metrics
===================================================================================================
Workstream B: Canonical Forecast and Metric Contracts.

Scientific References:
- Gneiting & Raftery (2007), JASA: Strictly Proper Scoring Rules.
- Xu & Xie (2021), ICML: Conformal Prediction Intervals.
- Fréchet (1935): Bounds on joint probability of two events.

Verifies:
1. Hand-calculated exact numerical outputs for every canonical metric.
2. Distinctness of marginal excursion coverage (P90) vs joint path containment.
3. Fréchet intersection bounds: P(A ∩ B) ∈ [P(A) + P(B) - 1, min(P(A), P(B))].
   For P(A)=0.90, P(B)=0.90: [0.80, 0.90], with 0.81 under independence.
4. Winkler score exact penalty weighting (2/alpha = 20.0 for alpha=0.10).
5. baseline_delta_bps is strictly None (unavailable) without point-in-time benchmark ledger.
"""

import pytest
import numpy as np
import pandas as pd

from engine.metric_contracts import (
    CANONICAL_METRIC_CATALOG,
    compute_mfe_error_pct,
    compute_mae_error_pct,
    compute_upper_coverage_pct,
    compute_lower_coverage_pct,
    compute_joint_path_containment_pct,
    compute_conformal_interval_width_pct,
    compute_winkler_score,
    evaluate_canonical_metrics
)


def test_hand_computed_mfe_mae_error():
    """
    Hand calculation:
    actual_mfe = [0.030, 0.015, 0.040, 0.020]
    exp_mfe    = [0.025, 0.020, 0.030, 0.020]
    errors     = [|0.030-0.025|=0.005, |0.015-0.020|=0.005, |0.040-0.030|=0.010, |0.020-0.020|=0.000]
    mean error = (0.005 + 0.005 + 0.010 + 0.000) / 4 = 0.020 / 4 = 0.005
    in percent = 0.005 * 100 = 0.5000%
    """
    act_mfe = np.array([0.030, 0.015, 0.040, 0.020])
    exp_mfe = np.array([0.025, 0.020, 0.030, 0.020])

    mfe_err = compute_mfe_error_pct(act_mfe, exp_mfe)
    assert mfe_err == pytest.approx(0.5000, abs=1e-5)

    act_mae = np.array([0.010, 0.025, 0.015, 0.030])
    exp_mae = np.array([0.012, 0.020, 0.015, 0.025])
    # |0.010-0.012|=0.002, |0.025-0.020|=0.005, 0.000, 0.005 -> sum=0.012 -> mean=0.003 -> 0.3000%
    mae_err = compute_mae_error_pct(act_mae, exp_mae)
    assert mae_err == pytest.approx(0.3000, abs=1e-5)


def test_hand_computed_marginal_vs_joint_path_containment():
    """
    Verifies that marginal coverage does NOT equal joint containment:
    10 observations:
    Obs 1: High breached (act_high > upper_p90), Low contained (act_low >= lower_p90) -> Upper: False, Lower: True, Joint: False
    Obs 2: High contained, Low breached (act_low < lower_p90) -> Upper: True, Lower: False, Joint: False
    Obs 3-10 (8 obs): Both contained -> Upper: True, Lower: True, Joint: True

    Upper coverage = 9 / 10 = 90.0%
    Lower coverage = 9 / 10 = 90.0%
    Joint containment = 8 / 10 = 80.0% (Fréchet lower bound!)
    """
    act_high = np.array([105.0, 95.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0, 92.0, 91.0])
    upper_p90 = np.array([100.0] * 10)  # Obs 0 breaches upper (105 > 100)

    act_low = np.array([90.0, 75.0, 85.0, 86.0, 87.0, 88.0, 89.0, 90.0, 85.0, 86.0])
    lower_p90 = np.array([80.0] * 10)   # Obs 1 breaches lower (75 < 80)

    upper_cov = compute_upper_coverage_pct(act_high, upper_p90)
    lower_cov = compute_lower_coverage_pct(act_low, lower_p90)
    joint_cont = compute_joint_path_containment_pct(act_high, act_low, upper_p90, lower_p90)

    assert upper_cov == 90.0
    assert lower_cov == 90.0
    assert joint_cont == 80.0  # Exactly 80%, proving joint containment is NOT 90%!


def test_frechet_bounds_mathematical_property():
    """
    Verifies Fréchet inequality:
    For events A, B with P(A)=0.90, P(B)=0.90:
    max(0, P(A) + P(B) - 1) <= P(A ∩ B) <= min(P(A), P(B))
    0.80 <= P(A ∩ B) <= 0.90.
    """
    p_a = 0.90
    p_b = 0.90
    frechet_lower = max(0.0, p_a + p_b - 1.0)
    frechet_upper = min(p_a, p_b)
    p_indep = p_a * p_b

    assert frechet_lower == pytest.approx(0.80, abs=1e-5)
    assert frechet_upper == pytest.approx(0.90, abs=1e-5)
    assert p_indep == pytest.approx(0.81, abs=1e-5)


def test_hand_computed_winkler_score():
    """
    Hand calculation of strictly proper Winkler interval score (alpha=0.10, penalty multiplier 2/alpha = 20.0):
    Obs 1: Price=100.0, [Lower=95.0, Upper=105.0] -> Width=(105-95)/100 = 0.10 (10.0%)
           High=102.0, Low=97.0 -> Contained! Exceedances = 0. Score = 0.10 * 100 = 10.0
    Obs 2: Price=100.0, [Lower=95.0, Upper=105.0] -> Width=0.10
           High=108.0 (Upper exceedance: (108-105)/100 = 0.03), Low=96.0 (Contained)
           Penalty = 20.0 * 0.03 = 0.60
           Score = (0.10 + 0.60) * 100 = 70.0
    Obs 3: Price=100.0, [Lower=95.0, Upper=105.0] -> Width=0.10
           High=104.0 (Contained), Low=92.0 (Lower exceedance: (95-92)/100 = 0.03)
           Penalty = 20.0 * 0.03 = 0.60
           Score = (0.10 + 0.60) * 100 = 70.0
    Mean score = (10.0 + 70.0 + 70.0) / 3 = 150.0 / 3 = 50.0000
    """
    curr_p = np.array([100.0, 100.0, 100.0])
    u_p90 = np.array([105.0, 105.0, 105.0])
    l_p90 = np.array([95.0, 95.0, 95.0])
    act_h = np.array([102.0, 108.0, 104.0])
    act_l = np.array([97.0, 96.0, 92.0])

    winkler = compute_winkler_score(act_h, act_l, u_p90, l_p90, curr_p, alpha=0.10)
    assert winkler == pytest.approx(50.0000, abs=1e-4)


def test_hand_computed_conformal_interval_width():
    """
    Hand calculation:
    Prices: [50000.0, 60000.0]
    Upper:  [53000.0, 63000.0]
    Lower:  [47000.0, 57000.0]
    Width 1: (53000 - 47000) / 50000 = 6000 / 50000 = 0.12 (12.0%)
    Width 2: (63000 - 57000) / 60000 = 6000 / 60000 = 0.10 (10.0%)
    Mean width: (12.0 + 10.0) / 2 = 11.0%
    """
    curr_p = np.array([50000.0, 60000.0])
    u_p90 = np.array([53000.0, 63000.0])
    l_p90 = np.array([47000.0, 57000.0])

    width_pct = compute_conformal_interval_width_pct(u_p90, l_p90, curr_p)
    assert width_pct == pytest.approx(11.00, abs=1e-5)


def test_canonical_metric_suite_evaluates_correctly():
    """Verifies that evaluate_canonical_metrics returns all canonical keys and sets baseline_delta_bps to None."""
    df = pd.DataFrame({
        "current_price": [100.0] * 5,
        "actual_high": [102.0, 101.0, 103.0, 102.5, 101.5],
        "actual_low": [98.0, 99.0, 97.0, 98.5, 98.0],
        "upper_p90": [105.0] * 5,
        "lower_p90": [95.0] * 5,
        "actual_mfe": [0.02, 0.01, 0.03, 0.025, 0.015],
        "actual_mae": [0.02, 0.01, 0.03, 0.015, 0.02],
        "exp_mfe": [0.02] * 5,
        "exp_mae": [0.02] * 5,
        "data_quality": ["VALID"] * 5,
        "degraded": [0] * 5
    })

    res = evaluate_canonical_metrics(df, min_observations=5)

    assert res["evaluation_status"] == "EVALUATED"
    assert res["sample_size"] == 5
    assert res["upper_coverage_pct"] == 100.0
    assert res["lower_coverage_pct"] == 100.0
    assert res["joint_path_containment_pct"] == 100.0
    assert res["conformal_interval_width_pct"] == 10.0
    assert res["winkler_score"] == pytest.approx(10.0, abs=1e-4)

    # Invariant: baseline_delta_bps MUST be None
    assert res["baseline_delta_bps"] is None
    assert res["baseline_status"] == "UNAVAILABLE"
