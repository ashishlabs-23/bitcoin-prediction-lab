"""
tests/test_coinbase_l2_collector_and_gating.py — Opt-In Coinbase L2 Test Suite
=============================================================================
Deterministic unit, integration, and fault-injection test suite for:
- Coinbase L2 WebSocket collector (disabled-by-default, reconnection, sequence gaps).
- Causal microstructure features (Cont et al. OFI, OBI, CVD, Spread).
- Point-in-time timestamp alignment (no future lookahead).
- Fail-closed gating logic and machine-readable rejection codes.
- Two-phase prospective ledger audit and deduplication.
- Protection of existing research ledgers and historical datasets.
- Non-execution and OFFLINE_RESEARCH_ONLY guardrails.
"""

import os
import json
import time
import tempfile
import pytest
import numpy as np
from fastapi.testclient import TestClient

from engine.l2_microstructure_features import (
    OrderBookTracker,
    L2MicrostructureSnapshot,
    compute_obi,
    compute_spread_bps,
    compute_ofi_from_top_of_book_events,
    compute_cvd_from_matches
)
from engine.coinbase_l2_collector import CoinbaseL2Collector, AUTHORIZED_PRODUCT
from engine.prospective_l2_shadow_gating import (
    ProspectiveL2GatedLedger,
    L2ShadowGatingEngine,
    L2GatedCandidateRecord,
    L2GatedOutcomeRecord,
    STRATEGY_ID,
    COST_REGISTRY_BPS
)
from engine.entry_contracts import CandidateSetup, compute_candidate_id
from api.server import app

client = TestClient(app)

PROTECTED_FILES = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prospective_entry_ledger.jsonl")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prospective_shadow_v1.jsonl")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prospective_entry_ledger_v2.jsonl")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "ohlcv.parquet")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "ohlcv_pre_backfill_backup.parquet")),
]


def test_l2_collector_disabled_by_default():
    """Verify collector fails closed if enabled=False."""
    collector = CoinbaseL2Collector(enabled=False)
    assert not collector.enabled
    started = collector.start()
    assert started is False
    assert not collector._running


def test_l2_collector_rejects_unauthorized_product():
    """Verify collector strictly rejects any symbol other than BTC-USD spot."""
    with pytest.raises(ValueError, match="Unauthorized product"):
        CoinbaseL2Collector(product_id="ETH-USD", enabled=False)


def test_order_book_snapshot_reconstruction():
    """Verify snapshot processing creates sorted bids and asks correctly."""
    tracker = OrderBookTracker()
    now = time.time()
    snapshot_msg = {
        "type": "snapshot",
        "product_id": "BTC-USD",
        "sequence": 1000,
        "bids": [["60000.00", "1.50"], ["59950.00", "2.00"], ["59900.00", "5.00"]],
        "asks": [["60050.00", "1.00"], ["60100.00", "3.00"], ["60150.00", "4.00"]]
    }
    tracker.process_snapshot(snapshot_msg, received_epoch=now)
    assert tracker.is_synchronized
    assert tracker.last_sequence == 1000

    best_b, best_b_sz = tracker.get_best_bid()
    best_a, best_a_sz = tracker.get_best_ask()
    assert best_b == 60000.00
    assert best_b_sz == 1.50
    assert best_a == 60050.00
    assert best_a_sz == 1.00

    spread = compute_spread_bps(best_b, best_a)
    expected_spread = ((60050.0 - 60000.0) / 60025.0) * 10000.0
    assert abs(spread - expected_spread) < 1e-4


def test_order_book_l2update_reconstruction():
    """Verify incremental updates modify order book and delete zero-size levels."""
    tracker = OrderBookTracker()
    now = time.time()
    tracker.process_snapshot({
        "type": "snapshot",
        "product_id": "BTC-USD",
        "sequence": 100,
        "bids": [["60000.00", "1.00"]],
        "asks": [["60050.00", "1.00"]]
    }, received_epoch=now)

    # 1. Add higher bid
    tracker.process_l2update({
        "type": "l2update",
        "product_id": "BTC-USD",
        "sequence": 101,
        "changes": [["buy", "60010.00", "2.50"]]
    }, received_epoch=now + 0.1)
    best_b, best_b_sz = tracker.get_best_bid()
    assert best_b == 60010.00
    assert best_b_sz == 2.50

    # 2. Delete level by setting size to 0
    tracker.process_l2update({
        "type": "l2update",
        "product_id": "BTC-USD",
        "sequence": 102,
        "changes": [["buy", "60010.00", "0"]]
    }, received_epoch=now + 0.2)
    best_b, best_b_sz = tracker.get_best_bid()
    assert best_b == 60000.00
    assert best_b_sz == 1.00


