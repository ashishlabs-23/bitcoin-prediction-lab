import logging
import threading
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import market_monitor_routes, server
from api.candle_manager import CandleStateManager
from engine import data_mode
from engine.market_data_feed import BitstampTradeFeed


def _feed(**kwargs):
    return BitstampTradeFeed(
        candle_manager=CandleStateManager(interval_seconds=60),
        **kwargs,
    )


def _patch_lifespan_dependencies(monkeypatch):
    monkeypatch.setattr(server, "verify_scientific_contract", lambda: None)
    monkeypatch.setattr(
        server,
        "evaluate_runtime_readiness",
        lambda force_refresh: {"status": "BLOCKED"},
    )
    monkeypatch.setattr(server, "is_production_authorized", lambda readiness: False)
    monkeypatch.setattr(server, "get_shared_client", lambda: object())
    monkeypatch.setattr(server.feature_cache, "initialize", lambda: None)

    async def close_client():
        return None

    monkeypatch.setattr(server, "close_shared_client", close_client)


def test_feed_start_is_denied_by_authoritative_network_policy(monkeypatch):
    monkeypatch.setattr(data_mode, "is_external_network_permitted", lambda: False)
    feed = _feed()

    assert feed.start() is False
    snapshot = feed.snapshot()
    assert snapshot["status"] == "DATA_UNAVAILABLE"
    assert snapshot["feed_state"] == "NETWORK_BLOCKED"
    assert "authoritative data-mode policy" in snapshot["reason"]
    assert feed._thread is None


def test_permitted_start_uses_mock_worker_without_transport(monkeypatch):
    monkeypatch.setattr(data_mode, "is_external_network_permitted", lambda: True)
    feed = _feed()
    worker_started = threading.Event()
    worker_release = threading.Event()

    def deterministic_worker():
        worker_started.set()
        worker_release.wait(timeout=2)

    feed._run_event_loop = deterministic_worker
    assert feed.start() is True
    assert worker_started.wait(timeout=1)
    worker_release.set()
    assert feed.stop(timeout=1) is True


def test_same_instance_start_is_idempotent_and_other_worker_is_blocked(monkeypatch):
    monkeypatch.setattr(data_mode, "is_external_network_permitted", lambda: True)
    feed = _feed()
    second_feed = _feed()
    worker_release = threading.Event()
    worker_started = threading.Event()

    def deterministic_worker():
        worker_started.set()
        worker_release.wait(timeout=2)

    feed._run_event_loop = deterministic_worker
    second_feed._run_event_loop = deterministic_worker
    assert feed.start() is True
    assert worker_started.wait(timeout=1)
    worker_thread = feed._thread

    assert feed.start() is True
    assert feed._thread is worker_thread
    assert second_feed.start() is False
    assert second_feed.snapshot()["feed_state"] == "DUPLICATE_WORKER_BLOCKED"
    worker_release.set()
    assert feed.stop(timeout=1) is True


def test_normal_lifespan_without_permission_exposes_unavailable_api_status(monkeypatch):
    _patch_lifespan_dependencies(monkeypatch)
    monkeypatch.setattr(data_mode, "is_external_network_permitted", lambda: False)
    app = FastAPI(lifespan=server.lifespan)
    app.include_router(market_monitor_routes.router)

    with TestClient(app) as client:
        body = client.get(
            "/api/market/candles?symbol=BTC-USD&interval=1m"
        ).json()

    assert body["status"] == "DATA_UNAVAILABLE"
    assert body["feed_state"] == "NETWORK_BLOCKED"
    assert "denied by the authoritative data-mode policy" in body["reason"]
    assert body["candles"] == []


def test_lifespan_does_not_start_injected_feed_when_permission_is_denied(monkeypatch):
    _patch_lifespan_dependencies(monkeypatch)
    monkeypatch.setattr(data_mode, "is_external_network_permitted", lambda: False)

    class InjectedFeed:
        def __init__(self):
            self.start_calls = 0

        def start(self):
            self.start_calls += 1
            return True

        def stop(self):
            return True

    injected_feed = InjectedFeed()
    app = FastAPI(lifespan=server.lifespan)
    app.state.bitstamp_trade_feed = injected_feed
    app.include_router(market_monitor_routes.router)

    with TestClient(app) as client:
        body = client.get(
            "/api/market/candles?symbol=BTC-USD&interval=1m"
        ).json()

    assert injected_feed.start_calls == 0
    assert body["status"] == "DATA_UNAVAILABLE"
    assert body["feed_state"] == "NETWORK_BLOCKED"
    assert body["candles"] == []


def test_failed_connection_remains_mocked_and_preserves_reconnect_state(monkeypatch):
    import websockets

    monkeypatch.setattr(data_mode, "is_external_network_permitted", lambda: True)

    class FailingConnection:
        async def __aenter__(self):
            raise ConnectionError("deterministic mocked connection failure")

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    connect_calls = []

    def mocked_connect(*args, **kwargs):
        connect_calls.append((args, kwargs))
        return FailingConnection()

    monkeypatch.setattr(websockets, "connect", mocked_connect)
    feed = _feed(max_reconnect_delay_seconds=0.01)

    assert feed.start() is True
    deadline = time.monotonic() + 1
    while feed.snapshot()["reconnect_count"] == 0 and time.monotonic() < deadline:
        time.sleep(0.005)

    assert connect_calls
    assert feed.snapshot()["reconnect_count"] >= 1
    assert "deterministic mocked connection failure" in feed.snapshot()["last_error"]
    assert feed.stop(timeout=1) is True


def test_shutdown_timeout_is_reported_by_feed_and_lifespan(monkeypatch, caplog):
    monkeypatch.setattr(data_mode, "is_external_network_permitted", lambda: True)
    feed = _feed()
    worker_release = threading.Event()
    worker_started = threading.Event()

    def unresponsive_worker():
        worker_started.set()
        worker_release.wait(timeout=2)

    feed._run_event_loop = unresponsive_worker
    assert feed.start() is True
    assert worker_started.wait(timeout=1)
    assert feed.stop(timeout=0.01) is False
    assert feed.snapshot()["feed_state"] == "SHUTDOWN_TIMEOUT"
    worker_release.set()
    assert feed.stop(timeout=1) is True

    class TimedOutInjectedFeed:
        def start(self):
            return True

        def stop(self):
            return False

        def snapshot(self):
            return {"feed_state": "SHUTDOWN_TIMEOUT"}

    _patch_lifespan_dependencies(monkeypatch)
    app = FastAPI(lifespan=server.lifespan)
    app.state.bitstamp_trade_feed = TimedOutInjectedFeed()
    caplog.set_level(logging.WARNING, logger="btcognitive.server")

    with TestClient(app):
        pass

    assert any(
        "did not terminate before its shutdown timeout" in record.message
        for record in caplog.records
    )
