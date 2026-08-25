"""
tests/test_context_health.py — Unit Tests for Volatility Context Health Monitor
================================================================================
Verifies:
1. Operational health states of volatility context calculations
2. Failure handling on high staleness or missing horizons
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.context_health import context_health_monitor, ContextHealthReport


def test_context_health_normal():
    rep = context_health_monitor.evaluate_context_health(staleness_ms=100.0, missing_horizons=0)

    assert isinstance(rep, ContextHealthReport)
    assert rep.context_health_status == "CONTEXT_HEALTHY"
    assert rep.is_production_safe is True


def test_context_health_degraded():
    rep = context_health_monitor.evaluate_context_health(staleness_ms=6000.0, missing_horizons=2)

    assert rep.context_health_status == "CONTEXT_DEGRADED"
    assert rep.is_production_safe is False
