import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import market_monitor_routes, server
from engine import data_mode
from api.candle_manager import CandleStateManager
from engine.market_data_feed import BitstampTradeFeed


class _DeterministicFixtureFeed(BitstampTradeFeed):
    """Local-only Bitstamp-shaped fixture; start never opens a provider connection."""

    def __init__(self):
        super().__init__(candle_manager=CandleStateManager(interval_seconds=60))
        self.started = False
        self.stopped = False
        self.network_attempts = 0
        self.forced_status = None
        self.visible_candle_limit = None
        self.invalidate_latest_candle = False
        self.mark_latest_provisional = False
        self.break_candle_sequence = False

    def start(self):
        self.started = True
        self._connected = True
        self._ever_connected = True
        self._feed_state = "CONNECTED"
        now = time.time()
        current_minute = int(now // 60) * 60
        latest_closed_minute = current_minute - 60
        for index in range(20):
            minute = latest_closed_minute - (19 - index) * 60
            event_time = datetime.fromtimestamp(
                minute + 59.5, timezone.utc
            )
            microtimestamp = int(event_time.timestamp() * 1_000_000)
            trade = {
                "event": "trade",
                "channel": self.CHANNEL,
                "data": {
                    "id": 930_000 + index,
                    "timestamp": str(microtimestamp // 1_000_000),
                    "microtimestamp": str(microtimestamp),
                    "price": str(68_000.0 + index),
                    "amount": "0.025",
                    "type": 0,
                },
            }
            observation = self._handle_raw_message(
                json.dumps(trade),
                received_at=datetime.now(timezone.utc),
            )
            if observation is None:
                raise AssertionError("A deterministic local test trade was rejected.")
        return True

    def stop(self):
        self.stopped = True
        self._connected = False
        self._feed_state = "DISCONNECTED"
        return True

    def snapshot(self, limit=500):
        result = super().snapshot(limit)
        result["test_only"] = True
        result["data_origin"] = "TEST_FIXTURE_ONLY"
        if self.forced_status is not None:
            result["status"] = self.forced_status
        if self.visible_candle_limit is not None:
            result["candles"] = result["candles"][-self.visible_candle_limit:]
        if self.invalidate_latest_candle and result["candles"]:
            result["candles"][-1]["quality_status"] = "INVALID"
        if self.mark_latest_provisional and result["candles"]:
            result["candles"][-1]["is_closed"] = False
        if self.break_candle_sequence and len(result["candles"]) >= 20:
            result["candles"][10]["time"] += 30
        return result


def _app():
    app = FastAPI(lifespan=server.lifespan)
    app.include_router(market_monitor_routes.router)
    return app


def _patch_local_lifespan(monkeypatch, app, network_permitted):
    monkeypatch.setattr(server, "verify_scientific_contract", lambda: None)
    monkeypatch.setattr(
        server, "evaluate_runtime_readiness", lambda force_refresh: {"status": "BLOCKED"}
    )
    monkeypatch.setattr(server, "is_production_authorized", lambda readiness: False)
    monkeypatch.setattr(server, "get_shared_client", lambda: object())
    monkeypatch.setattr(server.feature_cache, "initialize", lambda: None)

    async def close_client():
        return None

    monkeypatch.setattr(server, "close_shared_client", close_client)
    # The lifespan may import the policy locally or expose it as a module alias.
    monkeypatch.setattr(data_mode, "is_external_network_permitted", lambda: network_permitted)
    if hasattr(server, "is_external_network_permitted"):
        monkeypatch.setattr(
            server, "is_external_network_permitted", lambda: network_permitted
        )


def _exercise_existing_frontend(api_body):
    node = shutil.which("node")
    assert node is not None, "Node.js is required to exercise the existing frontend chart."
    app_js = Path(__file__).resolve().parents[1] / "web" / "app.js"
    script = r"""
const fs = require("fs");
const vm = require("vm");
const app = fs.readFileSync(process.argv[1], "utf8");
const apiBody = JSON.parse(fs.readFileSync(0, "utf8"));
const hookStart = app.indexOf("function useMarketCandleFeed(");
const hookEnd = app.indexOf("// LightweightCandleChart component", hookStart);
const badgeStart = app.indexOf("function LiveBadge(");
const chartStart = app.indexOf("function ChartTopBar(", badgeStart);
const chartEnd = app.indexOf("// Navbar", chartStart);
if ([hookStart, hookEnd, badgeStart, chartStart, chartEnd].some(index => index < 0)) {
  throw new Error("The existing market-feed hook or chart component could not be located.");
}

const state = [];
const refs = [];
let stateIndex = 0;
let refIndex = 0;
let renderCount = 0;
let requestedUrl = null;
function h(type, props, ...children) {
  return { type, props: props || {}, children: children.flat(Infinity) };
}
const context = {
  useState(initial) {
    const index = stateIndex++;
    if (!(index in state)) state[index] = typeof initial === "function" ? initial() : initial;
    return [state[index], value => {
      state[index] = typeof value === "function" ? value(state[index]) : value;
    }];
  },
  useRef(initial) {
    const index = refIndex++;
    if (!(index in refs)) refs[index] = { current: initial };
    return refs[index];
  },
  useCallback(callback) { return callback; },
  useEffect(effect) { if (renderCount === 0) effect(); },
  h,
  formatCandleCountdown(seconds) {
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  },
  INTERVAL_MAP: { "1m": "1m", "5m": "5m", "15m": "15m", "1H": "1h", "4H": "4h", "1D": "1d" },
  INTERVAL_STEP: { "1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400 },
  getApiBaseUrl: () => "http://local-fastapi-fixture",
  fetch: async url => {
    requestedUrl = url;
    return { ok: true, status: 200, json: async () => apiBody };
  },
  AbortController,
  setTimeout: () => 1,
  clearTimeout: () => {},
  setInterval: () => 1,
  clearInterval: () => {},
  performance,
  Date,
  console
};
vm.createContext(context);
vm.runInContext(
  app.slice(hookStart, hookEnd) + "\n" +
  app.slice(badgeStart, chartEnd),
  context
);

async function main() {
  context.useMarketCandleFeed("1m");
  await new Promise(resolve => setImmediate(resolve));
  stateIndex = 0;
  refIndex = 0;
  renderCount = 1;
  const market = context.useMarketCandleFeed("1m");
  if (!requestedUrl.includes("interval=1m")) throw new Error(`Wrong request interval: ${requestedUrl}`);
  if (market.wsStatus !== "ACTIVE" || market.historyStatus !== "ready") {
    throw new Error(`API status not passed to chart: ${market.wsStatus}/${market.historyStatus}`);
  }
  if (market.historySource !== "bitstamp" || market.historyTestOnly !== true) {
    throw new Error("The chart lost the Bitstamp source or test-only marker.");
  }
  if (market.historyEventTimestamp !== apiBody.last_event_timestamp ||
      market.historyReceiptTimestamp !== apiBody.last_receive_timestamp) {
    throw new Error("The chart hook did not retain the API event and receipt timestamps.");
  }
  const last = market.seedCandles[market.seedCandles.length - 1];
  if (market.seedCandles.length !== 20 || last.close !== apiBody.candles[19].close ||
      market.exchangeClock?.timestampMs !== Date.parse(apiBody.last_receive_timestamp)) {
    throw new Error("The actual API candle or receipt time did not reach the chart hook.");
  }
  const tree = context.ChartTopBar({
    wsStatus: market.wsStatus,
    activeInterval: "1m",
    livePrice: market.livePrice,
    latestCandleTime: last.time,
    exchangeClock: market.exchangeClock,
    chartCandleSnapshot: {
      source: market.historySource,
      status: market.historyStatus,
      freshnessStatus: market.historyFreshness,
      testOnly: market.historyTestOnly,
      eventTimestamp: market.historyEventTimestamp,
      receiptTimestamp: market.historyReceiptTimestamp,
      candles: market.seedCandles
    }
  });
  function text(node) {
    if (node == null || node === false || node === true) return "";
    if (Array.isArray(node)) return node.map(text).join("");
    if (typeof node === "string" || typeof node === "number") return String(node);
    if (typeof node.type === "function") return text(node.type(node.props));
    return (node.children || []).map(text).join("");
  }
  const displayed = text(tree);
  if (!displayed.includes("LOCAL TEST FIXTURE ONLY — NOT MARKET DATA")) {
    throw new Error("The chart did not label the local fixture as test-only.");
  }
  if (!displayed.includes("Local test fixture timestamp:") ||
      displayed.includes("Bitstamp observation:") ||
      displayed.includes("Coinbase quote:")) {
    throw new Error("The fixture timestamp was misattributed as a provider observation.");
  }
}

main().catch(error => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
"""
    result = subprocess.run(
        [node, "-e", script, str(app_js)],
        input=json.dumps(api_body),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_fixture_lifespan_without_opt_in_is_unavailable(monkeypatch):
    app = _app()

    with monkeypatch.context() as patch:
        _patch_local_lifespan(patch, app, network_permitted=False)
        with TestClient(app) as client:
            response = client.get(
                "/api/market/candles?symbol=BTC-USD&interval=1m&limit=500"
            )
            assert response.status_code == 200
            body = response.json()

            assert client.get("/api/health").status_code == 200
            assert client.get("/api/readiness").status_code == 200
            assert body["status"] == "DATA_UNAVAILABLE"
            assert body["freshness_status"] == "UNAVAILABLE"
            assert body["count"] == 0
            assert body["candles"] == []
            assert app.state.bitstamp_trade_feed is None
            assert app.state.local_fixture_feed_enabled is False
            assert app.state.local_fixture_feed is None


def test_normal_lifespan_without_network_permission_is_unavailable(monkeypatch):
    app = _app()
    app.state.bitstamp_trade_feed = None

    with monkeypatch.context() as patch:
        _patch_local_lifespan(patch, app, network_permitted=False)
        with TestClient(app) as client:
            response = client.get(
                "/api/market/candles?symbol=BTC-USD&interval=1m&limit=20"
            )
            body = response.json()
            assert response.status_code == 200
            assert body["status"] == "DATA_UNAVAILABLE"
            assert body["freshness_status"] == "UNAVAILABLE"
            assert body["count"] == 0
            assert body["candles"] == []
            blocked_feed = app.state.bitstamp_trade_feed
            assert blocked_feed is None
            assert client.get("/api/health").status_code == 200
            assert client.get("/api/readiness").status_code == 200


def test_opt_in_local_fixture_feed_is_in_memory_only_and_unvalidated(monkeypatch):
    import builtins
    import os
    import socket
    import sqlite3
    import urllib.request

    import pandas as pd

    from engine.data_mode import LOCAL_FIXTURE_LABEL, is_external_network_permitted

    monkeypatch.setenv("DATA_MODE", "fixture")
    monkeypatch.setenv("BTC_DATA_MODE", "fixture")
    monkeypatch.setenv("BTC_LOCAL_FIXTURE_FEED", "1")
    attempts = []
    original_connect = sqlite3.connect
    original_open = builtins.open
    original_socket_connect = socket.socket.connect
    original_socket_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def guarded_connect(database, *args, **kwargs):
        name = os.fsdecode(os.fspath(database))
        if name == ":memory:" or name.startswith("file::memory:") or "mode=memory" in name:
            return original_connect(database, *args, **kwargs)
        attempts.append(("persistent SQLite", name))
        raise AssertionError(f"unexpected persistent SQLite connection: {name}")

    def blocked(kind):
        def reject(*args, **kwargs):
            attempts.append(kind)
            raise AssertionError(f"unexpected {kind}")
        return reject

    def is_loopback(address):
        return isinstance(address, tuple) and address and str(address[0]).lower() in {
            "localhost", "127.0.0.1", "::1",
        }

    def guarded_socket_connect(sock, address):
        if is_loopback(address):
            return original_socket_connect(sock, address)
        attempts.append(("external socket connect", address))
        raise AssertionError(f"unexpected external socket: {address!r}")

    def guarded_socket_connect_ex(sock, address):
        if is_loopback(address):
            return original_socket_connect_ex(sock, address)
        attempts.append(("external socket connect_ex", address))
        raise AssertionError(f"unexpected external socket: {address!r}")

    def guarded_create_connection(address, *args, **kwargs):
        if is_loopback(address):
            return original_create_connection(address, *args, **kwargs)
        attempts.append(("external create_connection", address))
        raise AssertionError(f"unexpected external connection: {address!r}")

    def guarded_getaddrinfo(host, *args, **kwargs):
        if str(host).lower() in {"localhost", "127.0.0.1", "::1"}:
            return original_getaddrinfo(host, *args, **kwargs)
        attempts.append(("external DNS lookup", host))
        raise AssertionError(f"unexpected external DNS lookup: {host!r}")

    def guarded_open(file, *args, **kwargs):
        path = os.path.normcase(os.path.abspath(os.fsdecode(os.fspath(file))))
        protected_parts = (
            os.path.normcase(os.path.join("data", "raw")),
            os.path.normcase(os.path.join("data", "research")),
            os.path.normcase(os.path.join("experiments", "results")),
            os.path.normcase("checkpoints"),
        )
        if any(part in path for part in protected_parts):
            attempts.append(("protected file access", path))
            raise AssertionError(f"unexpected protected file access: {path}")
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", guarded_connect)
    monkeypatch.setattr(pd, "read_parquet", blocked("Parquet read"))
    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(socket.socket, "connect", guarded_socket_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_socket_connect_ex)
    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(urllib.request, "urlopen", blocked("urllib request"))

    from api.server import app

    assert is_external_network_permitted() is False
    with TestClient(app) as client:
        health_response = client.get("/api/health")
        readiness_response = client.get("/api/readiness")
        fixture_response = client.get(
            "/api/local-fixture/candles?symbol=BTC-USD&interval=1m&limit=500"
        )
        standard_response = client.get(
            "/api/market/candles?symbol=BTC-USD&interval=1m&limit=500"
        )

        assert health_response.status_code == 200
        health = health_response.json()
        assert health["system_status"]["data_mode"] == "fixture"
        assert health["system_status"]["local_fixture_feed_enabled"] is True
        assert health["system_status"]["data_mode_contract"]["external_network_allowed"] is False
        assert health["system_status"]["canonical_model_id"] is None

        assert readiness_response.status_code == 200
        readiness = readiness_response.json()
        assert readiness["status"] == "BLOCKED"
        assert readiness["reason_code"] == "FIXTURE_MODE_DATA_UNAVAILABLE"
        assert readiness["canonical_model_id"] is None
        assert readiness["model_version"] is None

        assert fixture_response.status_code == 200
        fixture = fixture_response.json()
        assert fixture["status"] == "FIXTURE_ONLY"
        assert fixture["freshness_status"] == "NOT_APPLICABLE"
        assert fixture["source"] == "fixture"
        assert fixture["test_only"] is True
        assert fixture["data_origin"] == "TEST_FIXTURE_ONLY"
        assert fixture["label"] == LOCAL_FIXTURE_LABEL
        assert fixture["label"] == "LOCAL TEST FIXTURE ONLY — NOT MARKET DATA"
        assert fixture["count"] == 20
        assert fixture["candles"][0]["time"] == 1_704_067_200
        assert fixture["candles"][0]["open"] == 100.0
        assert fixture["candles"][-1]["close"] == 119.25
        assert all(candle["source"] == "fixture" for candle in fixture["candles"])
        assert all(candle["test_only"] is True for candle in fixture["candles"])
        assert fixture["analysis"]["status"] == "UNVALIDATED"
        assert fixture["analysis"]["engine_invoked"] is False

        assert standard_response.status_code == 200
        standard = standard_response.json()
        assert standard["status"] == "DATA_UNAVAILABLE"
        assert standard["count"] == 0
        assert app.state.bitstamp_trade_feed is None
        assert app.state.local_fixture_feed_enabled is True

    assert attempts == []
