"""
tests/test_horizon_contract.py — Tests for Production and Shadow Horizon Contracts
==================================================================================
Verifies that:
- Production horizon is 24 hours (24 bars).
- Outcome resolution window equals production horizon (24 hours).
- Hawkes shadow is isolated to 5 minutes and marked non-production.
"""

from models.horizon_contract import (
    PRODUCTION_RANGE_HORIZON_HOURS,
    PRODUCTION_RANGE_HORIZON_BARS,
    PRODUCTION_RANGE_HORIZON_LABEL,
    OUTCOME_RESOLUTION_HORIZON_HOURS,
    HAWKES_SHADOW_HORIZON_MINUTES,
    HAWKES_SHADOW_HORIZON_LABEL,
    HAWKES_SHADOW_IS_PRODUCTION
)

def test_production_horizon_constants():
    assert PRODUCTION_RANGE_HORIZON_HOURS == 24
    assert PRODUCTION_RANGE_HORIZON_BARS == 24
    assert PRODUCTION_RANGE_HORIZON_LABEL == "24h"
    assert OUTCOME_RESOLUTION_HORIZON_HOURS == 24

def test_hawkes_shadow_horizon_constants():
    assert HAWKES_SHADOW_HORIZON_MINUTES == 5
    assert HAWKES_SHADOW_HORIZON_LABEL == "5m"
    assert HAWKES_SHADOW_IS_PRODUCTION is False
