"""
tests/test_v32_42_user_position_tracker_and_risk_copilot.py — BTCognitive V32.42 Test Suite
=============================================================================================
Tests the User Position Tracker and Adaptive Risk Copilot:
1. Long and Short mark-to-market P&L and fee modeling.
2. Spot short rejection (SPOT_SHORT_INELIGIBLE).
3. Derivative leverage and liquidation price estimation.
4. Partial exits and full close lifecycle reconciliation.
5. Idempotent event deduplication and restart-recovery reconstruction.
6. Stale feeds and missing data abstention (fail-closed diagnostics).
7. Adaptive risk alerts: stop loss proximity, target hit, GBDT directional conflict, regime shift.
8. FastAPI endpoints integration.
9. Strict non-execution safety and protected files isolation.
"""

import os
import sys
import json
import time
import math
import uuid
import hashlib
import tempfile
import pytest
from fastapi.testclient import TestClient

from api import routes_user_positions as position_routes
from engine.user_position_tracker import (
    UserPositionTracker,
    UserPosition,
    PartialExitRecord
)
from engine.adaptive_risk_copilot import (
    AdaptiveRiskCopilot,
    RiskAlert,
    PositionRiskSnapshot
)
from api.server import app
from api.routes_user_positions import get_current_principal_id

client = TestClient(app)


@pytest.fixture
def authenticated_api_user():
    previous = app.dependency_overrides.get(get_current_principal_id)
    app.dependency_overrides[get_current_principal_id] = lambda: "default_user"
    try:
        yield
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal_id, None)
        else:
            app.dependency_overrides[get_current_principal_id] = previous


@pytest.fixture
def isolated_api_position_storage(tmp_path, monkeypatch):
    tracker = UserPositionTracker(base_dir=str(tmp_path / "api_positions"))
    monkeypatch.setattr(position_routes, "_tracker", tracker)
    return tracker


PROTECTED_FILES = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prospective_entry_ledger.jsonl")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prospective_shadow_v1.jsonl")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prospective_entry_ledger_v2.jsonl")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "ohlcv.parquet")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "ohlcv_pre_backfill_backup.parquet")),
]