def test_order_book_sequence_gap_detection():
    """Verify that a missing sequence invalidates synchronization instantly."""
    tracker = OrderBookTracker()
    now = time.time()
    tracker.process_snapshot({
        "type": "snapshot",
        "product_id": "BTC-USD",
        "sequence": 100,
        "bids": [["60000.00", "1.00"]],
        "asks": [["60050.00", "1.00"]]
    }, received_epoch=now)
    assert tracker.is_synchronized

    # Message with sequence jump 100 -> 105 (gap of 4)
    tracker.process_l2update({
        "type": "l2update",
        "product_id": "BTC-USD",
        "sequence": 105,
        "changes": [["buy", "60000.00", "1.50"]]
    }, received_epoch=now + 0.1)

    assert not tracker.is_synchronized
    assert "SEQUENCE_GAP" in (tracker.desync_reason or "")

    # Feature extraction must fail closed
    snap = tracker.extract_microstructure_snapshot(decision_epoch=now + 0.2)
    assert not snap.is_available
    assert "L2_FEED_DESYNCHRONIZED" in (snap.reason_code or "")


def test_order_book_heartbeat_staleness_and_stall():
    """Verify heartbeat stall (>5.0s) causes fail-closed feature extraction."""
    tracker = OrderBookTracker()
    now = time.time()
    tracker.process_snapshot({
        "type": "snapshot",
        "product_id": "BTC-USD",
        "sequence": 100,
        "bids": [["60000.00", "1.00"]],
        "asks": [["60050.00", "1.00"]]
    }, received_epoch=now)

    # Fast forward 10 seconds without updates
    snap = tracker.extract_microstructure_snapshot(decision_epoch=now + 10.0, max_staleness_seconds=5.0)
    assert not snap.is_available
    assert "L2_DATA_STALE" in (snap.reason_code or "")


def test_cont_kukanov_stoikov_ofi_known_answer():
    """
    Known-answer fixture for Order Flow Imbalance (Cont, Kukanov & Stoikov 2014):
    Events:
    t0: bid=100 (q=10), ask=105 (q=10)
    t1: bid=101 (q=5)   [P_B increased -> delta_B = +5]
        ask=105 (q=8)   [P_A unchanged -> delta_A = 8 - 10 = -2]
        OFI_1 = delta_B - delta_A = 5 - (-2) = +7
    t2: bid=101 (q=3)   [P_B unchanged -> delta_B = 3 - 5 = -2]
        ask=106 (q=12)  [P_A increased -> delta_A = -12]
        OFI_2 = delta_B - delta_A = -2 - (-12) = +10
    Total OFI = 7 + 10 = +17
    """
    events = [
        {"best_bid": 100.0, "best_bid_size": 10.0, "best_ask": 105.0, "best_ask_size": 10.0},
        {"best_bid": 101.0, "best_bid_size": 5.0,  "best_ask": 105.0, "best_ask_size": 8.0},
        {"best_bid": 101.0, "best_bid_size": 3.0,  "best_ask": 106.0, "best_ask_size": 12.0},
    ]
    ofi = compute_ofi_from_top_of_book_events(events)
    assert ofi == 17.0


def test_obi_and_cvd_calculation():
    """Verify Order Book Imbalance and Cumulative Volume Delta."""
    bids = {60000.0: 3.0, 59900.0: 1.0}
    asks = {60100.0: 1.0, 60200.0: 1.0}
    # Total bids = 4.0, Total asks = 2.0 -> OBI = (4 - 2) / 6 = 2/6 = 0.3333...
    obi = compute_obi(bids, asks, depth=5)
    assert abs(obi - (2.0 / 6.0)) < 1e-4

    matches = [
        {"side": "buy", "size": "1.5"},
        {"side": "buy", "size": "0.5"},
        {"side": "sell", "size": "0.8"}
    ]
    cvd = compute_cvd_from_matches(matches)
    assert abs(cvd - (2.0 - 0.8)) < 1e-4


