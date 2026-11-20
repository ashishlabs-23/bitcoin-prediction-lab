from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api import routes_manual_journal as journal_routes
from api import routes_user_positions as position_routes
from api.server import app
from api.security_auth import API_KEYS_ENV, get_current_principal_id
from config.security import UserRole
from engine.manual_trade_journal import ManualTradeJournal, _compute_dict_sha256
from engine.user_position_tracker import UserPositionTracker


@pytest.fixture
def isolated_routes(tmp_path, monkeypatch):
    tracker = UserPositionTracker(base_dir=str(tmp_path / "positions"))
    journal = ManualTradeJournal(base_dir=str(tmp_path / "journal"))
    monkeypatch.setattr(position_routes, "_tracker", tracker)
    monkeypatch.setattr(journal_routes, "_journal", journal)
    previous = app.dependency_overrides.get(get_current_principal_id)
    app.dependency_overrides[get_current_principal_id] = lambda: "owner-a"

    async def unavailable_quote(request):
        return {
            "status": "UNAVAILABLE",
            "price": None,
            "bid": None,
            "ask": None,
            "is_live": False,
        }

    monkeypatch.setattr(position_routes, "_get_current_market_quote", unavailable_quote)
    try:
        yield TestClient(app), tracker, journal
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal_id, None)
        else:
            app.dependency_overrides[get_current_principal_id] = previous


def _record_position(tracker, position_id, user_id):
    position, error = tracker.record_open_position(
        position_id=position_id,
        instrument="BTC-USD",
        side="LONG",
        entry_price=80_000.0,
        quantity=0.1,
        entry_timestamp_utc="2026-11-04T00:00:00Z",
        user_id=user_id,
    )
    assert error is None
    return position


def _record_trade(journal, trade_id, user_id):
    trade, error = journal.record_entry(
        instrument="BTC-USD",
        direction="LONG",
        entry_price=80_000.0,
        quantity=0.1,
        entry_timestamp_utc="2026-11-04T00:00:00Z",
        user_id=user_id,
        trade_id=trade_id,
        pre_captured_snapshot={
            "forecast_status": "UNAVAILABLE_TEST_FIXTURE",
            "probability_up": None,
            "probability_down": None,
            "predicted_direction": "UNAVAILABLE",
            "regime_classification": "UNKNOWN",
            "horizons": {},
        },
    )
    assert error is None
    return trade


def test_missing_identity_provider_fails_closed_for_positions_and_journal(monkeypatch):
    monkeypatch.setitem(API_KEYS_ENV, "v37-3-test-user-key", UserRole.USER)
    previous = app.dependency_overrides.get(get_current_principal_id)
    app.dependency_overrides.pop(get_current_principal_id, None)
    try:
        client = TestClient(app)
        headers = {"X-API-Key": "v37-3-test-user-key"}
        positions = client.get("/api/positions", headers=headers)
        journal = client.get("/api/journal/trades", headers=headers)
    finally:
        if previous is not None:
            app.dependency_overrides[get_current_principal_id] = previous
    assert positions.status_code == 503
    assert journal.status_code == 503
    assert "identity provider is not configured" in positions.json()["detail"]
    assert "identity provider is not configured" in journal.json()["detail"]


def test_position_reads_and_mutations_are_scoped_to_authenticated_owner(isolated_routes):
    client, tracker, _ = isolated_routes
    _record_position(tracker, "owner-a-position", "owner-a")
    _record_position(tracker, "owner-b-position", "owner-b")

    listed = client.get("/api/positions")
    assert listed.status_code == 200
    assert [row["position"]["position_id"] for row in listed.json()["positions"]] == [
        "owner-a-position"
    ]
    assert client.get("/api/positions?user_id=owner-b").status_code == 403
    assert client.get("/api/positions/owner-b-position").status_code == 404
    assert client.post(
        "/api/positions/owner-b-position/close",
        json={"exit_price": 81_000.0},
    ).status_code == 404
    assert tracker.get_position("owner-b-position").status == "OPEN"

    spoofed_open = client.post(
        "/api/positions/open",
        json={
            "user_id": "owner-b",
            "instrument": "BTC-USD",
            "entry_price": 80_000.0,
            "quantity": 0.1,
        },
    )
    assert spoofed_open.status_code == 403
    assert tracker.get_open_positions(user_id="owner-b") == [
        tracker.get_position("owner-b-position")
    ]


