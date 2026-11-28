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

    # Derivatives quadrant neutral labeling. Without a funding/OI observation the
    # quadrant is None and the layer is marked UNAVAILABLE — never a fabricated
    # "STABLE" label derived from placeholder defaults.
    assert "derivatives_quadrant" in state.derivatives_state
    quadrant = state.derivatives_state["derivatives_quadrant"]
    assert quadrant is None or quadrant in (
        "PRICE_UP_OI_UP",
        "PRICE_DOWN_OI_UP",
        "PRICE_DOWN_OI_DOWN",
        "PRICE_UP_OI_DOWN",
        "STABLE"
    )
    if quadrant is None:
        assert state.derivatives_state.get("governance_status") == "UNAVAILABLE"


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
    # The endpoint returns only genuinely persisted snapshots (it used to repeat
    # the current evaluation ten times and call that "history"). With a seeded
    # store it must return exactly those rows, newest last, capped by `limit`.
    assert data2["status"] in ("OBSERVED", "UNAVAILABLE_NOT_PERSISTED")
    assert data2["count"] == len(data2["history"])
    assert data2["count"] <= 10


def test_market_state_history_returns_only_persisted_snapshots(tmp_path, monkeypatch):
    """Seeded store -> exactly those rows; empty store -> explicit empty state."""
    import pandas as pd
    import api.routes_prediction as rp

    seeded = tmp_path / "market_state.csv"
    pd.DataFrame({
        "timestamp": [f"2026-11-28T{h:02d}:00:00+00:00" for h in range(12)],
        "symbol": ["BTCUSD"] * 12,
        "current_price": [59000.0 + h for h in range(12)],
    }).to_csv(seeded, index=False)
    monkeypatch.setattr("engine.market_state.RESULTS_DIR", str(tmp_path))

    body = rp.get_prediction_market_state_history(limit=10)
    assert body["status"] == "OBSERVED"
    assert body["count"] == 10
    # NaN must never reach the wire: FastAPI's strict JSON encoder raises on it.
    import json
    json.dumps(body, allow_nan=False)
    assert body["history"][-1]["current_price"] == 59011.0  # newest last

    seeded.unlink()
    empty = rp.get_prediction_market_state_history(limit=10)
    assert empty["status"] == "UNAVAILABLE_NOT_PERSISTED"
    assert empty["count"] == 0
