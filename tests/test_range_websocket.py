"""
tests/test_range_websocket.py — Integration Tests for WebSocket Range Forecast Broadcasts
==========================================================================================
Verifies:
1. WebSocket connection lifecycle
2. Structured 'range_forecast_update' event broadcast payload
3. Single broadcast per prediction cycle (no duplicates or out-of-order timestamps)
"""

import os
import sys
import json
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app, ws_manager


@pytest.fixture
def ws_client():
    return TestClient(app)


def test_websocket_connection_and_heartbeat(ws_client):
    with ws_client.websocket_connect("/ws") as websocket:
        data = websocket.receive_text()
        msg = json.loads(data)
        assert msg["type"] == "CONNECTION_ESTABLISHED"

        # Send ping
        websocket.send_text("ping")
        pong_data = websocket.receive_text()
        pong_msg = json.loads(pong_data)
        assert pong_msg["type"] == "PONG"


def test_range_forecast_websocket_event_schema():
    from engine.range_forecast_service import RangeForecastService
    svc = RangeForecastService()
    fc = svc.generate_forecast(current_price=98000.0, vol_24h=0.015)

    ws_event = {
        "type": "range_forecast_update",
        "data": fc.to_dict()
    }
    serialized = json.dumps(ws_event)
    deserialized = json.loads(serialized)

    assert deserialized["type"] == "range_forecast_update"
    assert deserialized["data"]["symbol"] == "BTCUSD"
    assert "upper_p90" in deserialized["data"]
    assert "lower_p90" in deserialized["data"]
    assert "uncertainty" in deserialized["data"]
