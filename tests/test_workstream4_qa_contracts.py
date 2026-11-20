"""Focused synthetic QA checks for frozen resolver and UI/API failure contracts."""

import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import market_monitor_routes, routes_market
from research.entry_tp_sl.barrier_contract import OutcomeState, PathBar, Side
from research.entry_tp_sl.triple_barrier import TripleBarrierEngine, build_trade_contract


ROOT = Path(__file__).resolve().parents[1]


def _synthetic_contract():
    return build_trade_contract(
        "barrier_pair_04",
        decision_timestamp=1_700_000_000,
        side=Side.LONG,
        next_1m_open=100_000.0,
        sigma_t0=0.01,
    )


def _synthetic_path(contract):
    price = contract.entry_price
    return [
        PathBar(
            timestamp=contract.fill_timestamp + (index + 1) * 60,
            open=price,
            high=price + 1.0,
            low=price - 1.0,
            close=price,
            volume=0.0,
        )
        for index in range(contract.vertical_horizon_bars_1m)
    ]


@pytest.mark.parametrize(
    ("price", "sigma"),
    [
        (float("nan"), 0.01),
        (float("inf"), 0.01),
        (100_000.0, float("nan")),
        (100_000.0, float("inf")),
        (100_000.0, 0.0),
    ],
)
def test_contract_builder_rejects_nonfinite_or_nonpositive_inputs(price, sigma):
    with pytest.raises(ValueError):
        build_trade_contract(
            "barrier_pair_04",
            decision_timestamp=1_700_000_000,
            side=Side.LONG,
            next_1m_open=price,
            sigma_t0=sigma,
        )


def test_resolver_fails_closed_without_a_path():
    event = TripleBarrierEngine().resolve(_synthetic_contract(), [])

    assert event.outcome_state == OutcomeState.DATA_UNAVAILABLE
    assert event.first_touch is None
    assert event.gross_return is None
    assert event.gross_r is None
    assert event.cost_r is None
    assert event.net_r is None
    assert event.realized_pnl_bps is None


def test_resolver_synthetic_complete_path_returns_finite_outputs():
    contract = _synthetic_contract()
    event = TripleBarrierEngine().resolve(contract, _synthetic_path(contract))

    assert event.outcome_state == OutcomeState.TIMEOUT
    for field in (
        event.gross_return,
        event.gross_r,
        event.cost_r,
        event.net_r,
        event.realized_pnl_bps,
    ):
        assert field is not None
        assert math.isfinite(field)
    json.dumps(event.to_dict(), allow_nan=False)


def _market_app():
    app = FastAPI()
    app.state.research_gate = {
        "status": "BLOCKED_PROVENANCE_UNVERIFIED",
        "authorized": False,
        "authorization_status": "BLOCKED_PROVENANCE_UNVERIFIED",
        "reason": "Synthetic fixture has no authenticated production inputs.",
    }
    app.include_router(market_monitor_routes.router)
    return app


def test_market_dashboard_unavailable_state_does_not_fabricate_provider_features(monkeypatch):
    async def unavailable_dashboard(client=None, horizon="24h"):
        raise RuntimeError("synthetic provider failure detail")

    monkeypatch.setattr(
        market_monitor_routes, "get_market_dashboard", unavailable_dashboard
    )

    with TestClient(_market_app()) as client:
        response = client.get("/api/dashboard?horizon=24h")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DATA_UNAVAILABLE"
    assert body["market"]["status"] == "DATA_UNAVAILABLE"
    assert body["market"]["source"] is None
    assert body["market"]["price_usd"] is None
    assert body["market"]["bid_usd"] is None
    assert body["market"]["ask_usd"] is None
    assert body["candles"] == []
    assert body["drivers"] == []
    assert body["forecast"]["status"] == "DATA_UNAVAILABLE"
    assert body["forecast"]["price_quantiles_usd"] is None
    assert body["derivatives"]["status"] == "UNAVAILABLE"
    assert body["derivatives"]["funding_rate"] is None
    assert body["derivatives"]["open_interest_contracts"] is None
    assert body["capital_flows"]["status"] == "NOT_CONFIGURED"
    assert body["macro"]["status"] == "NOT_CONFIGURED"
    assert body["provider_errors"] == {"dashboard": "RuntimeError"}
    assert "synthetic provider failure detail" not in response.text
    assert body["research"]["production_forecast_available"] is False
    assert body["research"]["trading_enabled"] is False


def test_offline_15m_candles_fail_closed_without_calling_provider(monkeypatch):
    from engine.coinbase_15m_adapter import coinbase_15m_adapter

    provider_calls = []

    def unexpected_provider_call(*args, **kwargs):
        provider_calls.append((args, kwargs))
        pytest.fail("The offline 15m candles route must not call its provider.")

    monkeypatch.setattr(routes_market, "is_external_network_permitted", lambda: False)
    monkeypatch.setattr(
        coinbase_15m_adapter,
        "get_or_sync_15m_candles",
        unexpected_provider_call,
    )

    app = FastAPI()
    app.include_router(routes_market.router)
    with TestClient(app) as client:
        response = client.get("/candles?interval=15m")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DATA_UNAVAILABLE"
    assert body["freshness_status"] == "UNAVAILABLE"
    assert body["candles"] == []
    assert body["count"] == 0
    assert provider_calls == []


