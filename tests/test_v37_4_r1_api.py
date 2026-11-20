import time
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import market_monitor_routes
from api import server
from api.candle_manager import CandleStateManager
from engine import data_mode
from engine.market_data_feed import BitstampTradeFeed


class _LifecycleFixtureFeed(BitstampTradeFeed):
    def __init__(self):
        super().__init__(candle_manager=CandleStateManager(interval_seconds=60))
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True
        self._connected = True
        self._ever_connected = True
        self._feed_state = "CONNECTED"
        return True

    def stop(self):
        self.stopped = True
        self._connected = False
        self._feed_state = "DISCONNECTED"
        return True


def _observed_trade(feed):
    event_time = datetime.fromtimestamp(time.time() - 2, timezone.utc)
    microtimestamp = int(event_time.timestamp() * 1_000_000)
    message = (
        '{"event":"trade","channel":"live_trades_btcusd","data":'
        f'{{"id":731,"timestamp":"{microtimestamp // 1_000_000}",'
        f'"microtimestamp":"{microtimestamp}","price":"68420.5",'
        '"amount":"0.025","type":0}}'
    )
    receipt = datetime.now(timezone.utc)
    observation = feed._handle_raw_message(message, received_at=receipt)
    assert observation is not None
    return observation


def test_fastapi_lifespan_starts_feed_and_candle_route_returns_actual_observations(monkeypatch):
    # This fixture is explicitly authorized only inside the deterministic test;
    # no external connection is made.
    monkeypatch.setattr(data_mode, "is_external_network_permitted", lambda: True)
    feed = _LifecycleFixtureFeed()
    observation = _observed_trade(feed)
    app = FastAPI(lifespan=server.lifespan)
    app.state.bitstamp_trade_feed = feed
    app.include_router(market_monitor_routes.router)

    monkeypatch.setattr(server, "verify_scientific_contract", lambda: None)
    monkeypatch.setattr(server, "evaluate_runtime_readiness", lambda force_refresh: {"status": "BLOCKED"})
    monkeypatch.setattr(server, "is_production_authorized", lambda readiness: False)
    monkeypatch.setattr(server, "get_shared_client", lambda: object())
    monkeypatch.setattr(server.feature_cache, "initialize", lambda: None)

    async def close_client():
        return None

    monkeypatch.setattr(server, "close_shared_client", close_client)

    with TestClient(app) as client:
        assert feed.started is True
        response = client.get(
            "/api/market/candles?symbol=BTC-USD&interval=1m&limit=5"
        )
        assert response.status_code == 200
        body = response.json()

    assert feed.stopped is True
    assert body["status"] == "ACTIVE"
    assert body["freshness_status"] == "FRESH"
    assert body["exchange"] == "Bitstamp"
    assert body["source"] == "bitstamp"
    assert body["symbol"] == "BTC/USD"
    assert body["interval"] == "1m"
    assert body["count"] == 1
    candle = body["candles"][0]
    event_epoch = datetime.fromisoformat(
        observation.event_timestamp.replace("Z", "+00:00")
    ).timestamp()
    assert candle["time"] == int(event_epoch // 60) * 60
    assert candle["open"] == 68420.5
    assert candle["close"] == 68420.5
    assert candle["volume"] == 0.025
    assert candle["source"] == "bitstamp"
    assert body["last_event_timestamp"] == observation.event_timestamp
    assert body["last_receive_timestamp"] == observation.receipt_timestamp
    assert body["event_to_receive_delay_seconds"] >= 0
    assert body["analysis"]["status"] == "DATA_UNAVAILABLE"
    assert body["analysis"]["engine_invoked"] is False


def test_one_minute_route_fails_closed_for_wrong_symbol_and_missing_feed():
    app = FastAPI()
    app.include_router(market_monitor_routes.router)
    app.state.bitstamp_trade_feed = None

    with TestClient(app) as client:
        wrong_symbol = client.get(
            "/api/market/candles?symbol=ETH-USD&interval=1m"
        ).json()
        missing_feed = client.get(
            "/api/market/candles?symbol=BTC-USD&interval=1m"
        ).json()

    assert wrong_symbol["status"] == "UNSUPPORTED_REQUEST"
    assert wrong_symbol["candles"] == []
    assert missing_feed["status"] == "DATA_UNAVAILABLE"
    assert missing_feed["freshness_status"] == "UNAVAILABLE"
    assert missing_feed["count"] == 0
    assert missing_feed["candles"] == []


def test_fresh_contiguous_candles_reach_existing_descriptive_engine():
    now = int(time.time())
    current_minute = now // 60 * 60
    candles = []
    for offset in range(20, 0, -1):
        candle_time = current_minute - offset * 60
        close = 68_000 + (20 - offset) * 2
        candles.append({
            "time": candle_time,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": 0.5 + (20 - offset) * 0.01,
            "is_closed": True,
            "quality_status": "VALID",
            "source": "bitstamp",
        })
    last_event = datetime.fromtimestamp(
        candles[-1]["time"] + 55, timezone.utc
    ).isoformat().replace("+00:00", "Z")
    receipt = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    normalized = market_monitor_routes._normalize_bitstamp_snapshot({
        "status": "ACTIVE",
        "feed_state": "CONNECTED",
        "symbol": "BTC/USD",
        "exchange": "Bitstamp",
        "market_type": "SPOT",
        "interval": "1m",
        "source": "bitstamp",
        "last_event_timestamp": last_event,
        "last_receive_timestamp": receipt,
        "event_to_receive_delay_seconds": 0.1,
        "gap_count": 0,
        "duplicate_count": 0,
        "invalid_count": 0,
        "candles": candles,
    }, 500)

    assert normalized["status"] == "ACTIVE"
    assert normalized["analysis"]["engine_invoked"] is True
    assert normalized["analysis"]["engine"] == "MarketIntelligenceEngine"
    assert normalized["analysis"]["input_source"] == "bitstamp"
    assert normalized["analysis"]["input_candle_count"] == 20
    assert normalized["analysis"]["input_freshness"] == "FRESH"
    assert normalized["analysis"]["status"] == "UNVALIDATED"
    assert set(normalized["analysis"]["components"]) == {"structure", "momentum"}
