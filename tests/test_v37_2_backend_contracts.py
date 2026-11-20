import asyncio
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import market_monitor_routes as routes
from api import routes_user_positions as position_routes


def _client(gate=None):
    app = FastAPI()
    app.state.research_gate = gate or {
        "status": "BLOCKED_AUDIT_FAILURE",
        "authorized": False,
        "authorization_status": "BLOCKED_AUDIT_FAILURE",
        "reason": "Synthetic test gate.",
    }
    app.include_router(routes.router)
    return TestClient(app)


def _dashboard_payload():
    return {
        "status": "LIVE",
        "market": {
            "status": "LIVE",
            "symbol": "BTC/USD",
            "source": "synthetic_fixture",
            "price_usd": 100000.0,
            "retrieved_at": "2026-11-04T10:00:00Z",
        },
        "candles": [],
        "forecast": {
            "status": "EXPERIMENTAL_BASELINE",
            "availability": "AVAILABLE",
            "horizon": "24h",
            "direction": "NOT_ESTIMATED",
            "probability_pct": None,
            "tp": None,
            "sl": None,
            "live_capital_authorized": False,
        },
        "drivers": [],
    }


def test_health_and_readiness_keep_monitor_health_separate_from_authorization(monkeypatch):
    class SyntheticSystemStatus:
        def model_dump(self):
            return {"status": "BLOCKED_AUDIT_FAILURE"}

    status_module = ModuleType("engine.status_contract")
    status_module.evaluate_system_status = lambda: SyntheticSystemStatus()
    monkeypatch.setitem(sys.modules, "engine.status_contract", status_module)

    with _client() as client:
        health = client.get("/api/health")
        readiness = client.get("/api/readiness")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["mode"] == "MARKET_MONITOR_ONLY"
    assert health.json()["research_authorized"] is False
    assert health.json()["trading_enabled"] is False
    assert readiness.status_code == 200
    assert readiness.json()["authorization_status"] == "BLOCKED_AUDIT_FAILURE"
    assert readiness.json()["live_trading_enabled"] is False
    assert readiness.json()["order_submission_enabled"] is False


def test_dashboard_success_failure_and_invalid_horizon_are_explicit(monkeypatch):
    async def successful_dashboard(client=None, horizon="24h"):
        payload = _dashboard_payload()
        payload["forecast"]["horizon"] = horizon
        return payload

    monkeypatch.setattr(routes, "get_market_dashboard", successful_dashboard)
    with _client() as client:
        response = client.get("/api/dashboard?horizon=4h")
        market = client.get("/api/market/latest")
        prediction = client.get("/api/prediction/latest?horizon=4h")
        invalid = client.get("/api/dashboard?horizon=2d")

    assert response.status_code == 200
    assert response.json()["forecast"]["horizon"] == "4h"
    assert response.json()["research"]["authorized"] is False
    assert response.json()["research"]["trading_enabled"] is False
    assert market.status_code == 200
    assert market.json()["symbol"] == "BTC/USD"
    assert market.json()["data_status"] == "LIVE"
    assert prediction.status_code == 200
    assert prediction.json()["horizon"] == "4h"
    assert prediction.json()["direction"] == "NOT_ESTIMATED"
    assert prediction.json()["live_capital_authorized"] is False
    assert invalid.status_code == 422

    async def failing_dashboard(client=None, horizon="24h"):
        raise RuntimeError("synthetic provider failure")

    monkeypatch.setattr(routes, "get_market_dashboard", failing_dashboard)
    failed = _client().get("/api/market/dashboard")
    assert failed.status_code == 200
    assert failed.json()["status"] == "DATA_UNAVAILABLE"
    assert failed.json()["market"]["price_usd"] is None
    assert failed.json()["provider_errors"] == {"dashboard": "RuntimeError"}
    assert "synthetic provider failure" not in failed.text


def test_candles_reject_invalid_symbol_and_interval_without_market_access(monkeypatch):
    monkeypatch.setenv("BTC_DATA_MODE", "fixture")
    adapter_module = ModuleType("engine.coinbase_15m_adapter")
    adapter_module.coinbase_15m_adapter = SimpleNamespace(load_cached=lambda: None)
    monkeypatch.setitem(sys.modules, "engine.coinbase_15m_adapter", adapter_module)
    with _client() as client:
        symbol = client.get("/api/market/candles?symbol=ETH-USD&interval=1h")
        interval = client.get("/api/market/candles?symbol=BTC-USD&interval=1m")
        unavailable = client.get("/api/market/candles?symbol=BTC-USD&interval=15m")

    assert symbol.status_code == 200
    assert symbol.json()["status"] == "UNSUPPORTED_REQUEST"
    assert symbol.json()["candles"] == []
    assert interval.status_code == 200
    assert interval.json()["status"] == "UNSUPPORTED_REQUEST"
    assert interval.json()["candles"] == []
    assert unavailable.status_code == 200
    assert unavailable.json()["status"] == "DATA_UNAVAILABLE"
    assert unavailable.json()["candles"] == []


