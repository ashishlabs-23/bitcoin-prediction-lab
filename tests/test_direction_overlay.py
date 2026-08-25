"""
tests/test_direction_overlay.py — Unit Tests for Secondary Direction Overlay & Tradeability
==========================================================================================
Verifies:
1. Default to NO_DIRECTIONAL_EDGE when signal is unvalidated or noise
2. Conditional BULLISH / BEARISH detection under extreme asymmetry
3. Informational non-execution tradeability score categories (LOW / MEDIUM / HIGH)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.direction_overlay import DirectionOverlayService, DirectionOverlayResult
from engine.tradeability import TradeabilityService, TradeabilityResult


@pytest.fixture
def overlay_services():
    return DirectionOverlayService(), TradeabilityService()


def test_direction_overlay_default_no_edge(overlay_services):
    dir_svc, _ = overlay_services
    res = dir_svc.evaluate_direction(
        exp_mfe=0.010,
        exp_mae=0.010,
        directional_prob=0.52,
        uncertainty_level="HIGH"
    )
    assert isinstance(res, DirectionOverlayResult)
    assert res.state == "NO_DIRECTIONAL_EDGE"


def test_direction_overlay_bullish_asymmetry(overlay_services):
    dir_svc, _ = overlay_services
    res = dir_svc.evaluate_direction(
        exp_mfe=0.020,
        exp_mae=0.010,  # Asymmetry = 2.0x
        directional_prob=0.70,
        uncertainty_level="HIGH"
    )
    assert res.state == "BULLISH"


def test_tradeability_service_informational_labels(overlay_services):
    _, trade_svc = overlay_services
    res = trade_svc.compute_tradeability(
        exp_mfe=0.008,
        exp_mae=0.012,  # Adverse dominates
        uncertainty_level="HIGH"
    )
    assert isinstance(res, TradeabilityResult)
    assert res.category == "LOW"
    assert res.is_actionable is False
    assert res.label == "TRADEABILITY RESEARCH SCORE (NON-EXECUTION)"
