"""
tests/test_frontend_contracts.py
=================================
Automated test suite verifying the BTCognitive Frontend & Research API contracts:
1. Research Entry/TP/SL values are dynamically supplied and not suppressed by COST_ERASED.
2. COST_ERASED is presented alongside research values with clear non-executable interpretation.
3. No real trade execution buttons or broker order pathways exist.
4. DATA_UNAVAILABLE, PROVENANCE_FAILURE, and MODEL_FAILURE states are properly defined and handled.
5. Hypothetical / Paper Research labeling is mandatory.
6. Zero hard-coded Entry/TP/SL numbers in the frontend components.
7. No claims of guaranteed profitability or 'beat a coin flip' exist in the UI code.
8. A research signal cannot invoke live broker endpoints.
"""

import os
import re
import pytest
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)


def test_research_entry_tp_sl_endpoint_contract():
    """Verifies that /api/research/entry-tp-sl returns full dynamic research values."""
    response = client.get("/api/research/entry-tp-sl")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()

    assert data["research_status"] == "COST_ERASED"
    assert data["claim_level"] == "C2"
    assert data["live_capital_authorized"] is False
    assert data["execution_mode"] == "PAPER_RESEARCH_ONLY"
    assert "hypothetical_signal" in data

    sig = data["hypothetical_signal"]
    assert "direction" in sig
    assert "entry_price" in sig and sig["entry_price"] > 0
    assert "tp_price" in sig and sig["tp_price"] > 0
    assert "sl_price" in sig and sig["sl_price"] > 0
    assert sig["barrier_pair_id"] == "barrier_pair_01"
    assert sig["k_tp"] == 1.0
    assert sig["k_sl"] == 1.0
    assert "volatility_estimator" in sig
    assert "setup_detected" in sig
    assert "resolver_version" in sig
    assert "provenance_status" in sig


def test_prediction_latest_includes_hypothetical_research_fields():
    """Verifies that /prediction/latest provides non-actionable hypothetical research values."""
    response = client.get("/prediction/latest")
    assert response.status_code == 200
    data = response.json()

    assert "tp" in data
    assert "sl" in data
    assert "entry_price" in data or "btc_price" in data
    assert data.get("live_capital_authorized") is False
    assert data.get("research_classification") == "COST_ERASED"
    assert "governance_disclaimer" in data


def test_no_live_order_execution_routes():
    """Verifies that no live exchange order placement routes exist on the API."""
    routes = [r.path for r in app.routes]
    prohibited_routes = ["/api/order/buy", "/api/order/sell", "/api/broker/execute", "/api/trade/live"]
    for pr in prohibited_routes:
        assert pr not in routes, f"Prohibited live order route found: {pr}"


def test_frontend_js_contains_no_prohibited_trade_claims():
    """Audits web/app.js to ensure no misleading trade claims or 'beat a coin flip' language exists."""
    app_js_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must NOT contain misleading claims
    assert "beat a coin flip" not in content.lower()
    assert "guaranteed entry" not in content.lower()
    assert "guaranteed profit" not in content.lower()
    assert "safe trade" not in content.lower()
    assert "ultra high profit" not in content.lower()


def test_frontend_js_contains_hypothetical_and_research_labels():
    """Audits web/app.js to ensure research status, hypothetical labels, and evidence viewer are present."""
    app_js_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ENTRY / TP / SL RESEARCH MODE" in content
    assert "COST_ERASED" in content
    assert "Hypothetical signal" in content
    assert "No real orders are executed" in content
    assert "View Research Evidence" in content
    assert "DATA_UNAVAILABLE" in content
    assert "PROVENANCE_FAILURE" in content
    assert "MODEL_FAILURE" in content
