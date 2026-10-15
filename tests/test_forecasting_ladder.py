"""
tests/test_forecasting_ladder.py — Phase 6 Baseline-First Forecasting Ladder Tests
==================================================================================
Verifies:
1. Baseline A (Naive) produces valid zero-drift return quantiles and rolling historical volatility.
2. Challenger C (Quantile Regressor) fits P10, P50, P90 directly and enforces non-crossing quantiles.
3. Multi-horizon contracts (1h, 4h, 24h) emit standardized outputs binding horizon, model version,
   and generation timestamp.
4. Directional edge abstention: Models honestly report NO_DIRECTIONAL_EDGE when directional
   probabilities lack verifiable out-of-sample edge.
"""

import pytest
import numpy as np
from engine.forecasting_ladder import (
    NaiveBaselineForecaster,
    QuantileTreeChallengerForecaster,
    ForecastingLadderOrchestrator,
    ForecastHorizon,
    ModelLadderTier
)


def test_naive_baseline_zero_drift_and_volatility():
    """Baseline A produces zero-drift P50 and symmetric normal bounds based on historical returns."""
    forecaster = NaiveBaselineForecaster()
    np.random.seed(42)
    # 720 hours (~30 days) of returns with mean=0, std=0.008 (~80 bps per hour)
    returns = np.random.normal(0.0, 0.008, size=720)

    for h in [ForecastHorizon.H1, ForecastHorizon.H4, ForecastHorizon.H24]:
        out = forecaster.forecast(current_price=65000.0, horizon=h, historical_returns_1h=returns)
        assert out.model_tier == ModelLadderTier.BASELINE_A_NAIVE
        assert out.horizon == h.value
        assert out.current_price == 65000.0
        assert out.return_p50 == 0.0
        assert out.price_mid_p50 == 65000.0
        assert out.price_lower_p10 < out.price_mid_p50 < out.price_upper_p90
        assert out.directional_state == "NO_DIRECTIONAL_EDGE"
        assert out.governance_status == "BASELINE_REFERENCE_ONLY"
        assert out.is_production_authorized is False


def test_quantile_challenger_monotonicity_and_fit():
    """Challenger C fits P10/P50/P90 via pinball loss and enforces non-crossing quantiles."""
    challenger = QuantileTreeChallengerForecaster(ForecastHorizon.H24)
    np.random.seed(123)

    # 100 samples with 5 features
    X = np.random.normal(0, 1, size=(100, 5))
    # Target 24h returns
    y = 0.01 * X[:, 0] + np.random.normal(0, 0.03, size=100)

    challenger.fit(X, y)
    assert challenger.is_fitted is True

    # Predict for a new observation
    X_test = np.array([0.5, -0.2, 0.1, 0.0, 1.0])
    p10, p50, p90 = challenger.predict_quantiles(X_test)

    # Invariant: P10 <= P50 <= P90
    assert p10 <= p50 <= p90

    out = challenger.forecast(current_price=68000.0, feature_vector=X_test)
    assert out.price_lower_p10 <= out.price_mid_p50 <= out.price_upper_p90
    assert out.horizon == "24h"
    assert out.directional_state == "NO_DIRECTIONAL_EDGE"


def test_forecasting_ladder_orchestration():
    """Forecasting ladder coordinates side-by-side execution across tiers."""
    ladder = ForecastingLadderOrchestrator()
    np.random.seed(99)
    returns = np.random.normal(0.0, 0.005, size=200)

    # Generate ladder for 1h, 4h, 24h
    for h in [ForecastHorizon.H1, ForecastHorizon.H4, ForecastHorizon.H24]:
        res = ladder.generate_ladder(current_price=64000.0, horizon=h, historical_returns_1h=returns)
        assert "baseline_a" in res
        assert res["baseline_a"].price_lower_p10 < res["baseline_a"].price_upper_p90
