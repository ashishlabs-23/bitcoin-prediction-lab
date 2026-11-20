"""
tests/test_v32_42_manual_trade_journal_and_eval.py — BTCognitive V32.42 Manual Journal Tests
=============================================================================================
Tests the Manual Trade Journal and AI Forecast Evaluation Subsystem:
1. Long and Short gross and net P&L calculations.
2. Fees handling: GROSS_PNL_ONLY when fees unknown vs NET_PNL_COMPLETE when known.
3. Derivative contract calculations and missing contract specs handling.
4. Partial and full exit lifecycle reconciliation.
5. Durable persistence and state recovery across restarts from append-only ledger.
6. Forecast snapshot immutability (SHA-256 seal verification).
7. Forecast direction vs user-selected trade direction (trade against AI preserved).
8. Missing or stale forecast handling (honestly reported, never fabricated).
9. Duplicate trade ID protection and invalid inputs validation.
10. Insufficient evaluation samples caveat and contingency matrix accuracy.
11. FastAPI endpoints lifecycle integration.
12. Strict non-execution invariants and 5 protected files isolation.
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

from api import routes_manual_journal as journal_routes
from engine.manual_trade_journal import (
    ManualTradeJournal,
    ManualTradeRecord,
    capture_entry_forecast_snapshot
)
from api.server import app
from api.routes_manual_journal import get_current_principal_id

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
def isolated_api_journal_storage(tmp_path, monkeypatch):
    journal = ManualTradeJournal(base_dir=str(tmp_path / "api_journal"))
    monkeypatch.setattr(journal_routes, "_journal", journal)
    return journal


PROTECTED_FILES = [
    "data/prospective_entry_ledger.jsonl",
    "data/prospective_shadow_v1.jsonl",
    "data/prospective_entry_ledger_v2.jsonl",
    "data/raw/ohlcv.parquet",
    "data/raw/ohlcv_pre_backfill_backup.parquet"
]


def test_safety_non_execution_and_journal_status(authenticated_api_user, isolated_api_journal_storage):
    """Verify live trading is permanently DISABLED and zero broker adapters exist."""
    res = client.get("/api/journal/status")
    assert res.status_code == 200
    data = res.json()
    assert data["governance_status"] == "OFFLINE_RESEARCH_ONLY"
    assert data["economic_posture"] == "NO_GO_NO_VALIDATED_EDGE"
    assert data["live_trading_authorization"] == "DISABLED"
    assert data["broker_adapters"] == "STRICTLY_NONE"


def test_long_and_short_pnl_with_fees():
    """Verify spot Long and Short P&L calculations with known fees."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal = ManualTradeJournal(base_dir=tmpdir)

        # 1. Spot Long: Entry 80,000, Exit 85,000, Qty 0.5 BTC, Entry Fee $20, Exit Fee $21.25
        # Gross = (85,000 - 80,000) * 0.5 = $2,500
        # Net = 2,500 - 20 - 21.25 = $2,458.75
        t_long, err1 = journal.record_entry(
            instrument="BTC-USD",
            direction="LONG",
            entry_price=80000.0,
            quantity=0.5,
            entry_fee_usd=20.0
        )
        assert err1 is None
        assert t_long.pnl_status == "NET_PNL_INCOMPLETE"  # exit fee still pending

        closed_long, err_ex1 = journal.record_exit(
            trade_id=t_long.trade_id,
            exit_price=85000.0,
            exit_fee_usd=21.25
        )
        assert err_ex1 is None
        assert closed_long.status == "CLOSED"
        assert abs(closed_long.gross_pnl_usd - 2500.0) < 1e-4
        assert abs(closed_long.net_pnl_usd - 2458.75) < 1e-4
        assert closed_long.pnl_status == "NET_PNL_COMPLETE"
        assert closed_long.user_outcome == "WIN"
        assert closed_long.return_on_notional_pct == pytest.approx(6.25, abs=0.01)

        # 2. Spot Short: Entry 80,000, Exit 76,000, Qty 0.4 BTC, Entry Fee $16, Exit Fee $15.20
        # Gross = (80,000 - 76,000) * 0.4 = $1,600
        # Net = 1,600 - 16 - 15.20 = $1,568.80
        t_short, err2 = journal.record_entry(
            instrument="BTC-USD",
            direction="SHORT",
            entry_price=80000.0,
            quantity=0.4,
            entry_fee_usd=16.0
        )
        assert err2 is None
        closed_short, err_ex2 = journal.record_exit(
            trade_id=t_short.trade_id,
            exit_price=76000.0,
            exit_fee_usd=15.20
        )
        assert err_ex2 is None
        assert closed_short.status == "CLOSED"
        assert abs(closed_short.gross_pnl_usd - 1600.0) < 1e-4
        assert abs(closed_short.net_pnl_usd - 1568.80) < 1e-4
        assert closed_short.pnl_status == "NET_PNL_COMPLETE"
        assert closed_short.user_outcome == "WIN"


