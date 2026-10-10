"""
tests/test_terminal_routes.py — Unit Tests for Terminal & Observatory Routes
=============================================================================
Verifies that /api/terminal/live, /api/observatory/summary, and /api/observatory/history
return valid schemas and correct answers to the 4 foundational decision questions.
"""

import pytest
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)


def test_server_startup_rejects_unverifiable_frozen_inputs():
    with pytest.raises(RuntimeError, match="Full scientific freeze verification failed"):
        with TestClient(app):
            pass


@pytest.mark.parametrize(
    ("state", "code"),
    [
        ("PROVENANCE_FAILURE", "FROZEN_INPUT_HASH_MISMATCH"),
        ("DATA_UNAVAILABLE", "FROZEN_INPUT_MISSING"),
        ("MODEL_FAILURE", "FROZEN_MODEL_OR_RUNTIME_INVALID"),
    ],
)
def test_terminal_live_endpoint_fails_closed_without_verified_forecast(monkeypatch, state, code):
    import api.routes_terminal as terminal_routes

    monkeypatch.setattr(terminal_routes, "_init_live_terminal", lambda: None)
    monkeypatch.setattr(terminal_routes, "_pipeline", None)
    monkeypatch.setattr(terminal_routes, "_initialization_failure", {
        "state": state,
        "code": code,
    })

    response = client.get("/api/terminal/live")
    assert response.status_code == 503
    assert response.json()["detail"] == {
        "status": "UNAVAILABLE",
        "state": state,
        "code": code,
        "forecast": None,
    }


def test_observatory_summary_endpoint():
    response = client.get("/api/observatory/summary")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "total_resolved_forecasts" in data
    assert "pending_unresolved_forecasts" in data


def test_observatory_history_endpoint():
    response = client.get("/api/observatory/history?limit=10")
    assert response.status_code == 200
    records = response.json()
    assert isinstance(records, list)
    if records:
        rec = records[0]
        assert "forecast_id" in rec
        assert "forecast_hash" in rec
        assert "lifecycle_state" in rec