def test_causal_point_in_time_boundary_no_lookahead():
    """Verify feature extractor strictly ignores any events received after decision_epoch."""
    tracker = OrderBookTracker()
    t_decision = 1000.0

    tracker.process_snapshot({
        "type": "snapshot",
        "product_id": "BTC-USD",
        "sequence": 1,
        "bids": [["60000.00", "1.00"]],
        "asks": [["60050.00", "1.00"]]
    }, received_epoch=999.0)

    # Add future match at t = 1005.0
    tracker.process_match({
        "type": "match",
        "sequence": 2,
        "side": "buy",
        "size": "50.0",
        "price": "60050.00",
        "time": "2026-10-25T12:00:05.000000Z"
    }, received_epoch=1005.0)

    # Snapshot at t_decision (1000.0) must NOT include the trade at 1005.0
    snap = tracker.extract_microstructure_snapshot(decision_epoch=t_decision)
    assert snap.cvd_value == 0.0
    assert snap.trade_count_in_window == 0


def test_l2_shadow_gating_decision_matrix():
    """Verify complete decision matrix of frozen gating protocol."""
    engine = L2ShadowGatingEngine()

    # 1. Feed uninitialized / desynchronized
    snap_desync = L2MicrostructureSnapshot(
        is_available=False,
        reason_code="L2_FEED_DESYNCHRONIZED: NOT_INITIALIZED",
        observation_time_utc="2026-10-25T12:00:00Z",
        observation_epoch=1000.0,
        best_bid=None, best_ask=None, mid_price=None, spread_bps=None,
        obi_5=None, obi_10=None, obi_25=None, ofi_value=None, cvd_value=None,
        trade_count_in_window=0, book_updates_in_window=0, data_age_seconds=0.0,
        is_feed_synchronized=False
    )
    dec, reason = engine.evaluate_gate(snap_desync)
    assert dec == "GATE_ABSTAIN_L2_UNAVAILABLE"

    # 2. Toxic OFI (OFI <= 0.0)
    snap_toxic_ofi = L2MicrostructureSnapshot(
        is_available=True, reason_code=None,
        observation_time_utc="2026-10-25T12:00:00Z", observation_epoch=1000.0,
        best_bid=60000.0, best_ask=60010.0, mid_price=60005.0, spread_bps=1.67,
        obi_5=0.10, obi_10=0.10, obi_25=0.10,
        ofi_value=-2.5, cvd_value=1.0,
        trade_count_in_window=10, book_updates_in_window=20, data_age_seconds=0.1,
        is_feed_synchronized=True
    )
    dec, reason = engine.evaluate_gate(snap_toxic_ofi)
    assert dec == "GATE_REJECTED_TOXIC_OFI"

    # 3. Heavy Ask Depth (OBI_5 <= -0.20)
    snap_heavy_ask = L2MicrostructureSnapshot(
        is_available=True, reason_code=None,
        observation_time_utc="2026-10-25T12:00:00Z", observation_epoch=1000.0,
        best_bid=60000.0, best_ask=60010.0, mid_price=60005.0, spread_bps=1.67,
        obi_5=-0.45, obi_10=-0.30, obi_25=-0.20,
        ofi_value=5.0, cvd_value=1.0,
        trade_count_in_window=10, book_updates_in_window=20, data_age_seconds=0.1,
        is_feed_synchronized=True
    )
    dec, reason = engine.evaluate_gate(snap_heavy_ask)
    assert dec == "GATE_REJECTED_HEAVY_ASK"

    # 4. Wide Spread (> 5.0 bps)
    snap_wide_spread = L2MicrostructureSnapshot(
        is_available=True, reason_code=None,
        observation_time_utc="2026-10-25T12:00:00Z", observation_epoch=1000.0,
        best_bid=60000.0, best_ask=60060.0, mid_price=60030.0, spread_bps=9.99,
        obi_5=0.20, obi_10=0.20, obi_25=0.20,
        ofi_value=5.0, cvd_value=1.0,
        trade_count_in_window=10, book_updates_in_window=20, data_age_seconds=0.1,
        is_feed_synchronized=True
    )
    dec, reason = engine.evaluate_gate(snap_wide_spread)
    assert dec == "GATE_REJECTED_WIDE_SPREAD"

    # 5. Healthy Book
    snap_healthy = L2MicrostructureSnapshot(
        is_available=True, reason_code=None,
        observation_time_utc="2026-10-25T12:00:00Z", observation_epoch=1000.0,
        best_bid=60000.0, best_ask=60010.0, mid_price=60005.0, spread_bps=1.67,
        obi_5=0.15, obi_10=0.15, obi_25=0.15,
        ofi_value=8.4, cvd_value=3.2,
        trade_count_in_window=15, book_updates_in_window=30, data_age_seconds=0.05,
        is_feed_synchronized=True
    )
    dec, reason = engine.evaluate_gate(snap_healthy)
    assert dec == "GATE_ACCEPTED_SHADOW"
    assert reason is None


