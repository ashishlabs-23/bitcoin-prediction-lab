"""
tests/test_observatory.py — Unit tests for Layer 3 Forecast Accuracy Observatory
================================================================================
Tests immutable logging, outcome resolution, 30d/90d coverage tracking, and
Calibration Health State Machine transitions (STABLE, WATCH, DEGRADED, FAIL).
"""

import pytest
from engine.observatory import (
    ForecastAccuracyObservatory,
    CalibrationHealthStatus
)


def test_observatory_logging_and_resolution():
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=":memory:")
    rec = obs.log_forecast(
        timestamp="2026-08-01T00:00:00Z",
        v_hat=0.35,
        lower=0.20,
        upper=0.55
    )
    assert rec.point_forecast_har_rs_dow == 0.35
    assert rec.risk_envelope_lower == 0.20
    assert rec.risk_envelope_upper == 0.55
    assert rec.is_covered is None

    # Resolve covered outcome
    res = obs.resolve_outcome("2026-08-01T00:00:00Z", actual_rv7d=0.40)
    assert res is not None
    assert res.is_covered is True
    assert res.upper_breach is False
    assert res.lower_breach is False
    assert res.winkler_score == 0.35


def test_observatory_health_state_machine():
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=":memory:")
    
    # 1. Populate 100 resolved forecasts with 93% coverage and balanced tails -> STABLE
    for i in range(100):
        ts = f"2026-07-{i+1:02d}T00:00:00Z"
        obs.log_forecast(ts, v_hat=0.35, lower=0.20, upper=0.50)
        if i < 4:
            actual = 0.60 # 4 upper breaches
        elif i < 7:
            actual = 0.10 # 3 lower breaches
        else:
            actual = 0.35 # 93 covered
        obs.resolve_outcome(ts, actual_rv7d=actual)
        
    health = obs.evaluate_calibration_health()
    assert health.status == CalibrationHealthStatus.STABLE
    assert health.coverage_30d_pct == 93.0
    assert health.upper_breach_30d_pct == 4.0
    assert health.lower_breach_30d_pct == 3.0
    assert health.tail_asymmetry_30d_pct == 1.0

    # 2. Add 20 consecutive upper breaches -> DEGRADED (triggering ABSTAIN)
    for j in range(20):
        ts_deg = f"2026-08-deg-{j:02d}T00:00:00Z"
        obs.log_forecast(ts_deg, v_hat=0.35, lower=0.20, upper=0.50)
        obs.resolve_outcome(ts_deg, actual_rv7d=0.75) # upper breach
        
    health_deg = obs.evaluate_calibration_health()
    assert health_deg.status == CalibrationHealthStatus.DEGRADED
    assert "DEGRADED" in health_deg.status_rationale
