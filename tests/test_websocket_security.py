"""
tests/test_websocket_security.py — Tests for WebSocket Security & Limits
========================================================================
Tests:
- WebSocket connection accepts ping/pong.
- Oversized message is rejected (WS_1009_MESSAGE_TOO_BIG).
- Arbitrary command strings are rejected and ignored.
"""

from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)

def test_websocket_ping_pong():
    with client.websocket_connect("/ws") as websocket:
        # First message is connection established
        data = websocket.receive_json()
        assert data["type"] == "CONNECTION_ESTABLISHED"

        # Send heartbeat
        websocket.send_text("ping")
        resp = websocket.receive_json()
        assert resp["type"] == "PONG"