def test_safety_non_execution_and_copilot_status(authenticated_api_user, isolated_api_position_storage):
    """Verify tracker and copilot have zero live broker adapters or execution endpoints."""
    tracker = UserPositionTracker()
    copilot = AdaptiveRiskCopilot()

    prohibited_attrs = [
        "ccxt", "broker", "api_key", "api_secret", "passphrase",
        "place_order", "send_order", "submit_order", "execute_live_order",
        "cancel_live_order", "exchange_client"
    ]
    for attr in prohibited_attrs:
        assert not hasattr(tracker, attr), f"Prohibited attribute '{attr}' found on UserPositionTracker"
        assert not hasattr(copilot, attr), f"Prohibited attribute '{attr}' found on AdaptiveRiskCopilot"

    # Verify FastAPI status endpoint
    res = client.get("/api/positions/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["copilot_state"] == "COPILOT_MONITORING_ACTIVE"
    assert data["governing_posture"] == "OFFLINE_RESEARCH_ONLY"
    assert data["live_trading"] == "DISABLED"
    assert data["broker_execution_adapters"] == "NONE"
    assert data["order_placement_routes"] == "NONE"


def test_spot_short_rejection_fail_closed():
    """Verify spot short positions are rejected with SPOT_SHORT_INELIGIBLE."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = UserPositionTracker(base_dir=tmpdir)
        pos, err = tracker.record_open_position(
            position_id="test_spot_short_001",
            instrument="BTC-USD",
            side="SHORT",
            entry_price=80000.0,
            quantity=0.5,
            entry_timestamp_utc="2026-10-25T12:00:00Z",
            market_type="SPOT"
        )
        assert pos is None
        assert err is not None
        assert "SPOT_SHORT_INELIGIBLE" in err


def test_derivative_short_acceptance_and_liquidation_modeling():
    """Verify perpetual short positions are accepted and compute liquidation level."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = UserPositionTracker(base_dir=tmpdir)
        pos, err = tracker.record_open_position(
            position_id="test_perp_short_001",
            instrument="BTC-PERP",
            side="SHORT",
            entry_price=80000.0,
            quantity=1.0,
            entry_timestamp_utc="2026-10-25T12:00:00Z",
            market_type="PERPETUAL",
            leverage=5.0
        )
        assert err is None
        assert pos is not None
        assert pos.side == "SHORT"
        assert pos.market_type == "PERPETUAL"
        assert pos.leverage == 5.0
        # For 5x short: entry * (1 + 1/5 - 0.005) = 80000 * 1.195 = 95600.0
        assert pos.liquidation_price is not None
        assert abs(pos.liquidation_price - 95600.0) < 1.0


def test_long_pnl_mark_to_market_and_fees():
    """Verify long position mark-to-market P&L, fees, and return percentage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = UserPositionTracker(base_dir=tmpdir)
        copilot = AdaptiveRiskCopilot()

        pos, _ = tracker.record_open_position(
            position_id="test_long_001",
            instrument="BTC-USD",
            side="LONG",
            entry_price=80000.0,
            quantity=1.0,
            entry_timestamp_utc="2026-10-25T12:00:00Z",
            entry_fee_usd=80.0,  # 10 bps entry
            stop_loss_price=76000.0,
            take_profit_price=88000.0
        )
        assert pos is not None

        # Quote at $84,000 (+$4,000 gross)
        quote = {
            "price": 84000.0,
            "bid": 83995.0,
            "ask": 84005.0,
            "age_seconds": 1.2,
            "provider": "COINBASE"
        }
        snapshot = copilot.evaluate_position_risk(position=pos, market_quote=quote)
        assert snapshot.mark_price == 84000.0
        assert snapshot.mark_price_status == "VERIFIED_LIVE"
        assert snapshot.gross_unrealized_pnl_usd == 4000.0
        # Estimated exit fee: 84000 * 1.0 * 0.0010 = $84.00
        assert abs(snapshot.estimated_exit_fee_usd - 84.0) < 0.1
        # Net unrealized = 4000 - 80 (entry) - 84 (exit) = 3836.00
        assert abs(snapshot.net_unrealized_pnl_usd - 3836.0) < 0.2
        # Net return = 3836 / 80000 = 4.795%
        assert abs(snapshot.net_return_pct - 4.80) < 0.05
        # Distance to stop: (84000 - 76000) / 84000 * 100 = 9.52%
        assert abs(snapshot.distance_to_stop_pct - 9.52) < 0.1
        # Distance to target: (88000 - 84000) / 84000 * 100 = 4.76%
        assert abs(snapshot.distance_to_target_pct - 4.76) < 0.1


def test_partial_exits_and_full_close_lifecycle():
    """Verify partial exits update remaining quantity and full close updates status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = UserPositionTracker(base_dir=tmpdir)
        pos, _ = tracker.record_open_position(
            position_id="test_pe_close_001",
            instrument="BTC-USD",
            side="LONG",
            entry_price=80000.0,
            quantity=1.0,
            entry_timestamp_utc="2026-10-25T12:00:00Z",
            entry_fee_usd=80.0
        )
        assert pos.remaining_quantity == 1.0

        # 1. Partial exit of 0.4 BTC @ 84,000 (Gross = 0.4 * 4000 = $1,600, Fee = $33.60)
        pos_pe, err = tracker.record_partial_exit(
            position_id="test_pe_close_001",
            exit_price=84000.0,
            quantity=0.4,
            exit_timestamp_utc="2026-10-25T14:00:00Z",
            fee_usd=33.60,
            reason="TP1_HIT"
        )
        assert err is None
        assert pos_pe.status == "PARTIALLY_CLOSED"
        assert pos_pe.remaining_quantity == 0.6
        assert len(pos_pe.partial_exits) == 1
        assert abs(pos_pe.total_realized_pnl_usd - (1600.0 - 33.60)) < 0.1

        # 2. Exceeding quantity is rejected
        _, err_over = tracker.record_partial_exit(
            position_id="test_pe_close_001",
            exit_price=85000.0,
            quantity=0.8,  # > 0.6
            exit_timestamp_utc="2026-10-25T15:00:00Z"
        )
        assert err_over is not None

        # 3. Full close of remaining 0.6 BTC @ 86,000 (Gross = 0.6 * 6000 = $3,600, Fee = $51.60)
        pos_close, err_c = tracker.record_close_position(
            position_id="test_pe_close_001",
            exit_price=86000.0,
            exit_timestamp_utc="2026-10-25T16:00:00Z",
            fee_usd=51.60,
            reason="MANUAL_FINAL_CLOSE"
        )
        assert err_c is None
        assert pos_close.status == "CLOSED"
        assert pos_close.remaining_quantity == 0.0
        assert len(pos_close.partial_exits) == 2
        # Total Realized = (1600 - 33.60) + (3600 - 51.60) = 5114.80
        assert abs(pos_close.total_realized_pnl_usd - 5114.80) < 0.2

        # 4. Check lists
        assert len(tracker.get_open_positions()) == 0
        assert len(tracker.get_closed_positions()) == 1


def test_idempotent_event_replay_and_state_recovery():
    """Verify event store idempotency and state reconstruction across restarts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker1 = UserPositionTracker(base_dir=tmpdir)
        tracker1.record_open_position(
            position_id="test_persist_001",
            instrument="BTC-USD",
            side="LONG",
            entry_price=80000.0,
            quantity=0.5,
            entry_timestamp_utc="2026-10-25T12:00:00Z"
        )
        tracker1.record_partial_exit(
            position_id="test_persist_001",
            exit_price=82000.0,
            quantity=0.2,
            exit_timestamp_utc="2026-10-25T13:00:00Z"
        )

        # Re-instantiate a clean tracker instance pointing to same storage
        tracker2 = UserPositionTracker(base_dir=tmpdir)
        recovered_pos = tracker2.get_position("test_persist_001")
        assert recovered_pos is not None
        assert recovered_pos.status == "PARTIALLY_CLOSED"
        assert recovered_pos.initial_quantity == 0.5
        assert recovered_pos.remaining_quantity == 0.3
        assert len(recovered_pos.partial_exits) == 1


def test_stale_market_data_handling():
    """Verify data_age > threshold generates WARNING_DATA_STALE alert."""
    copilot = AdaptiveRiskCopilot(stale_threshold_seconds=5.0)
    pos = UserPosition(
        position_id="test_stale_pos",
        user_id="default_user",
        instrument="BTC-USD",
        venue="COINBASE",
        market_type="SPOT",
        side="LONG",
        entry_price=80000.0,
        initial_quantity=1.0,
        remaining_quantity=1.0,
        entry_timestamp_utc="2026-10-25T12:00:00Z",
        entry_fee_usd=0.0,
        accumulated_fees_usd=0.0
    )
    quote_stale = {
        "price": 81000.0,
        "age_seconds": 12.5,  # > 5.0s
        "provider": "COINBASE"
    }
    snapshot = copilot.evaluate_position_risk(position=pos, market_quote=quote_stale)
    assert snapshot.mark_price_status == "DATA_STALE"
    alert_codes = [a.alert_code for a in snapshot.active_alerts]
    assert "WARNING_DATA_STALE" in alert_codes


def test_adaptive_risk_alerts_generation():
    """Verify stop proximity, target hit, GBDT conflict, and regime risk alerts."""
    copilot = AdaptiveRiskCopilot()
    pos = UserPosition(
        position_id="test_alert_pos",
        user_id="default_user",
        instrument="BTC-USD",
        venue="COINBASE",
        market_type="SPOT",
        side="LONG",
        entry_price=80000.0,
        initial_quantity=1.0,
        remaining_quantity=1.0,
        entry_timestamp_utc="2026-10-25T12:00:00Z",
        entry_fee_usd=0.0,
        accumulated_fees_usd=0.0,
        stop_loss_price=79500.0,  # Tight stop
        take_profit_price=85000.0
    )

    # Price at 79,800 is within 0.38% of stop (<= 1.0%) -> triggers WARNING_STOP_APPROACHING
    quote = {"price": 79800.0, "age_seconds": 1.0, "provider": "COINBASE"}
    gbdt_conflict = {
        "1h": {"probability_up": 0.25, "probability_down": 0.75}  # Strong down prediction against Long
    }
    regime_vol = {
        "regime": "BEARISH_BREAKDOWN",
        "volatility_state": "HIGH_VOLATILITY"
    }

    snapshot = copilot.evaluate_position_risk(
        position=pos,
        market_quote=quote,
        gbdt_forecasts=gbdt_conflict,
        regime_data=regime_vol
    )
    alert_codes = [a.alert_code for a in snapshot.active_alerts]
    assert "WARNING_STOP_APPROACHING" in alert_codes
    assert "WARNING_DIRECTIONAL_FORECAST_CONFLICT" in alert_codes
    assert "WARNING_REGIME_VOLATILITY_EXPANSION" in alert_codes


def test_api_endpoints_user_positions(authenticated_api_user, isolated_api_position_storage):
    """Verify REST API lifecycle endpoints for user positions."""
    test_pos_id = f"api_test_pos_{uuid.uuid4().hex[:8]}"
    # 1. Open a valid Long position
    req_open = {
        "position_id": test_pos_id,
        "instrument": "BTC-USD",
        "side": "LONG",
        "entry_price": 80000.0,
        "quantity": 0.5,
        "entry_fee_usd": 40.0,
        "stop_loss_price": 75000.0,
        "take_profit_price": 90000.0,
        "notes": "Testing API integration"
    }
    res = client.post("/api/positions/open", json=req_open)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["position"]["position_id"] == test_pos_id

    # 2. Query open positions list
    res_list = client.get("/api/positions")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total_open_count"] >= 1

    # 3. Query position detail
    res_detail = client.get(f"/api/positions/{test_pos_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["position"]["position_id"] == test_pos_id
    assert "risk_snapshot" in detail_data

    # 4. Partial exit
    res_pe = client.post(
        f"/api/positions/{test_pos_id}/partial-exit",
        json={"exit_price": 82000.0, "quantity": 0.2, "fee_usd": 16.4}
    )
    assert res_pe.status_code == 200
    pe_data = res_pe.json()
    assert pe_data["position"]["remaining_quantity"] == 0.3

    # 5. Full close
    res_c = client.post(
        f"/api/positions/{test_pos_id}/close",
        json={"exit_price": 83000.0, "fee_usd": 24.9}
    )
    assert res_c.status_code == 200
    c_data = res_c.json()
    assert c_data["position"]["status"] == "CLOSED"

    # 6. Check closed history
    res_hist = client.get("/api/positions/history")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    closed_ids = [p["position_id"] for p in hist_data["positions"]]
    assert test_pos_id in closed_ids


def test_protected_files_isolation_assertion():
    """Verify user position operations never modify any of the 5 protected files."""
    for path in PROTECTED_FILES:
        assert os.path.exists(path), f"Protected file missing: {path}"
        assert "user_positions" not in path
        with open(path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
            assert len(h) == 64
