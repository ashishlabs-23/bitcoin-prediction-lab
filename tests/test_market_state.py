"""
tests/test_market_state.py — Unit Tests for Unified Multiscale Market-State Orchestrator
========================================================================================
Verifies:
1. Complete synthesis of MarketState schema across all layers
2. Integration with GET /prediction/market-state and GET /prediction/market-state/history
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.market_state import (
    market_state_engine,
    MarketState,
    classify_utc_session,
    classify_derivatives_quadrant,
)
from api.server import app
from datetime import datetime, timezone

client = TestClient(app)


def test_market_state_evaluation():
    state = market_state_engine.evaluate_market_state()

    assert isinstance(state, MarketState)
    assert state.symbol == "BTCUSD"
    assert "hawkes_event_pressure" in state.microstructure_state
    assert "regime" in state.volatility_state
    assert "long_term_risk_state" in state.long_term_state
    assert "summary" in state.explanation

    # Session context
    assert state.session_context is not None
    assert "session_state" in state.session_context
    assert "utc_hour" in state.session_context
    assert state.session_context["session_version"] == "1.0.0"

    # Derivatives quadrant neutral labeling
    assert "derivatives_quadrant" in state.derivatives_state
    assert state.derivatives_state["derivatives_quadrant"] in (
        "PRICE_UP_OI_UP",
        "PRICE_DOWN_OI_UP",
        "PRICE_DOWN_OI_DOWN",
        "PRICE_UP_OI_DOWN",
        "STABLE"
    )


def test_classify_utc_session():
    # Explicit half-open interval boundary testing:
    # 1. 06:59 vs 07:00
    assert classify_utc_session(datetime(2026, 9, 8, 6, 59, tzinfo=timezone.utc))["session_state"] == "ASIA_RANGE"
    assert classify_utc_session(datetime(2026, 9, 8, 7, 0, tzinfo=timezone.utc))["session_state"] == "LONDON_EXPANSION"

    # 2. 13:29 vs 13:30
    assert classify_utc_session(datetime(2026, 9, 8, 13, 29, tzinfo=timezone.utc))["session_state"] == "LONDON_EXPANSION"
    assert classify_utc_session(datetime(2026, 9, 8, 13, 30, tzinfo=timezone.utc))["session_state"] == "NY_LONDON_OVERLAP"

    # 3. 16:29 vs 16:30
    assert classify_utc_session(datetime(2026, 9, 8, 16, 29, tzinfo=timezone.utc))["session_state"] == "NY_LONDON_OVERLAP"
    assert classify_utc_session(datetime(2026, 9, 8, 16, 30, tzinfo=timezone.utc))["session_state"] == "US_AFTERNOON"

    # 4. 20:59 vs 21:00
    assert classify_utc_session(datetime(2026, 9, 8, 20, 59, tzinfo=timezone.utc))["session_state"] == "US_AFTERNOON"
    assert classify_utc_session(datetime(2026, 9, 8, 21, 0, tzinfo=timezone.utc))["session_state"] == "POST_CLOSE_CHOP"

    # 5. 23:59 vs 00:00
    assert classify_utc_session(datetime(2026, 9, 8, 23, 59, tzinfo=timezone.utc))["session_state"] == "POST_CLOSE_CHOP"
    assert classify_utc_session(datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc))["session_state"] == "ASIA_RANGE"


def test_classify_derivatives_quadrant_neutral_labels():
    assert classify_derivatives_quadrant(0.5, 1.0) == "PRICE_UP_OI_UP"
    assert classify_derivatives_quadrant(-0.5, 1.0) == "PRICE_DOWN_OI_UP"
    assert classify_derivatives_quadrant(-0.5, -1.0) == "PRICE_DOWN_OI_DOWN"
    assert classify_derivatives_quadrant(0.5, -1.0) == "PRICE_UP_OI_DOWN"
    assert classify_derivatives_quadrant(0.01, 0.01) == "STABLE"


def test_get_market_state_endpoints():
    res1 = client.get("/prediction/market-state")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["symbol"] == "BTCUSD"
    assert "volatility_state" in data1
    assert "session_context" in data1
    assert "derivatives_quadrant" in data1["derivatives_state"]

    res2 = client.get("/prediction/market-state/history?limit=10")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["count"] == 10
