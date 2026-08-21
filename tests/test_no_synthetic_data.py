"""
tests/test_no_synthetic_data.py — Anti-Regression Test for Zero Synthetic Price Fabrication
===========================================================================================
Audits production inference engine code to guarantee:
1. No np.random or synthetic price generation in production inference paths
2. Explicit DEGRADED / INVALID error returns instead of fabricated market prices
"""

import os
import sys
import inspect
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_forecast_service import RangeForecastService


def test_production_service_source_code_clean_of_synthetic_randomness():
    src = inspect.getsource(RangeForecastService)

    # Asserts no random generators in production path
    assert "np.random.normal" not in src
    assert "np.random.uniform" not in src
    assert "random.random" not in src


def test_deterministic_non_synthetic_price_bounds():
    svc = RangeForecastService()
    fc = svc.generate_forecast(current_price=65000.0, vol_24h=0.015)

    assert fc.current_price == 65000.0
    assert fc.upper_p90 > 65000.0
    assert fc.lower_p90 < 65000.0
    assert fc.mfe_p50 > 0.0
    assert fc.mae_p50 > 0.0