def test_btcusdt_candle_request_is_rejected_without_market_data_access(monkeypatch):
    monkeypatch.setenv("BTC_DATA_MODE", "fixture")

    def unexpected_market_access(*args, **kwargs):
        pytest.fail("A BTCUSDT request must be rejected before market-data access.")

    monkeypatch.setattr(routes, "get_market_dashboard", unexpected_market_access)
    wrong_quote = _client().get("/api/market/candles?symbol=BTCUSDT&interval=1h&limit=1")

    assert wrong_quote.status_code == 200
    assert wrong_quote.json()["status"] == "UNSUPPORTED_REQUEST"
    assert wrong_quote.json()["symbol"] == "BTC-USD"
    assert wrong_quote.json()["candles"] == []


def test_position_risk_routes_do_not_inject_unvalidated_forecasts_or_regimes(monkeypatch):
    class SyntheticPosition:
        position_id = "synthetic-position"
        user_id = "synthetic-user"

        def to_dict(self):
            return {"position_id": self.position_id}

    class SyntheticSnapshot:
        net_unrealized_pnl_usd = 0.0
        cost_basis_usd = 0.0

        def to_dict(self):
            return {"gbdt_forecasts": {}, "regime_context": {}}

    position = SyntheticPosition()
    captured_calls = []
    monkeypatch.setattr(
        position_routes,
        "_tracker",
        SimpleNamespace(
            get_open_positions=lambda user_id=None: [position],
            get_position=lambda position_id: position,
        ),
    )
    monkeypatch.setattr(
        position_routes,
        "_copilot",
        SimpleNamespace(
            evaluate_position_risk=lambda **kwargs: (
                captured_calls.append(kwargs) or SyntheticSnapshot()
            )
        ),
    )

    async def unavailable_quote(request):
        return {"status": "UNAVAILABLE", "price": None}

    monkeypatch.setattr(position_routes, "_get_current_market_quote", unavailable_quote)
    asyncio.run(position_routes.list_open_positions(
        request=None, principal_id="synthetic-user"
    ))
    asyncio.run(position_routes.get_position_detail(
        "synthetic-position", request=None, principal_id="synthetic-user"
    ))

    assert len(captured_calls) == 2
    assert all("gbdt_forecasts" not in call for call in captured_calls)
    assert all("regime_data" not in call for call in captured_calls)


def test_comparator_stale_and_offline_unavailable_contracts(monkeypatch):
    comparator_module = ModuleType("engine.spot_exchange_comparator")

    async def stale_comparison(client=None):
        return {
            "status": "DEGRADED",
            "active_primary_provider": None,
            "primary_price_usd": None,
            "healthy_providers_count": 0,
            "quotes": {"coinbase": {"quality": "STALE"}},
        }

    comparator_module.fetch_and_compare_spot_quotes = stale_comparison
    monkeypatch.setitem(sys.modules, "engine.spot_exchange_comparator", comparator_module)
    stale = _client().get("/market/comparator")
    assert stale.status_code == 200
    assert stale.json()["status"] == "DEGRADED"
    assert stale.json()["quotes"]["coinbase"]["quality"] == "STALE"

    monkeypatch.delitem(sys.modules, "engine.spot_exchange_comparator")
    monkeypatch.setenv("BTC_DATA_MODE", "fixture")
    unavailable = _client().get("/api/market/comparator")
    assert unavailable.status_code == 200
    assert unavailable.json()["status"] == "DATA_UNAVAILABLE"
    assert unavailable.json()["divergence_reason"] == "EXTERNAL_NETWORK_BLOCKED"
    assert unavailable.json()["quotes"] == {}


def test_forecast_and_analysis_contracts_fail_closed(monkeypatch):
    forecast_module = ModuleType("engine.forecast_engine_15m")
    forecast_module.generate_forecast_contract = lambda horizon: {
        "status": "DATA_UNAVAILABLE",
        "horizon": horizon,
        "forecast": None,
        "live_capital_authorized": False,
    }
    monkeypatch.setitem(sys.modules, "engine.forecast_engine_15m", forecast_module)

    with _client() as client:
        forecast = client.get("/api/forecast/latest?horizon=15m")
        analysis = client.get("/api/research/entry-tp-sl")

    assert forecast.status_code == 200
    assert forecast.json()["status"] == "DATA_UNAVAILABLE"
    assert forecast.json()["horizon"] == "15m"
    assert forecast.json()["forecast"] is None
    assert forecast.json()["live_capital_authorized"] is False
    assert analysis.status_code == 200
    assert analysis.json()["status"] == "BLOCKED"
    assert analysis.json()["hypothetical_signal"] is None
    assert analysis.json()["entry_price"] is None
    assert analysis.json()["tp_price"] is None
    assert analysis.json()["sl_price"] is None
    assert analysis.json()["trading_enabled"] is False


def test_active_frontend_maps_to_checked_market_and_forecast_routes():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "web" / "app.js").read_text(encoding="utf-8")

    assert '<div id="root"></div>' in html
    assert 'src="/app.js?v=35.4.1"' in html
    assert 'fetch(`${getApiBaseUrl()}/market/latest`)' in app_js
    assert "/api/market/candles?symbol=BTC-USD&interval=${sourceInterval}&limit=500" in app_js
    assert 'fetch(`${getApiBaseUrl()}/market/comparator`)' in app_js
    assert "/api/forecast/latest?horizon=${encodeURIComponent(horizon)}" in app_js
    assert "/api/prediction/price/forecast" in app_js
    assert "/api/research/entry-tp-sl" not in app_js
    monitor_routes = (root / "api" / "market_monitor_routes.py").read_text(encoding="utf-8")
    assert '@router.get("/api/research/entry-tp-sl")' in monitor_routes
