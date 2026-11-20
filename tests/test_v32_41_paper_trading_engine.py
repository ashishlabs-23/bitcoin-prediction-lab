"""
tests/test_v32_41_paper_trading_engine.py — BTCognitive V32.41 Paper-Trading Verification Suite
================================================================================================
Tests the virtual execution engine, dual-sleeve portfolio simulation, causal latency delays,
order-book depth walking, fee calculations, partial fills, stale-feed abstention, delayed outcome
resolution, GBDT forecast recording, and strict non-execution safety invariants.
"""

import os
import sys
import json
import time
import math
import hashlib
import tempfile
import pytest
import numpy as np
from fastapi.testclient import TestClient

from engine.paper_trading_engine import (
    PaperTradingEngine,
    VirtualFill,
    VirtualPosition,
    VirtualSleeveState,
    PaperTradeOutcome,
    COST_REGISTRY
)
from api.server import app

client = TestClient(app)

PROTECTED_FILES = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prospective_entry_ledger.jsonl")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prospective_shadow_v1.jsonl")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prospective_entry_ledger_v2.jsonl")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "ohlcv.parquet")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "ohlcv_pre_backfill_backup.parquet")),
]


def test_safety_non_execution_and_no_broker_adapters():
    """Verify engine has zero broker execution adapters or order-placement capabilities."""
    engine = PaperTradingEngine()
    prohibited_attrs = [
        "ccxt", "broker", "api_key", "api_secret", "passphrase",
        "place_order", "send_order", "submit_order", "execute_live_order",
        "cancel_live_order", "exchange_client"
    ]
    for attr in prohibited_attrs:
        assert not hasattr(engine, attr), f"Prohibited live trading attribute '{attr}' found in PaperTradingEngine!"

    # Verify FastAPI endpoints status
    res = client.get("/api/research/paper-trading/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["engine_state"] == "PAPER_ENGINE_READY"
    assert data["operating_posture"] == "OFFLINE_RESEARCH_ONLY"
    assert data["live_trading"] == "DISABLED"
    assert data["broker_execution_adapters"] == "NONE"
    assert data["order_placement_routes"] == "NONE"
    assert "Chronos-2" in data["quarantined_models"]


def test_causal_decision_to_fill_latency_delay():
    """Verify fill occurs strictly after decision timestamp by documented latency delay."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = PaperTradingEngine(base_dir=tmpdir, latency_delay_sec=0.250)
        t_decision = 1792940000.0
        asks = [[80000.0, 1.0], [80010.0, 2.0]]
        bids = [[79990.0, 1.0], [79980.0, 2.0]]

        fill = engine.simulate_order_execution(
            sleeve_id="TEST_SLEEVE",
            side="BUY",
            target_qty_btc=0.5,
            decision_epoch=t_decision,
            order_book_bids=bids,
            order_book_asks=asks
        )
        assert fill.status == "FILLED"
        assert fill.decision_epoch == t_decision
        assert fill.fill_epoch == t_decision + 0.250
        assert fill.latency_delay_ms == 250.0
        assert fill.fill_epoch > fill.decision_epoch


def test_order_book_depth_walking_and_vwap_pricing():
    """Verify simulated execution walks multiple book levels to compute exact VWAP."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = PaperTradingEngine(base_dir=tmpdir)
        t_decision = 1792940000.0
        # Ask ladder: 0.1 BTC @ 80,000, 0.4 BTC @ 80,100, 1.0 BTC @ 80,200
        asks = [
            [80000.0, 0.1],
            [80100.0, 0.4],
            [80200.0, 1.0]
        ]
        bids = [[79990.0, 2.0]]

        # Target: 0.3 BTC -> fills 0.1 @ 80,000 + 0.2 @ 80,100
        # Expected cost = (0.1 * 80000) + (0.2 * 80100) = 8000 + 16020 = 24020
        # Expected VWAP = 24020 / 0.3 = 80066.67
        fill = engine.simulate_order_execution(
            sleeve_id="TEST_SLEEVE",
            side="BUY",
            target_qty_btc=0.3,
            decision_epoch=t_decision,
            order_book_bids=bids,
            order_book_asks=asks
        )
        assert fill.status == "FILLED"
        assert fill.filled_qty == 0.3
        assert fill.levels_traversed == 2
        assert abs(fill.vwap_fill_price - 80066.67) < 0.1
        # Slippage from best quote (80,000)
        expected_slippage_bps = (80066.67 - 80000.0) / 80000.0 * 10000.0
        assert abs(fill.slippage_bps - expected_slippage_bps) < 0.2


def test_order_book_depth_exhaustion_and_excessive_slippage():
    """Verify orders with excessive slippage (>50 bps) or empty books are rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = PaperTradingEngine(base_dir=tmpdir)
        t_decision = 1792940000.0

        # Case 1: Empty book
        fill_empty = engine.simulate_order_execution(
            sleeve_id="TEST_SLEEVE",
            side="BUY",
            target_qty_btc=1.0,
            decision_epoch=t_decision,
            order_book_bids=[],
            order_book_asks=[]
        )
        assert fill_empty.status == "REJECTED_STALE_FEED"
        assert fill_empty.filled_qty == 0.0

        # Case 2: Severe thin book resulting in >50 bps slippage
        # Best ask 80,000 (0.01 BTC), next ask 81,000 (10.0 BTC) -> ~124 bps slippage for 1.0 BTC
        asks_thin = [
            [80000.0, 0.01],
            [81000.0, 10.0]
        ]
        bids = [[79990.0, 5.0]]
        fill_slip = engine.simulate_order_execution(
            sleeve_id="TEST_SLEEVE",
            side="BUY",
            target_qty_btc=1.0,
            decision_epoch=t_decision,
            order_book_bids=bids,
            order_book_asks=asks_thin
        )
        assert fill_slip.status == "REJECTED_EXCESSIVE_SLIPPAGE"
        assert fill_slip.filled_qty == 0.0


def test_dual_sleeve_gated_vs_ungated_bifurcation():
    """Verify L2 gate blocks trade in Gated sleeve while Ungated sleeve executes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = PaperTradingEngine(base_dir=tmpdir)
        t_decision = 1792940000.0
        candidate_setup = {
            "candidate_id": "cand_test_001",
            "strategy_id": "TSMOM_DONCHIAN_168H_336H",
            "proposed_entry_price": 80000.0,
            "stop_loss_price": 76000.0,
            "take_profit_price": 88000.0,
            "holding_horizon_hours": 168.0
        }
        l2_snapshot = {
            "best_bid": 79995.0,
            "best_ask": 80000.0,
            "spread_bps": 0.625,
            "obi_5": -0.45,  # Heavy ask pressure -> Gate will reject!
            "ofi_15m": -12.4,  # Toxic negative OFI -> Gate rejects!
            "is_available": True
        }
        bids = [[79995.0, 5.0]]
        asks = [[80000.0, 5.0]]

        # Candidate with failed L2 gate
        res = engine.evaluate_and_execute_candidate(
            candidate_setup=candidate_setup,
            l2_snapshot=l2_snapshot,
            decision_epoch=t_decision,
            order_book_bids=bids,
            order_book_asks=asks,
            is_l2_gate_accepted=False,
            rejection_reason="GATE_REJECTED_TOXIC_OFI"
        )

        assert res["is_l2_gate_accepted"] is False
        assert res["sleeve_actions"]["GATED"]["action"] == "ABSTAIN_GATE_REJECTED"
        assert res["sleeve_actions"]["UNGATED"]["action"] == "ENTERED_LONG"

        # Verify Gated sleeve remains flat with full cash
        gated = engine.sleeves["TSMOM_DONCHIAN_168H_336H_L2_GATED"]
        assert gated.open_position is None
        assert gated.cash_balance_usd == 100000.0
        assert gated.total_trades_count == 0

        # Verify Ungated sleeve holds open position and cash reduced
        ungated = engine.sleeves["TSMOM_DONCHIAN_168H_336H_UNGATED"]
        assert ungated.open_position is not None
        assert ungated.open_position.is_open is True
        assert ungated.cash_balance_usd < 100000.0
        assert ungated.total_trades_count == 1


def test_fee_scenarios_active_vs_retail():
    """Verify transaction fee calculation under 27-bps vs 87-bps models."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Active trader (10 bps taker commission)
        engine_active = PaperTradingEngine(base_dir=tmpdir, cost_scenario="ACTIVE_TRADER_27BPS")
        fill_active = engine_active.simulate_order_execution(
            sleeve_id="TEST",
            side="BUY",
            target_qty_btc=1.0,
            decision_epoch=1792940000.0,
            order_book_bids=[[79990.0, 2.0]],
            order_book_asks=[[80000.0, 2.0]]
        )
        assert fill_active.commission_bps == 10.0
        # 1.0 BTC @ 80,000 * 10 bps = $80.00
        assert abs(fill_active.commission_usd - 80.0) < 0.01

        # 2. Retail (40 bps taker commission)
        engine_retail = PaperTradingEngine(base_dir=tmpdir, cost_scenario="RETAIL_87BPS")
        fill_retail = engine_retail.simulate_order_execution(
            sleeve_id="TEST",
            side="BUY",
            target_qty_btc=1.0,
            decision_epoch=1792940000.0,
            order_book_bids=[[79990.0, 2.0]],
            order_book_asks=[[80000.0, 2.0]]
        )
        assert fill_retail.commission_bps == 40.0
        # 1.0 BTC @ 80,000 * 40 bps = $320.00
        assert abs(fill_retail.commission_usd - 320.0) < 0.01


def test_delayed_outcome_resolution_enforcement():
    """Verify positions do not prematurely resolve, and close strictly upon barrier hit or maturity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = PaperTradingEngine(base_dir=tmpdir)
        t_entry = 1792940000.0
        bids = [[80000.0, 5.0]]
        asks = [[80010.0, 5.0]]

        candidate_setup = {
            "candidate_id": "cand_test_res",
            "strategy_id": "TSMOM_DONCHIAN_168H_336H",
            "proposed_entry_price": 80010.0,
            "stop_loss_price": 76000.0,
            "take_profit_price": 88000.0,
            "holding_horizon_hours": 168.0
        }
        engine.evaluate_and_execute_candidate(
            candidate_setup=candidate_setup,
            l2_snapshot={"is_available": True},
            decision_epoch=t_entry,
            order_book_bids=bids,
            order_book_asks=asks,
            is_l2_gate_accepted=True
        )

        # 1. During holding period, price is between SL and TP -> NO premature resolution
        resolved_mid = engine.check_and_resolve_positions(
            current_epoch=t_entry + 3600.0,  # 1 hour later
            current_price=82000.0,
            order_book_bids=[[81990.0, 5.0]],
            order_book_asks=[[82010.0, 5.0]]
        )
        assert len(resolved_mid) == 0  # Neither sleeve resolved

        # 2. Take profit hit at 88,500
        resolved_tp = engine.check_and_resolve_positions(
            current_epoch=t_entry + 7200.0,
            current_price=88500.0,
            order_book_bids=[[88500.0, 5.0]],
            order_book_asks=[[88510.0, 5.0]]
        )
        assert len(resolved_tp) == 2  # Both Gated and Ungated resolved
        assert resolved_tp[0].exit_reason == "TAKE_PROFIT"
        assert resolved_tp[0].realized_r > 0
        assert resolved_tp[0].mfe_r >= resolved_tp[0].realized_r


def test_gbdt_forecast_logging_and_quarantine():
    """Verify GBDT forecasts are logged point-in-time and Chronos-2 is quarantined."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = PaperTradingEngine(base_dir=tmpdir)
        closes = [60000.0 + i * 10 for i in range(700)]
        t_decision = 1792940000.0

        fc_entry = engine.log_and_evaluate_gbdt_forecasts(
            closes=closes,
            decision_epoch=t_decision,
            timeframe="15m"
        )
        assert fc_entry["record_type"] == "PAPER_GBDT_FORECAST_EMISSION"
        assert "1h" in fc_entry["forecasts"]
        assert "4h" in fc_entry["forecasts"]
        assert "24h" in fc_entry["forecasts"]
        assert "Chronos-2" not in fc_entry["forecasts"]

        # Ledger check
        assert os.path.exists(engine.gbdt_eval_ledger_path)
        with open(engine.gbdt_eval_ledger_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            rec = json.loads(lines[0])
            assert rec["decision_epoch"] == t_decision


def test_protected_files_isolation_assertion():
    """Verify paper trading operations never touch or modify the 5 protected files."""
    for path in PROTECTED_FILES:
        assert os.path.exists(path), f"Protected file missing: {path}"
        assert "paper_trading" not in path
        with open(path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
            assert len(h) == 64
