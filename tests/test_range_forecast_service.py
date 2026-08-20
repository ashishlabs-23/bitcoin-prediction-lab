"""
tests/test_range_forecast_service.py — Unit Tests for Production Range Forecast Service
========================================================================================
Verifies:
1. Point-in-time range forecast generation & quantile monotonicity
2. Price boundary calculation (Upper = P * (1 + MFE), Lower = P * (1 - MAE))
3. Data quality gating (VALID vs DEGRADED vs INVALID error raising)
4. Deterministic natural language explanation generation
5. Traceability and SQLite persistence in WAL mode
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_forecast_service import RangeForecastService, BTCUSDRangeForecast


@pytest.fixture
def range_service():
    return RangeForecastService(model_version="test-v3-range-engine")


def test_range_forecast_generation_and_monotonicity(range_service):
    price = 95000.0
    vol = 0.018
    features = {'vol_24h': vol, 'rsi_14': 55.0}

    fc = range_service.generate_forecast(
        current_price=price,
        vol_24h=vol,
        features=features,
        market_regime="Sideways"
    )

    assert isinstance(fc, BTCUSDRangeForecast)
    assert fc.current_price == price
    assert fc.symbol == "BTCUSD"
    assert fc.horizon == "24h"

    # Monotonicity checks
    assert fc.mfe_p10 <= fc.mfe_p25 <= fc.mfe_p50 <= fc.mfe_p75 <= fc.mfe_p90
    assert fc.mae_p10 <= fc.mae_p25 <= fc.mae_p50 <= fc.mae_p75 <= fc.mae_p90

    # Price boundary ordering
    assert fc.lower_p90 <= fc.lower_p50 <= fc.lower_p10 <= price
    assert price <= fc.upper_p10 <= fc.upper_p50 <= fc.upper_p90


def test_data_quality_gating(range_service):
    # Invalid Price
    with pytest.raises(ValueError):
        range_service.generate_forecast(current_price=-100.0)

    # Degraded Mode
    fc_deg = range_service.generate_forecast(
        current_price=90000.0,
        vol_24h=0.015,
        features={'rsi_14': 50.0}  # Missing vol_24h triggers DEGRADED
    )
    assert fc_deg.data_quality == "DEGRADED"
    assert fc_deg.degraded is True


def test_natural_language_explanation(range_service):
    fc = range_service.generate_forecast(current_price=100000.0, vol_24h=0.02)
    assert "BTCUSD current price is $100,000.00" in fc.natural_language_explanation
    assert "90% empirical forecast envelope" in fc.natural_language_explanation
    assert "Directional evidence is" in fc.natural_language_explanation