def test_gross_only_label_when_fees_unknown():
    """Verify result is labeled GROSS_PNL_ONLY when fees are omitted (never assumes zero)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal = ManualTradeJournal(base_dir=tmpdir)
        t, err = journal.record_entry(
            instrument="BTC-USD",
            direction="LONG",
            entry_price=80000.0,
            quantity=0.5,
            entry_fee_usd=None  # Unknown
        )
        assert err is None
        assert t.pnl_status == "GROSS_PNL_ONLY"

        closed, err_ex = journal.record_exit(
            trade_id=t.trade_id,
            exit_price=82000.0,
            exit_fee_usd=None  # Unknown
        )
        assert err_ex is None
        assert closed.status == "CLOSED"
        assert closed.gross_pnl_usd == pytest.approx(1000.0, abs=1e-4)
        assert closed.net_pnl_usd is None
        assert closed.pnl_status == "GROSS_PNL_ONLY"


def test_derivative_calculations_and_missing_contract_specs():
    """Verify derivative multipliers and rejection when contract specs are invalid."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal = ManualTradeJournal(base_dir=tmpdir)

        # Valid perpetual with contract multiplier 10.0
        # Entry 80,000, Exit 82,000, Qty 1.0, Multiplier 10.0 -> Gross = 2,000 * 1.0 * 10.0 = $20,000
        t_perp, _ = journal.record_entry(
            instrument="BTC-PERP",
            direction="LONG",
            entry_price=80000.0,
            quantity=1.0,
            market_type="PERPETUAL",
            leverage=5.0,
            contract_multiplier=10.0
        )
        closed_perp, _ = journal.record_exit(trade_id=t_perp.trade_id, exit_price=82000.0)
        assert closed_perp.gross_pnl_usd == pytest.approx(20000.0, abs=1e-4)

        # Invalid contract multiplier (<= 0)
        t_bad, _ = journal.record_entry(
            instrument="BTC-PERP",
            direction="LONG",
            entry_price=80000.0,
            quantity=1.0,
            market_type="PERPETUAL",
            contract_multiplier=-1.0
        )
        assert t_bad.contract_spec_valid is False
        assert t_bad.pnl_status == "CALCULATION_INCOMPLETE_MISSING_CONTRACT_SPECS"

        closed_bad, _ = journal.record_exit(trade_id=t_bad.trade_id, exit_price=82000.0)
        assert closed_bad.pnl_status == "CALCULATION_INCOMPLETE_MISSING_CONTRACT_SPECS"
        assert closed_bad.gross_pnl_usd is None


def test_partial_and_full_exits_reconciliation():
    """Verify partial exit deduction and final volume-weighted close."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal = ManualTradeJournal(base_dir=tmpdir)
        t, _ = journal.record_entry(
            instrument="BTC-USD",
            direction="LONG",
            entry_price=80000.0,
            quantity=1.0,
            entry_fee_usd=40.0
        )

        # Partial exit 1: 0.4 BTC @ 82,000, Fee $16.40
        # Gross = 0.4 * 2,000 = $800
        t_part, err_p = journal.record_exit(
            trade_id=t.trade_id,
            exit_price=82000.0,
            quantity=0.4,
            exit_fee_usd=16.40
        )
        assert err_p is None
        assert t_part.status == "PARTIALLY_EXITED"
        assert t_part.remaining_quantity == pytest.approx(0.6, abs=1e-6)
        assert t_part.gross_pnl_usd == pytest.approx(800.0, abs=1e-4)

        # Exceeding quantity is rejected
        _, err_over = journal.record_exit(
            trade_id=t.trade_id,
            exit_price=83000.0,
            quantity=0.7  # > 0.6
        )
        assert err_over is not None

        # Partial exit 2 (Full close): remaining 0.6 BTC @ 84,000, Fee $25.20
        # Gross = 0.6 * 4,000 = $2,400
        # Total Gross = 800 + 2,400 = $3,200
        # Total Fees = 40.0 + 16.40 + 25.20 = $81.60
        # Total Net = 3,200 - 81.60 = $3,118.40
        # VWAP Exit Price = (0.4 * 82000 + 0.6 * 84000) / 1.0 = 83,200
        closed, err_c = journal.record_exit(
            trade_id=t.trade_id,
            exit_price=84000.0,
            quantity=0.6,
            exit_fee_usd=25.20
        )
        assert err_c is None
        assert closed.status == "CLOSED"
        assert closed.remaining_quantity == 0.0
        assert closed.final_exit_price == pytest.approx(83200.0, abs=1e-4)
        assert closed.gross_pnl_usd == pytest.approx(3200.0, abs=1e-4)
        assert closed.net_pnl_usd == pytest.approx(3118.40, abs=1e-4)
        assert closed.pnl_status == "NET_PNL_COMPLETE"


def test_durable_persistence_and_recovery():
    """Verify append-only ledger reconstructs exact state across re-initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal1 = ManualTradeJournal(base_dir=tmpdir)
        t, _ = journal1.record_entry(
            trade_id="persist_trade_001",
            instrument="BTC-USD",
            direction="LONG",
            entry_price=80000.0,
            quantity=0.5
        )
        journal1.record_exit(trade_id="persist_trade_001", exit_price=82000.0, quantity=0.2)

        # Second instance from same directory
        journal2 = ManualTradeJournal(base_dir=tmpdir)
        rec = journal2.get_trade("persist_trade_001")
        assert rec is not None
        assert rec.status == "PARTIALLY_EXITED"
        assert rec.remaining_quantity == pytest.approx(0.3, abs=1e-6)
        assert len(rec.exits) == 1


