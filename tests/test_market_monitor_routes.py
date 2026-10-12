from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import market_monitor_routes as routes


def _app():
    app = FastAPI()
    app.state.research_gate = {"status": "BLOCKED_PROVENANCE_UNVERIFIED", "authorized": False,
                               "reason": "Frozen inputs are not authenticated."}
    app.include_router(routes.router)
    return app


def _dashboard_payload():
    return {
        "status": "LIVE",
        "generated_at": "2026-10-12T00:00:00Z",
        "market": {"status": "LIVE", "symbol": "BTC/USD", "source": "coinbase",
                   "price_usd": 100000.0, "bid_usd": 99999.0, "ask_usd": 100001.0,
                   "retrieved_at": "2026-10-12T00:00:00Z", "age_seconds": 0.1},
        "technical": {"momentum_24h_pct": 0.5},
        "candles": [], "candle_count": 0,
        "forecast": {"status": "EXPERIMENTAL_BASELINE", "availability": "AVAILABLE",
                     "horizon": "24h", "spot_price_usd": 100000.0,
                     "price_quantiles_usd": {"p10": 98000, "p50": 100500, "p90": 103000},
                     "return_quantiles_pct": {"p10": -2, "p50": 0.5, "p90": 3},
                     "direction": "NOT_ESTIMATED", "probability_pct": None, "tp": None, "sl": None,
                     "live_capital_authorized": False, "research_classification": "EXPERIMENTAL_BASELINE",
                     "governance_disclaimer": "Historical baseline only.",
                     "sample_blocks": 90, "backtest": {"status": "INSUFFICIENT_HOLDOUT", "test_blocks": 10}},
        "drivers": [], "derivatives": {"status": "UNAVAILABLE"},
        "capital_flows": {"status": "NOT_CONFIGURED"}, "macro": {"status": "NOT_CONFIGURED"},
        "research": {"status": "BLOCKED_PROVENANCE_UNVERIFIED", "production_forecast_available": False,
                     "trading_enabled": False},
        "provider_errors": {},
    }


def test_dashboard_returns_source_backed_payload_and_research_stays_blocked(monkeypatch):
    async def fake_dashboard(client=None, horizon="24h"):
        result = _dashboard_payload()
        result["forecast"]["horizon"] = horizon
        return result

    monkeypatch.setattr(routes, "get_market_dashboard", fake_dashboard)
    response = TestClient(_app()).get("/api/dashboard?horizon=4h")
    assert response.status_code == 200
    body = response.json()
    assert body["market"]["symbol"] == "BTC/USD"
    assert body["forecast"]["horizon"] == "4h"
    assert body["research"]["authorized"] is False
    assert body["research"]["production_forecast_available"] is False
    assert body["research"]["trading_enabled"] is False


def test_prediction_compatibility_endpoint_uses_empirical_baseline_not_directional_signal(monkeypatch):
    async def fake_dashboard(client=None, horizon="24h"):
        result = _dashboard_payload()
        result["forecast"]["horizon"] = horizon
        return result

    monkeypatch.setattr(routes, "get_market_dashboard", fake_dashboard)
    response = TestClient(_app()).get("/prediction/latest?horizon=24h")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "EXPERIMENTAL_BASELINE"
    assert body["direction"] == "NOT_ESTIMATED"
    assert body["probability_pct"] is None
    assert body["tp"] is None and body["sl"] is None
    assert body["live_capital_authorized"] is False
    assert body["research"]["authorized"] is False


def test_research_contract_never_returns_synthetic_entry_tp_sl():
    response = TestClient(_app()).get("/api/research/entry-tp-sl")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "BLOCKED"
    assert body["hypothetical_signal"] is None
    assert body["entry_price"] is None
    assert body["tp_price"] is None
    assert body["sl_price"] is None
    assert body["live_capital_authorized"] is False


def test_monitor_health_can_be_ok_while_production_forecasts_are_blocked():
    body = TestClient(_app()).get("/health").json()
    assert body["status"] == "ok"
    assert body["mode"] == "MARKET_MONITOR_ONLY"
    assert body["research_authorized"] is False
    assert body["production_forecast_available"] is False
    assert body["trading_enabled"] is False


def test_non_btc_usd_or_non_hourly_candle_request_fails_explicitly():
    response = TestClient(_app()).get("/market/candles?symbol=BTCUSDT&interval=1m")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "UNSUPPORTED_REQUEST"
    assert body["candles"] == []