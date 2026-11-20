"""
tests/test_isolated_real_http_server.py — Isolated Real HTTP Integration Test
=============================================================================
Verifies FastAPI routing, serialization, and fail-closed error handling over a true
TCP loopback socket using a dynamically selected ephemeral port on 127.0.0.1.

Governance & Safety Invariants:
1. Spawns an isolated test uvicorn server in a separate background thread with dedicated asyncio event loop.
2. Dynamically binds to an ephemeral OS-assigned port to prevent collisions with port 8000.
3. Tests real HTTP requests via urllib.request (zero mocks on network transport layer).
4. Strictly shuts down only the server created by this test in a finally fixture block.
5. Verifies zero live trading capability and fail-closed Smart Entry responses.
"""

import time
import socket
import threading
import json
import asyncio
import urllib.request
import urllib.error
import pytest
import uvicorn

from api.server import app


def get_ephemeral_port() -> int:
    """Finds an available ephemeral port on loopback."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class EphemeralUvicornServer:
    """Manages an in-process Uvicorn server running in a background daemon thread."""

    def __init__(self, port: int):
        self.port = port
        self.loop = asyncio.new_event_loop()
        self.config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning"
        )
        self.server = uvicorn.Server(self.config)
        self.thread = threading.Thread(target=self._run_server, daemon=True)

    def _run_server(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.server.serve())

    def start(self):
        self.thread.start()
        deadline = time.monotonic() + 120.0
        url = f"http://127.0.0.1:{self.port}/api/health"
        try:
            while not self.server.started:
                if not self.thread.is_alive():
                    raise RuntimeError(
                        f"Ephemeral Uvicorn server exited before startup on port {self.port}"
                    )
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"Ephemeral Uvicorn server did not start on port {self.port} within 120s"
                    )
                time.sleep(0.1)
            with urllib.request.urlopen(url, timeout=5.0) as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        f"Ephemeral Uvicorn server returned HTTP {resp.status} on {url}"
                    )
        except Exception:
            self.stop()
            raise

    def stop(self):
        self.server.should_exit = True
        if self.thread.ident is None:
            return
        self.thread.join(timeout=10.0)
        if self.thread.is_alive():
            raise RuntimeError(f"Ephemeral Uvicorn server on port {self.port} did not stop")


@pytest.fixture(scope="module")
def isolated_server():
    """Starts an ephemeral Uvicorn server and ensures guaranteed cleanup."""
    port = get_ephemeral_port()
    server = EphemeralUvicornServer(port)
    server.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.stop()


def test_real_http_health_check(isolated_server):
    """Verifies that the isolated real HTTP server responds with 200 on /api/health."""
    url = f"{isolated_server}/api/health"
    req = urllib.request.Request(url, headers={"User-Agent": "BTCognitive-QA/1.0"})
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "status" in data
        assert data.get("live_trading_enabled") is False
        assert data.get("order_submission_enabled") is False


def test_real_http_smart_entry_pipeline_post(isolated_server):
    """
    Verifies that POST /api/research/smart-entry/pipeline processes a real HTTP request
    and returns a complete fail-closed PipelineExecutionReport.
    """
    url = f"{isolated_server}/api/research/smart-entry/pipeline"
    payload = {
        "strategy_id": "TSMOM_DONCHIAN_24H_168H",
        "instrument": "BTC-USD",
        "venue": "COINBASE",
        "timeframe": "1h",
        "assumed_cost_scenario": "COINBASE_RETAIL_87BPS"
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "BTCognitive-QA/1.0"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "pipeline_id" in data
        assert data["final_action"] == "ABSTAIN"
        assert data["live_trading"] == "DISABLED"
        assert data["governance_status"] == "OFFLINE_RESEARCH_ONLY"
        assert "stage1_data_validation" in data
        assert "stage5_smart_entry_gate" in data


def test_real_http_smart_entry_pipeline_latest_get(isolated_server):
    """
    Verifies that GET /api/research/smart-entry/pipeline/latest evaluates over real HTTP
    and returns a valid fail-closed JSON payload.
    """
    url = f"{isolated_server}/api/research/smart-entry/pipeline/latest?strategy_id=TSMOM_DONCHIAN_24H_168H&assumed_cost_scenario=COINBASE_ACTIVE_27BPS"
    req = urllib.request.Request(url, headers={"User-Agent": "BTCognitive-QA/1.0"})
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["final_action"] == "ABSTAIN"
        assert data["live_trading"] == "DISABLED"


def test_real_http_smart_entry_pipeline_validation_error(isolated_server):
    """
    Verifies that an invalid request schema yields 422 Unprocessable Entity over real HTTP.
    """
    url = f"{isolated_server}/api/research/smart-entry/pipeline"
    # Send malformed payload violating Pydantic schema
    payload = {"candles": "invalid_not_a_list"}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "BTCognitive-QA/1.0"
        },
        method="POST"
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=3.0)
    assert exc_info.value.code == 422