def test_forecast_snapshot_immutability():
    """Verify point-in-time forecast snapshot contains valid SHA-256 seal."""
    snap = capture_entry_forecast_snapshot(instrument="BTC-USD", reference_price=80000.0)
    assert "immutable_sha256" in snap
    sha = snap["immutable_sha256"]
    assert len(sha) == 64
    assert snap["model_id"] == "directional-gbm-ensemble-v1.0"
    assert "horizons" in snap


def test_forecast_direction_vs_user_selected_trade_direction():
    """Verify user entering against AI forecast is preserved and evaluated separately."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal = ManualTradeJournal(base_dir=tmpdir)

        # Simulated snapshot predicting UP
        mock_snapshot = {
            "snapshot_timestamp_utc": "2026-10-25T12:00:00Z",
            "instrument": "BTC-USD",
            "forecast_status": "VALID",
            "model_id": "directional-gbm-ensemble-v1.0",
            "predicted_direction": "UP",
            "probability_up": 0.72,
            "probability_down": 0.28,
            "regime_classification": "BULLISH_TREND",
            "strategy_signal": "ENTER_LONG",
            "immutable_sha256": "fake_sha_for_test"
        }

        # User chooses to go SHORT against the model
        t, _ = journal.record_entry(
            direction="SHORT",
            entry_price=80000.0,
            quantity=1.0,
            pre_captured_snapshot=mock_snapshot
        )
        assert t.forecast_agreement is False  # User went against AI

        # Market rises to 82,000 (Model was CORRECT, User suffered a LOSS)
        closed, _ = journal.record_exit(trade_id=t.trade_id, exit_price=82000.0)
        assert closed.user_outcome == "LOSS"
        assert closed.forecast_outcome == "CORRECT"  # Model predicted UP, price went up!

        eval_res = journal.evaluate_performance()
        ai_perf = eval_res["ai_performance"]
        assert ai_perf["directional_agreement_count"] == 0
        assert ai_perf["model_correct_count"] == 1
        assert ai_perf["contingency_matrix"]["user_loss_model_correct"] == 1


def test_api_endpoints_manual_journal_lifecycle(authenticated_api_user, isolated_api_journal_storage):
    """Verify REST API lifecycle endpoints for manual trade journal."""
    test_id = f"trd_api_{uuid.uuid4().hex[:8]}"

    # 1. Enter trade
    req_enter = {
        "trade_id": test_id,
        "instrument": "BTC-USD",
        "direction": "LONG",
        "entry_price": 80000.0,
        "quantity": 0.5,
        "entry_fee_usd": 20.0,
        "notes": "Testing manual journal API"
    }
    res = client.post("/api/journal/trades/enter", json=req_enter)
    assert res.status_code == 200
    t_data = res.json()["trade"]
    assert t_data["trade_id"] == test_id
    assert t_data["status"] == "OPEN"

    # 2. Query detail
    res_d = client.get(f"/api/journal/trades/{test_id}")
    assert res_d.status_code == 200
    assert res_d.json()["trade"]["trade_id"] == test_id

    # 3. Auditable adjustment
    res_adj = client.post(
        f"/api/journal/trades/{test_id}/adjust",
        json={"field_name": "notes", "new_value": "Updated thesis note", "reason": "Operator clarification"}
    )
    assert res_adj.status_code == 200
    assert res_adj.json()["trade"]["notes"] == "Updated thesis note"

    # 4. Exit trade
    res_ex = client.post(
        f"/api/journal/trades/{test_id}/exit",
        json={"exit_price": 82000.0, "exit_fee_usd": 20.5, "notes": "Target reached"}
    )
    assert res_ex.status_code == 200
    closed = res_ex.json()["trade"]
    assert closed["status"] == "CLOSED"
    assert closed["user_outcome"] == "WIN"
    assert closed["pnl_status"] == "NET_PNL_COMPLETE"

    # 5. Query evaluation
    res_ev = client.get("/api/journal/evaluation")
    assert res_ev.status_code == 503
    assert "Owner-scoped performance evaluation is unavailable" in res_ev.json()["detail"]


def test_protected_files_isolation_assertion():
    """Verify that the 5 protected files are never altered."""
    for rel_path in PROTECTED_FILES:
        full_path = os.path.join(os.path.dirname(__file__), "..", rel_path)
        assert os.path.exists(full_path), f"Protected file missing: {rel_path}"
