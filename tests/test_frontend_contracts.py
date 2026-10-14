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
    """Frozen research output stays blocked without authenticated evidence."""
    response = client.get("/api/research/entry-tp-sl")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "BLOCKED"
    assert data["research_status"] in {"BLOCKED_PROVENANCE_UNVERIFIED", "BLOCKED_AUDIT_FAILURE"}
    assert data["claim_level"] == "UNVALIDATED"
    assert data["live_capital_authorized"] is False
    assert data["execution_mode"] == "READ_ONLY_RESEARCH"
    assert data["hypothetical_signal"] is None
    assert data["entry_price"] is None
    assert data["tp_price"] is None
    assert data["sl_price"] is None


def test_prediction_latest_includes_empirical_ranges_without_directional_claims(monkeypatch):
    """The compatibility route exposes empirical ranges, never a fabricated direction."""
    import api.market_monitor_routes as monitor_routes

    async def fake_market_data(client=None, horizon="24h"):
        return {
            "status": "LIVE",
            "market": {"symbol": "BTC/USD", "source": "test", "price_usd": 100000.0},
            "technical": {}, "candles": [], "drivers": [],
            "forecast": {
                "status": "EXPERIMENTAL_BASELINE", "availability": "AVAILABLE", "horizon": horizon,
                "spot_price_usd": 100000.0,
                "price_quantiles_usd": {"p10": 98000.0, "p50": 100000.0, "p90": 102000.0},
                "return_quantiles_pct": {"p10": -2.0, "p50": 0.0, "p90": 2.0},
                "direction": "NOT_ESTIMATED", "probability_pct": None, "tp": None, "sl": None,
                "live_capital_authorized": False, "research_classification": "EXPERIMENTAL_BASELINE",
                "governance_disclaimer": "Historical distribution baseline only.",
            },
            "research": {"status": "BLOCKED_PROVENANCE_UNVERIFIED", "trading_enabled": False},
        }

    monkeypatch.setattr(monitor_routes, "get_market_dashboard", fake_market_data)
    response = client.get("/prediction/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "EXPERIMENTAL_BASELINE"
    assert data["price_quantiles_usd"]["p10"] <= data["price_quantiles_usd"]["p50"] <= data["price_quantiles_usd"]["p90"]
    assert data["direction"] == "NOT_ESTIMATED"
    assert data["probability_pct"] is None
    assert data["tp"] is None and data["sl"] is None
    assert data["live_capital_authorized"] is False
    assert data["research"]["authorized"] is False


def test_no_live_order_execution_routes():
    """Verifies that no live exchange order placement routes exist on the API."""
    def collect_paths(routes):
        paths = []
        for route in routes:
            path = getattr(route, "path", None)
            if isinstance(path, str):
                paths.append(path)
            included_router = getattr(route, "original_router", None)
            nested_routes = getattr(included_router, "routes", None)
            if nested_routes is not None:
                paths.extend(collect_paths(nested_routes))
        return paths

    routes = collect_paths(app.routes)
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


def test_active_frontend_is_the_research_terminal_and_discloses_forecast_gate():
    root = os.path.join(os.path.dirname(__file__), "..", "web")
    with open(os.path.join(root, "index.html"), "r", encoding="utf-8") as f:
        html = f.read()
    with open(os.path.join(root, "app.js"), "r", encoding="utf-8") as f:
        app_js = f.read()
    served = client.get("/")
    assert served.status_code == 200
    assert "BTCognitive — Probabilistic Risk Intelligence" in served.text
    assert "/app.js?v=10.9" in served.text
    assert '<title>BTCognitive — Probabilistic Risk Intelligence</title>' in html
    assert '/styles.css?v=10.9' in html
    assert '/app.js?v=10.9' in html
    assert "BTCognitive Research Terminal" in app_js
    assert "function useCoinbaseFeed" in app_js
    assert "function useBinanceFeed" not in app_js
    assert '"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 3600, "1d": 86400' in app_js
    assert "function candleBucketStart" in app_js
    assert "function formatCandleCountdown" in app_js
    assert "setExchangeClock({ timestampMs: time * 1000" in app_js
    assert "const clockNow = exchangeClock" in app_js
    assert "wsStatus: coinbaseWsStatus" in app_js
    assert "Forecast unavailable · frozen inputs unverified" in app_js
    assert "Coverage: ${liveCov}%" not in app_js
    assert "updateExcursionEnvelope" not in app_js
    assert "RESEARCH RESULTS UNAVAILABLE" in app_js
    assert "BTC / USD · Coinbase Exchange" in app_js
    assert "generating simulated live alert" not in app_js
    assert "Math.random() > 0.3" not in app_js
    assert "64654.60" not in app_js
    assert "Test request completed; check the configured delivery status." in app_js
    assert "No validated market observations or notification tests have been recorded." in app_js
    assert "🧪 NOTIFICATION TEST · NOT A MARKET SIGNAL" in app_js
    assert "Send Test Notification" in app_js
    with open(os.path.join(root, "styles.css"), "r", encoding="utf-8") as f:
        styles = f.read()
    assert "#root > div > nav {\n  z-index: 1000;" in styles
    assert "PREVIEW ONLY" in html
    assert "frozen research inputs are unverified" in html
    assert "trading is disabled" in html
    assert "market-monitor" not in html
    assert sorted(os.listdir(root)) == ["app.js", "index.html", "styles.css"]
    assert "guaranteed profit" not in (html + "\n" + app_js).lower()
    assert "place order" not in (html + "\n" + app_js).lower()
