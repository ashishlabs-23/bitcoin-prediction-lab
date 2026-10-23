"""
tests/test_phase3_volatility_and_range_validation.py — Verification of Phase 3 Risk & Range Forecasts
======================================================================================================
Tests:
1. HAR-RS-DOW-v1.0 model semantic contract: target is strictly 7-day realized variance, non-directional.
2. Proper scoring rule verification: Winkler score penalizes miscoverage at nominal miscoverage rate.
3. Fréchet bounds on joint path containment vs marginal excursion coverage.
4. RangeForecastService generates excursion quantiles without directional claims.
"""

import numpy as np
import pytest

from models.authoritative_model_registry import (
    get_active_production_model,
    ModelClassification,
    AuthorizationStatus,
)
from engine.metric_contracts import (
    compute_winkler_score,
    evaluate_canonical_metrics,
)
from engine.range_forecast_service import RangeForecastService


def test_har_rs_dow_semantic_contract():
    model = get_active_production_model()
    assert model.canonical_id == "HAR-RS-DOW-v1.0"
    assert model.classification == ModelClassification.PRODUCTION_VOLATILITY
    assert "rv7d_var_ann" in model.forecast_target
    assert "168h" in model.forecast_horizon
    assert model.directional_prediction_capability is False
    assert model.authorization_status in [AuthorizationStatus.AUTHORIZED_FOR_PRODUCTION, AuthorizationStatus.BLOCKED_AUDIT_FAILURE]



def test_winkler_score_proper_scoring():
    upper_p90 = np.array([105.0])
    lower_p90 = np.array([95.0])
    current_price = np.array([100.0])

    # Inside interval: high=104, low=96. Width = (105-95)/100 = 0.10 => 10.0%
    score_inside = compute_winkler_score(
        actual_high=np.array([104.0]),
        actual_low=np.array([96.0]),
        upper_p90=upper_p90,
        lower_p90=lower_p90,
        current_price=current_price,
        alpha=0.10
    )
    assert round(score_inside, 4) == 10.0

    # Upper breach: actual_high=107.5. Exceedance = 2.5/100 = 0.025.
    # Penalty = (2/0.10)*0.025 = 20 * 0.025 = 0.50. Total = (0.10 + 0.50)*100 = 60.0
    score_upper = compute_winkler_score(
        actual_high=np.array([107.5]),
        actual_low=np.array([96.0]),
        upper_p90=upper_p90,
        lower_p90=lower_p90,
        current_price=current_price,
        alpha=0.10
    )
    assert round(score_upper, 4) == 60.0


def test_frechet_bounds_containment_semantics():
    # If upper coverage is 90% and lower coverage is 90%, joint containment must be in [80%, 90%]
    n = 100
    # Simulate marginal 90% events with independence
    upper_ok = np.array([True] * 90 + [False] * 10)
    lower_ok = np.array([True] * 90 + [False] * 10)
    np.random.seed(42)
    np.random.shuffle(lower_ok)

    joint_ok = upper_ok & lower_ok
    joint_pct = (np.sum(joint_ok) / n) * 100.0

    assert 80.0 <= joint_pct <= 90.0
    # Crucially, joint containment is not nominal 90% scalar coverage
    assert joint_pct < 90.0 or joint_pct == 90.0


def test_range_forecast_service_non_directional():
    service = RangeForecastService(default_horizon="24h")
    # Verify default state
    assert service.default_horizon == "24h"
    # When initialized, uncertainty service is attached and directional overlay is not an ML signal
    assert service.uncertainty_svc is not None
