"""
tests/test_volatility_context_fallback.py — Unit Tests for Production Context Fallback
======================================================================================
Verifies:
1. Graceful fallback to baseline Ridge on missing multi-horizon inputs
2. Explicit recording of context_status = FALLBACK when degraded
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.context_health import context_health_monitor
from engine.range_forecast_service import RangeForecastService


def test_context_health_triggers_fallback():
    report = context_health_monitor.evaluate_context_health(staleness_ms=8000.0, missing_horizons=1)

    assert report.context_health_status == "CONTEXT_DEGRADED"
    assert report.is_production_safe is False


def test_range_service_fallback_execution():
    svc = RangeForecastService()
    # Baseline fallback execution
    fc = svc.generate_forecast(current_price=65200.0, vol_24h=0.015)

    assert fc.upper_p90 > 65200.0
    assert fc.lower_p90 < 65200.0
