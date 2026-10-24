"""
tests/test_modern_research_validation.py — Modern Econometric & Research Validation Tests
========================================================================================
Tests Bailey & López de Prado (2014) Deflated Sharpe Ratio, Finite-Horizon Monte Carlo Null,
Brier Skill Score diagnostics, Purged Sample Size, and Regional Fee Models.
"""

import pytest
import numpy as np

from engine.modern_research_validation import (
    DeflatedSharpeRatio,
    FiniteHorizonMonteCarloNull,
    ProbabilisticCalibrationDiagnostics,
    PurgedEffectiveSampleSize,
)
from engine.execution_cost_model import ExecutionCostModel


def test_deflated_sharpe_ratio_penalizes_multiple_trials():
    # Single trial with SR=1.2 is statistically significant
    single_trial = DeflatedSharpeRatio.calculate_dsr(
        observed_sharpe=1.2,
        n_observations=250,
        n_trials=1,
        var_trials_sharpe=0.25
    )
    assert single_trial["is_significant_95pct"] is True
    assert single_trial["data_snooping_hurdle_sr"] == 0.0

    # With 100 trials, the hurdle SR* increases significantly
    multi_trials = DeflatedSharpeRatio.calculate_dsr(
        observed_sharpe=1.2,
        n_observations=250,
        n_trials=100,
        var_trials_sharpe=0.25
    )
    assert multi_trials["data_snooping_hurdle_sr"] > 1.0
    # A marginal SR of 0.8 with 100 trials will fail DSR
    failing_trial = DeflatedSharpeRatio.calculate_dsr(
        observed_sharpe=0.8,
        n_observations=250,
        n_trials=100,
        var_trials_sharpe=0.25
    )
    assert failing_trial["is_significant_95pct"] is False
    assert failing_trial["verdict"] == "FAIL_DATA_SNOOPING_OVERFIT_RISK"


def test_finite_horizon_monte_carlo_null_identifies_timeout_penalty():
    # Generate 100 synthetic random-walk candles
    rng = np.random.default_rng(42)
    rets = rng.normal(0.0001, 0.005, 120)
    prices = 60000.0 * np.exp(np.cumsum(rets))
    highs = prices * (1.0 + np.abs(rng.normal(0, 0.002, 120)))
    lows = prices * (1.0 - np.abs(rng.normal(0, 0.002, 120)))

    mc_null = FiniteHorizonMonteCarloNull.simulate_random_entry_baseline(
        closes=prices,
        highs=highs,
        lows=lows,
        horizon_bars=24,
        k_tp=1.5,
        k_sl=1.0,
        n_simulations=100,
        random_seed=42
    )

    assert "empirical_null_hit_rate" in mc_null
    assert "empirical_timeout_rate" in mc_null
    assert mc_null["theoretical_infinite_horizon_null"] == round(1.0 / 2.5, 4)  # 0.40
    # Because of timeouts, the finite-horizon win rate must be bounded
    assert 0.0 <= mc_null["empirical_null_hit_rate"] <= 1.0


def test_brier_skill_score_diagnostics():
    # Perfect probabilities should yield high BSS
    probs = [0.9, 0.8, 0.1, 0.2]
    outcomes = [1, 1, 0, 0]
    result = ProbabilisticCalibrationDiagnostics.evaluate_calibration(probs, outcomes)
    assert result["brier_skill_score"] > 0.0
    assert result["has_predictive_skill"] is True
    assert result["calibration_quality"] in {"SUPERIOR_SKILL", "MARGINAL_SKILL"}

    # Inverted probabilities should yield negative BSS
    bad_probs = [0.1, 0.2, 0.9, 0.8]
    bad_result = ProbabilisticCalibrationDiagnostics.evaluate_calibration(bad_probs, outcomes)
    assert bad_result["brier_skill_score"] < 0.0
    assert bad_result["has_predictive_skill"] is False
    assert bad_result["calibration_quality"] == "NO_SKILL_WORSE_THAN_BASE_RATE"


def test_purged_effective_sample_size():
    eff = PurgedEffectiveSampleSize.calculate_effective_sample_size(
        total_bars=240,
        label_horizon_bars=24
    )
    assert eff["effective_independent_samples_n_eff"] == 10
    assert eff["variance_underestimation_factor"] == round(np.sqrt(24), 2)


def test_regional_cost_schedule_and_breakeven_calculation():
    # US Retail (187 bps)
    us_model = ExecutionCostModel(venue="COINBASE_US_RETAIL_187BPS")
    cfg_us = us_model.get_config()
    assert cfg_us["taker_bps_per_side"] == 90.0
    assert cfg_us["maker_bps_per_side"] == 50.0

    # India Retail (27 bps)
    in_model = ExecutionCostModel(venue="COINBASE_INDIA_INTL_27BPS")
    cfg_in = in_model.get_config()
    assert cfg_in["taker_bps_per_side"] == 10.0
    assert cfg_in["maker_bps_per_side"] == 9.0

    # Break-even win rate calculation:
    # At 0 friction, 1.5:1 reward:risk gives 1 / (1.5 + 1) = 40% break-even
    be_zero = ExecutionCostModel.calculate_breakeven_win_rate(friction_r=0.0, k_tp=1.5, k_sl=1.0)
    assert be_zero == 0.40

    # With friction_r = 0.5R, break-even is 1.5 / 2.5 = 60%
    be_costly = ExecutionCostModel.calculate_breakeven_win_rate(friction_r=0.5, k_tp=1.5, k_sl=1.0)
    assert be_costly == 0.60

    # Legacy discrepancy reconciliation
    reconciliation = ExecutionCostModel.reconcile_legacy_discrepancy(
        price=81242.50,
        sigma_t0=0.00837,
        k_sl=1.0
    )
    assert reconciliation["legacy_91bps_friction_r"] == 1.0877
    assert reconciliation["advanced_87bps_friction_r"] == 1.0394
    assert reconciliation["india_27bps_friction_r"] == 0.3226
    assert reconciliation["us_187bps_friction_r"] == 2.2342
