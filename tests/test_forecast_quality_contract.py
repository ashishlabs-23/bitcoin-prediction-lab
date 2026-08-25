"""
tests/test_forecast_quality_contract.py — Tests for Forecast Quality & Eligibility
===================================================================================
Verifies that:
- Complete features produce ForecastQuality.VALID with validation_eligible = True.
- Incomplete secondary features produce ForecastQuality.DEGRADED with validation_eligible = False.
- Invalid price/volatility produces ForecastQuality.INVALID with validation_eligible = False.
"""

from models.forecast_quality_contract import (
    ForecastQuality,
    assess_forecast_quality,
    ForecastQualityRecord
)

def test_valid_forecast_quality():
    q = assess_forecast_quality(
        current_price=65000.0,
        vol_24h=0.015,
        features={"rsi_14": 50.0, "atr_14": 800.0, "ret_24h": 0.01},
        context_healthy=True
    )
    assert q.data_quality == ForecastQuality.VALID
    assert q.validation_eligible is True
    assert q.context_status == "CONTEXT_HEALTHY"
    assert q.degraded_reason is None

def test_degraded_forecast_quality_on_missing_features():
    q = assess_forecast_quality(
        current_price=65000.0,
        vol_24h=0.015,
        features={"rsi_14": 50.0},  # Missing atr_14 and ret_24h
        context_healthy=True
    )
    assert q.data_quality == ForecastQuality.DEGRADED
    assert q.validation_eligible is False
    assert "Missing secondary features" in q.degraded_reason

def test_invalid_forecast_quality_on_bad_pricing():
    q = assess_forecast_quality(
        current_price=0.0,
        vol_24h=0.015,
        features=None,
        context_healthy=True
    )
    assert q.data_quality == ForecastQuality.INVALID
    assert q.validation_eligible is False
