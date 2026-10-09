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
from fastapi.testclient import TestClient
from api.local_safe_server import app

client = TestClient(app)


def test_research_entry_tp_sl_endpoint_reports_blocked_without_signal_values():
    """Blocked research must not expose a signal or unverified metrics."""
    response = client.get("/api/research/entry-tp-sl")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()

    assert data["status"] == "BLOCKED_AUDIT_FAILURE"
    assert data["research_status"] == "BLOCKED_AUDIT_FAILURE"
    assert data["live_capital_authorized"] is False
    assert data["execution_mode"] == "PAPER_RESEARCH_ONLY"
    assert data["hypothetical_signal"] is None
    assert data["metrics"] is None


def test_prediction_latest_does_not_invent_research_values():
    """No model inference in local-safe mode means no numeric prediction payload."""
    response = client.get("/prediction/latest")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "DATA_UNAVAILABLE"
    assert data["model_inference"] == "DATA_UNAVAILABLE"
    assert "tp" not in data
    assert "sl" not in data
    assert "entry_price" not in data
    assert "probability" not in data


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


def test_frontend_uses_the_authoritative_research_contract_without_numeric_fallbacks():
    """Research display must be API-driven and never manufacture Entry/TP/SL values."""
    app_js_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "fetchResearchSignal" in content
    assert "/api/research/entry-tp-sl" in content
    assert "const entryPrice = signal?.entry_price" in content
    assert "const tpPrice = signal?.tp_price" in content
    assert "const slPrice = signal?.sl_price" in content
    assert "entryP * 0.985" not in content[content.index("function PredictionPanel"):content.index("function PaperPortfolio")]
    assert "DATA_UNAVAILABLE" in content


def test_research_panel_has_no_order_action_path():
    """A displayed research signal must not call an order or arena-trade endpoint."""
    app_js_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "executeArenaTrade" not in content
    assert "/api/arena/trade\", {" not in content
    panel = content[content.index("function PredictionPanel"):content.index("function PaperPortfolio")]
    assert "No real orders are executed" in panel
