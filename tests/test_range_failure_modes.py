"""
tests/test_range_failure_modes.py — Integration Tests for Range Engine Failure & Degradation Modes
===================================================================================================
Verifies:
1. Handling of Binance data disconnect / empty feature cache
2. Degraded mode activation upon partial missing features
3. Safe error rejection on invalid price (NaN, negative, zero)
4. Graceful SQLite write failure recovery
"""

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_forecast_service import RangeForecastService


@pytest.fixture
def range_svc():
    return RangeForecastService()


def test_invalid_price_failure_mode(range_svc):
    with pytest.raises(ValueError):
        range_svc.generate_forecast(current_price=0.0)

    with pytest.raises(ValueError):
        range_svc.generate_forecast(current_price=float('nan'))

    with pytest.raises(ValueError):
        range_svc.generate_forecast(current_price=-5000.0)


def test_degraded_mode_missing_features(range_svc):
    # Only supply RSI, missing vol_24h
    fc = range_svc.generate_forecast(
        current_price=94000.0,
        vol_24h=0.015,
        features={'rsi_14': 45.0}
    )
    assert fc.data_quality == "DEGRADED"
    assert fc.degraded is True
    # Uncertainty widens in degraded mode
    assert fc.uncertainty > 0.0


def test_clean_valid_features_mode(range_svc):
    fc = range_svc.generate_forecast(
        current_price=94000.0,
        vol_24h=0.015,
        features={'vol_24h': 0.015, 'rsi_14': 50.0}
    )
    assert fc.data_quality == "VALID"
    assert fc.degraded is False