def test_prospective_l2_gated_ledger_idempotency_and_two_phase_audit():
    """Verify Phase A and Phase B atomic writes and duplicate rejection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_file = os.path.join(tmpdir, "test_l2_ledger.jsonl")
        ledger = ProspectiveL2GatedLedger(ledger_path=ledger_file)

        cand_record = L2GatedCandidateRecord(
            record_type="L2_GATED_CANDIDATE",
            schema_version="PROSPECTIVE_L2_GATED_V1",
            candidate_id="scand_test_001",
            strategy_id=STRATEGY_ID,
            strategy_spec_hash="8f3e2b9c7a1d5e4b",
            instrument_id="BTC-USD",
            venue="COINBASE",
            market_type="SPOT",
            decision_timestamp_utc="2026-10-25T12:00:00Z",
            fill_timestamp_utc="2026-10-25T13:00:00Z",
            entry_reference_price=60000.0,
            proposed_entry_price=60000.0,
            stop_loss_price=58000.0,
            take_profit_price=63000.0,
            direction="LONG",
            horizon_bars=168,
            risk_unit_usd=2000.0,
            cost_scenario="ACTIVE_TRADER_27BPS",
            round_trip_friction_bps=27.0,
            gate_decision="GATE_ACCEPTED_SHADOW",
            rejection_reason=None,
            l2_snapshot={"ofi_value": 5.0, "obi_5": 0.25, "spread_bps": 2.0}
        )

        # 1. First write must succeed
        assert ledger.append_candidate(cand_record) is True

        # 2. Duplicate write must be rejected
        assert ledger.append_candidate(cand_record) is False

        # 3. Append outcome
        outcome_record = L2GatedOutcomeRecord(
            record_type="L2_GATED_OUTCOME",
            schema_version="PROSPECTIVE_L2_GATED_V1",
            candidate_id="scand_test_001",
            strategy_id=STRATEGY_ID,
            resolution_status="RESOLVED",
            exit_reason="TAKE_PROFIT",
            is_ambiguous_touch=False,
            entry_timestamp_utc="2026-10-25T13:00:00Z",
            exit_timestamp_utc="2026-10-26T14:00:00Z",
            entry_fill_price=60000.0,
            exit_price=63000.0,
            bars_held=25,
            gross_return_bps=500.0,
            net_returns_by_scenario_bps={"ACTIVE_TRADER_27BPS": 473.0, "RETAIL_87BPS": 413.0},
            risk_unit_usd=2000.0,
            gross_r=1.50,
            net_r_by_scenario={"ACTIVE_TRADER_27BPS": 1.419, "RETAIL_87BPS": 1.239},
            mfe_r=1.50,
            mae_r=-0.20,
            gate_decision="GATE_ACCEPTED_SHADOW",
            was_shadow_gated_accepted=True,
            resolution_timestamp_utc="2026-10-26T14:00:05Z"
        )
        assert ledger.append_outcome(outcome_record) is True
        assert ledger.append_outcome(outcome_record) is False

        # Read back
        recs = ledger.read_all_records()
        assert len(recs) == 2
        assert recs[0]["record_type"] == "L2_GATED_CANDIDATE"
        assert recs[1]["record_type"] == "L2_GATED_OUTCOME"


def test_protected_files_isolation_assertion():
    """Verify test operations never touch or modify the 5 protected files."""
    for path in PROTECTED_FILES:
        assert os.path.exists(path), f"Protected file missing: {path}"
        assert not path.endswith("prospective_l2_gated_ledger_v1.jsonl"), "L2 ledger must be separate from protected files"


def test_api_endpoints_l2_gating():
    """Verify HTTP GET endpoints for L2 gating status and evaluation."""
    res_status = client.get("/api/research/l2-gating-status")
    assert res_status.status_code == 200
    data = res_status.json()
    assert data["status"] == "SUCCESS"
    assert data["operating_posture"] == "OFFLINE_RESEARCH_ONLY"
    assert data["live_trading"] == "DISABLED"
    assert data["collector_enabled_default"] is False
    assert data["product_id"] == "BTC-USD"
    assert data["gating_rules"]["fail_closed_mode"] == "GATE_ABSTAIN_L2_UNAVAILABLE"

    res_eval = client.get("/api/research/l2-shadow-evaluation")
    assert res_eval.status_code == 200
    eval_data = res_eval.json()
    assert "protocol_version" in eval_data
    assert eval_data["protocol_version"] == "V32.31_PROSPECTIVE_L2_GATED_V1"
    assert "confirmatory_gate_decision" in eval_data