def test_journal_reads_and_mutations_are_scoped_to_authenticated_owner(isolated_routes):
    client, _, journal = isolated_routes
    _record_trade(journal, "owner-a-trade", "owner-a")
    _record_trade(journal, "owner-b-trade", "owner-b")

    listed = client.get("/api/journal/trades")
    assert listed.status_code == 200
    assert [trade["trade_id"] for trade in listed.json()["open_trades"]] == [
        "owner-a-trade"
    ]
    assert client.get("/api/journal/trades?user_id=owner-b").status_code == 403
    assert client.get("/api/journal/trades/owner-b-trade").status_code == 404
    assert client.post(
        "/api/journal/trades/owner-b-trade/exit",
        json={"exit_price": 81_000.0},
    ).status_code == 404
    assert client.post(
        "/api/journal/trades/owner-b-trade/adjust",
        json={
            "field_name": "notes",
            "new_value": "unauthorized",
            "reason": "ownership regression",
        },
    ).status_code == 404
    assert journal.get_trade("owner-b-trade").status == "OPEN"

    spoofed_open = client.post(
        "/api/journal/trades/enter",
        json={
            "user_id": "owner-b",
            "entry_price": 80_000.0,
            "quantity": 0.1,
        },
    )
    assert spoofed_open.status_code == 403
    assert journal.get_trade("owner-b-trade").status == "OPEN"


def test_manual_journal_route_does_not_store_fabricated_probabilities_or_regime(
    isolated_routes,
    monkeypatch,
    caplog,
):
    client, _, _ = isolated_routes
    monkeypatch.setattr(
        journal_routes,
        "capture_entry_forecast_snapshot",
        lambda instrument, reference_price: {
            "forecast_status": "VALID",
            "model_id": "synthetic-invalid-fixture",
            "probability_up": 0.9,
            "probability_down": 0.8,
            "predicted_direction": "UP",
            "regime_classification": "NORMAL_VOLATILITY",
            "horizons": {
                "1h": {
                    "status": "VALID",
                    "p_up": 0.9,
                    "p_down": 0.8,
                    "predicted_direction": "UP",
                }
            },
        },
    )
    class BrokenInferenceEngine:
        @property
        def latest_regime(self):
            raise RuntimeError("sensitive regime detail")

    monkeypatch.setitem(
        __import__("sys").modules,
        "engine.inference_service",
        SimpleNamespace(live_engine=BrokenInferenceEngine()),
    )
    response = client.post(
        "/api/journal/trades/enter",
        json={"entry_price": 80_000.0, "quantity": 0.1},
    )

    assert response.status_code == 200
    snapshot = response.json()["trade"]["forecast_snapshot"]
    assert snapshot["forecast_status"] == "UNAVAILABLE_INVALID_FORECAST"
    assert snapshot["probability_up"] is None
    assert snapshot["probability_down"] is None
    assert snapshot["predicted_direction"] == "UNAVAILABLE"
    assert snapshot["regime_classification"] == "UNKNOWN"
    assert snapshot["horizons"]["1h"]["p_up"] is None
    assert snapshot["horizons"]["1h"]["p_down"] is None
    assert snapshot["horizons"]["1h"]["predicted_direction"] == "UNAVAILABLE"
    assert "RuntimeError" in caplog.text
    assert "sensitive regime detail" not in caplog.text
    digest = snapshot.pop("immutable_sha256")
    assert digest == _compute_dict_sha256(snapshot)


def test_manual_journal_forecast_capture_failure_is_explicit_and_logged(
    isolated_routes,
    monkeypatch,
    caplog,
):
    client, _, _ = isolated_routes

    def failed_capture(instrument, reference_price):
        raise RuntimeError("sensitive provider detail")

    monkeypatch.setattr(
        journal_routes, "capture_entry_forecast_snapshot", failed_capture
    )
    response = client.post(
        "/api/journal/trades/enter",
        json={"entry_price": 80_000.0, "quantity": 0.1},
    )

    assert response.status_code == 200
    snapshot = response.json()["trade"]["forecast_snapshot"]
    assert snapshot["forecast_status"] == "UNAVAILABLE_CAPTURE_ERROR"
    assert snapshot["probability_up"] is None
    assert snapshot["probability_down"] is None
    assert snapshot["predicted_direction"] == "UNAVAILABLE"
    assert snapshot["regime_classification"] == "UNKNOWN"
    assert "RuntimeError" in caplog.text
    assert "sensitive provider detail" not in caplog.text