def test_offline_15m_market_candles_serves_local_cache_without_provider(monkeypatch):
    import pandas as pd

    from engine import data_mode
    from engine.coinbase_15m_adapter import coinbase_15m_adapter

    provider_calls = []
    cached_candles = pd.DataFrame(
        [
            {
                "epoch_time": 1_700_000_100,
                "open": 100_000.0,
                "high": 100_100.0,
                "low": 99_900.0,
                "close": 100_050.0,
                "volume": 12.5,
            }
        ]
    )

    def unexpected_provider_call(*args, **kwargs):
        provider_calls.append((args, kwargs))
        pytest.fail("The offline cached-candles route must not call its provider.")

    monkeypatch.setattr(data_mode, "is_external_network_permitted", lambda: False)
    monkeypatch.setattr(
        coinbase_15m_adapter,
        "load_cached",
        lambda: (
            cached_candles,
            {"metadata": {"last_completed_candle_utc": "2023-11-14T22:30:00Z"}},
        ),
    )
    monkeypatch.setattr(
        coinbase_15m_adapter,
        "get_or_sync_15m_candles",
        unexpected_provider_call,
    )

    with TestClient(_market_app()) as client:
        response = client.get("/api/market/candles?interval=15m")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "HISTORICAL_SNAPSHOT"
    assert body["source"] == "LOCAL_HISTORICAL_CACHE"
    assert body["degraded"] is True
    assert body["count"] == 1
    assert body["candles"] == [
        {
            "time": 1_700_000_100,
            "open": 100_000.0,
            "high": 100_100.0,
            "low": 99_900.0,
            "close": 100_050.0,
            "volume": 12.5,
        }
    ]
    assert provider_calls == []


def test_frontend_accepts_local_historical_cache_candle_source():
    app_source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    whitelist = re.search(
        r"!\[(?P<sources>[^\]]+)\]\.includes\(resolvedSource\)", app_source
    )

    assert whitelist is not None
    accepted_sources = json.loads(f"[{whitelist.group('sources')}]")
    assert "LOCAL_HISTORICAL_CACHE" in accepted_sources


def test_health_response_keeps_all_execution_capabilities_disabled():
    with TestClient(_market_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["live_trading_enabled"] is False
    assert body["order_submission_enabled"] is False
    assert body["directional_recommendation_status"] == "DISABLED"
    assert body["execution_status"] == "DISABLED_ANALYSIS_ONLY"
    assert body["trading_enabled"] is False


def test_ui_forecast_response_states_for_stale_unavailable_and_malformed_payloads():
    node = shutil.which("node")
    assert node is not None, "Node.js is required to exercise the shipped frontend state function."
    app_source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    start = app_source.index("function getDirectionalForecastState(payload) {")
    end = app_source.index("\nfunction formatCandleCountdown", start)
    function_source = app_source[start:end]
    script = f"""
{function_source}
const common = {{
  status: "FORECAST_AVAILABLE_RESEARCH_ONLY",
  generated_at_utc: "2026-01-01T00:00:00Z",
  forecast_origin_timestamp: 1767225600,
  points: [{{ time: 1767225660, value: 100000 }}],
  directional_forecast: {{
    status: "RESEARCH_INFERENCE_AVAILABLE",
    predicted_direction: "UP",
    probability_up: 0.6,
    probability_down: 0.4
  }}
}};
const stale = getDirectionalForecastState({{
  ...common, data_freshness_status: "STALE"
}});
const unavailable = getDirectionalForecastState({{
  status: "DATA_UNAVAILABLE",
  reason: "Synthetic fixture has no market provider."
}});
const malformed = getDirectionalForecastState({{
  ...common,
  data_freshness_status: "FRESH",
  points: [{{ time: 1767225660, value: Number.POSITIVE_INFINITY }}]
}});
const fresh = getDirectionalForecastState({{
  ...common, data_freshness_status: "FRESH"
}});
console.log(JSON.stringify({{ stale, unavailable, malformed, fresh }}));
"""
    result = subprocess.run(
        [node, "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    states = json.loads(result.stdout)

    assert states["stale"]["status"] == "FORECAST_STALE"
    assert states["unavailable"]["status"] == "FORECAST_UNAVAILABLE"
    assert states["malformed"]["status"] == "FORECAST_MALFORMED"
    assert states["fresh"]["status"] == "FORECAST_AVAILABLE"
    assert states["fresh"]["probabilityUp"] == pytest.approx(0.6)
    assert states["fresh"]["probabilityDown"] == pytest.approx(0.4)
