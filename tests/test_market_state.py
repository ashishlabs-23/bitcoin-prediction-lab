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

from engine.market_state import market_state_engine, MarketState
from api.server import app

client = TestClient(app)


def test_market_state_evaluation():
    state = market_state_engine.evaluate_market_state()

    assert isinstance(state, MarketState)
    assert state.symbol == "BTCUSD"
    assert "hawkes_event_pressure" in state.microstructure_state
    assert "regime" in state.volatility_state
    assert "long_term_risk_state" in state.long_term_state
    assert "summary" in state.explanation


def test_get_market_state_endpoints():
    res1 = client.get("/prediction/market-state")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["symbol"] == "BTCUSD"
    assert "volatility_state" in data1

    res2 = client.get("/prediction/market-state/history?limit=10")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["count"] == 10
