import asyncio
import json
from datetime import datetime, timezone

import pytest

from api.candle_manager import CandleStateManager
from engine import market_data_feed
from engine.market_data_feed import BitstampTradeFeed, FreshnessStatus


def _feed(**kwargs):
    return BitstampTradeFeed(
        candle_manager=CandleStateManager(interval_seconds=60),
        **kwargs,
    )


def _trade(trade_id, event_microseconds, price, amount=1.0, channel="live_trades_btcusd"):
    return json.dumps({
        "event": "trade",
        "channel": channel,
        "data": {
            "id": trade_id,
            "timestamp": str(event_microseconds // 1_000_000),
            "microtimestamp": str(event_microseconds),
            "price": str(price),
            "amount": str(amount),
            "type": 0,
        },
    })


def test_bitstamp_timestamp_uses_microseconds_and_preserves_receipt_lag():
    feed = _feed()
    event_microseconds = 1_700_000_000_123_456
    receipt = datetime.fromtimestamp(1_700_000_000.5, timezone.utc)

    observation = feed._handle_raw_message(
        _trade(1, event_microseconds, 25_000),
        received_at=receipt,
    )

    assert observation is not None
    assert observation.event_timestamp == "2023-11-14T22:13:20.123456Z"
    assert observation.receipt_timestamp == "2023-11-14T22:13:20.500000Z"
    assert observation.payload["timestamp"] == "1700000000"
    assert observation.payload["microtimestamp"] == "1700000000123456"
    assert observation.latency_ms == pytest.approx(376.544, abs=1e-9)
    assert feed.snapshot()["event_to_receive_delay_seconds"] == pytest.approx(0.376544, abs=1e-12)


@pytest.mark.parametrize(
    "raw_message",
    [
        "{not-json",
        json.dumps({"event": "trade", "channel": "live_trades_btcusd", "data": {"id": 1}}),
        _trade(1, 1_700_000_000_000_000, 25_000, channel="live_trades_ethusd"),
    ],
)
def test_parser_rejects_malformed_and_non_btcusd_messages(raw_message):
    feed = _feed()

    assert feed._handle_raw_message(raw_message) is None

    snapshot = feed.snapshot()
    assert snapshot["candles"] == []
    assert snapshot["invalid_count"] == 1


def test_parser_rejects_nonintegral_trade_ids():
    feed = _feed()
    message = json.loads(_trade(1, 1_700_000_000_000_000, 25_000))
    message["data"]["id"] = 1.5

    assert feed._handle_raw_message(json.dumps(message)) is None
    assert feed.snapshot()["invalid_count"] == 1
    assert feed.snapshot()["candles"] == []


def test_duplicate_trade_id_is_ignored_without_changing_candle():
    feed = _feed()
    event_microseconds = 1_700_000_040_010_000
    receipt = datetime.fromtimestamp(1_700_000_040.1, timezone.utc)

    first = feed._handle_raw_message(
        _trade(7, event_microseconds, 100, amount=2),
        received_at=receipt,
    )
    duplicate = feed._handle_raw_message(
        _trade(7, event_microseconds + 1_000, 900, amount=100),
        received_at=receipt,
    )

    assert first is not None
    assert duplicate is None
    snapshot = feed.snapshot()
    assert snapshot["duplicate_count"] == 1
    candle = snapshot["candles"][0]
    assert {
        key: candle[key]
        for key in ("time", "open", "high", "low", "close", "volume", "is_closed")
    } == {
        "time": 1_700_000_040,
        "open": 100.0,
        "high": 100.0,
        "low": 100.0,
        "close": 100.0,
        "volume": 2.0,
        "is_closed": True,
    }
    assert candle["event_timestamp"] == "2023-11-14T22:14:00.010000Z"
    assert candle["received_timestamp"] == "2023-11-14T22:14:00.100000Z"
    assert candle["source"] == "bitstamp"


def test_out_of_order_trades_make_deterministic_minute_ohlcv_and_boundary():
    feed = _feed()
    minute_start_us = 1_700_000_040_000_000
    receipt = datetime.fromtimestamp(1_700_000_100, timezone.utc)

    for trade_id, offset_us, price, amount in (
        (12, 20_000_000, 120, 2),
        (10, 10_000_000, 100, 1),
        (13, 59_999_000, 130, 3),
        (14, 60_000_000, 200, 4),
    ):
        assert feed._handle_raw_message(
            _trade(trade_id, minute_start_us + offset_us, price, amount),
            received_at=receipt,
        ) is not None

    candles = feed.snapshot()["candles"]
    assert [
        {key: candle[key] for key in ("time", "open", "high", "low", "close", "volume", "is_closed")}
        for candle in candles
    ] == [
        {
            "time": 1_700_000_040,
            "open": 100.0,
            "high": 130.0,
            "low": 100.0,
            "close": 130.0,
            "volume": 6.0,
            "is_closed": True,
        },
        {
            "time": 1_700_000_100,
            "open": 200.0,
            "high": 200.0,
            "low": 200.0,
            "close": 200.0,
            "volume": 4.0,
            "is_closed": True,
        },
    ]
    assert candles[0]["event_timestamp"] == "2023-11-14T22:14:59.999000Z"
    assert candles[1]["event_timestamp"] == "2023-11-14T22:15:00.000000Z"


def test_missing_minute_is_reported_without_synthesizing_a_candle():
    feed = _feed()
    minute_start_us = 1_700_000_040_000_000
    receipt = datetime.fromtimestamp(1_700_000_400, timezone.utc)

    for trade_id, offset_us, price in (
        (1, 10_000_000, 100),
        (2, 190_000_000, 110),
    ):
        feed._handle_raw_message(
            _trade(trade_id, minute_start_us + offset_us, price),
            received_at=receipt,
        )

    snapshot = feed.snapshot()
    assert [candle["time"] for candle in snapshot["candles"]] == [
        1_700_000_040,
        1_700_000_220,
    ]
    assert len(snapshot["candles"]) == 2
    assert snapshot["gap_count"] == 2


def test_stale_status_uses_configured_threshold_including_exact_boundary(monkeypatch):
    fixed_now = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is not None else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(market_data_feed, "datetime", FrozenDateTime)

    on_boundary = _feed(stale_after_seconds=1)
    on_boundary._connected = True
    exact_boundary = on_boundary._handle_raw_message(
        _trade(1, int(fixed_now.timestamp() * 1_000_000) - 1_000_000, 100),
        received_at=fixed_now,
    )
    assert exact_boundary is not None
    assert exact_boundary.freshness_status is FreshnessStatus.FRESH
    assert on_boundary.snapshot()["status"] == "ACTIVE"

    beyond_boundary = _feed(stale_after_seconds=1)
    beyond_boundary._connected = True
    stale = beyond_boundary._handle_raw_message(
        _trade(2, int(fixed_now.timestamp() * 1_000_000) - 1_000_001, 100),
        received_at=fixed_now,
    )
    assert stale is not None
    assert stale.freshness_status is FreshnessStatus.STALE
    assert beyond_boundary.snapshot()["status"] == "STALE"


def test_disconnected_feed_and_no_data_are_explicit_states():
    feed = _feed()

    empty = feed.snapshot()
    assert empty["status"] == "DATA_UNAVAILABLE"
    assert empty["feed_state"] == "DATA_UNAVAILABLE"
    assert empty["last_event_timestamp"] is None
    assert empty["candles"] == []

    feed._ever_connected = True
    feed.stop()
    disconnected = feed.snapshot()
    assert disconnected["status"] == "DISCONNECTED"
    assert disconnected["feed_state"] == "DISCONNECTED"
    assert disconnected["candles"] == []


def test_reconnect_backoff_is_exponential_and_capped_without_network(monkeypatch):
    import websockets

    feed = _feed(max_reconnect_delay_seconds=3)
    delays = []

    class FailingConnection:
        async def __aenter__(self):
            raise ConnectionError("deterministic fixture disconnect")

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(websockets, "connect", lambda *args, **kwargs: FailingConnection())

    async def record_wait(awaitable, timeout):
        delays.append(timeout)
        awaitable.close()
        if len(delays) == 4:
            feed._stop_requested = True
        raise asyncio.TimeoutError

    monkeypatch.setattr(asyncio, "wait_for", record_wait)

    async def run_loop():
        feed._stop_requested = False
        feed._stop_event = asyncio.Event()
        await feed._connection_loop()

    asyncio.run(run_loop())

    assert delays == [1.0, 2.0, 3.0, 3]
    assert feed.snapshot()["reconnect_count"] == 4
    assert feed.snapshot()["feed_state"] == "DISCONNECTED"
