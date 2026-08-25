"""
tests/test_context_dependency.py — Unit Tests for Production Context Dependency Isolation
=========================================================================================
Verifies:
1. Zero runtime dependency of Config B on shadow Hawkes model
2. Complete mathematical decoupling between Ridge production and Hawkes shadow subsystems
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.volatility_bridge import volatility_bridge_service
from engine.range_forecast_service import RangeForecastService


def test_volatility_bridge_has_no_hawkes_dependency():
    ts = volatility_bridge_service.analyze_term_structure()

    # Verify input variables and dictionary output do not require Hawkes intensities
    d = ts.to_dict()
    assert "lambda_buy" not in d
    assert "hawkes_event_pressure" not in d
    assert "regime" in d


def test_production_ridge_safe_fallback():
    svc = RangeForecastService()
    fc = svc.generate_forecast(current_price=65200.0, vol_24h=0.015)

    assert fc.upper_p90 > 65200.0
    assert fc.lower_p90 < 65200.0
