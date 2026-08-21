"""
tests/test_forecast_reliability.py — Unit Tests for Forecast Reliability Evaluator
==================================================================================
Verifies:
1. Deterministic calculation of reliability scores and tiers
2. Behavior across high-performing vs degraded telemetry inputs
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.forecast_reliability import forecast_reliability_service, ForecastReliabilityReport


def test_forecast_reliability_very_high():
    rep = forecast_reliability_service.evaluate_reliability(
        p90_coverage_pct=91.10,
        mfe_error_pct=0.3980,
        drift_psi=0.024,
        is_healthy=True,
        independent_blocks=31
    )

    assert isinstance(rep, ForecastReliabilityReport)
    assert rep.reliability_tier == "VERY_HIGH"
    assert rep.reliability_score >= 85.0


def test_forecast_reliability_insufficient_sample():
    rep = forecast_reliability_service.evaluate_reliability(
        p90_coverage_pct=91.10,
        mfe_error_pct=0.3980,
        drift_psi=0.024,
        is_healthy=True,
        independent_blocks=5
    )

    assert rep.reliability_tier != "VERY_HIGH"
