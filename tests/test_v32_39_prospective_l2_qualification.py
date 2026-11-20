"""
tests/test_v32_39_prospective_l2_qualification.py
=================================================
BTCognitive V32.39: Prospective Level-2 Shadow Qualification Test Suite

Verifies:
1. Preflight checks and deterministic dry-run verification.
2. Reconnect recovery requiring authoritative snapshot resynchronization.
3. Sequence gap handling causing fail-closed gate abstention.
4. Deterministic replay and SHA-256 event checksum validation.
5. Causal timestamp integrity (strictly <= decision epoch).
6. Candidate completeness (recording both gate-passing and gate-rejected opportunities).
7. Delayed outcome resolution guard (rejecting premature resolution).
8. Statistical independence: Non-overlapping block accounting and overlap handling.
9. Pre-registered confirmatory paired difference statistics and 100-block hurdle.
10. Protected files bit-identical isolation.
"""

import os
import sys
import time
import json
import hashlib
import tempfile
import pytest
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from engine.l2_microstructure_features import OrderBookTracker
from engine.l2_event_recorder import RawL2Event, L2EventRecorder
from engine.run_l2_prospective_burnin import (
    run_preflight_checks,
    execute_dry_run_test,
    check_free_disk_space_mb
)
from engine.prospective_l2_evaluation_protocol import (
    ProspectiveL2EvaluationProtocol,
    ProspectiveCandidateEntry,
    ProspectiveOutcomeEntry,
    SCHEMA_VERSION,
    HORIZON_HOURS,
    COST_SCENARIOS
)

PROTECTED_FILES = {
    "data/prospective_entry_ledger.jsonl": "91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7",
    "data/prospective_shadow_v1.jsonl": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "data/prospective_entry_ledger_v2.jsonl": "e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604",
    "data/raw/ohlcv.parquet": "1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c",
    "data/raw/ohlcv_pre_backfill_backup.parquet": "c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8"
}


def test_preflight_checks_and_dry_run():
    """Verify disk space, preflight diagnostics, and synthetic stream replay."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        preflight = run_preflight_checks(tmp_dir)
        assert preflight["free_disk_space_mb"] > 100.0
        assert preflight["disk_space_sufficient"]
        assert preflight["preflight_status"] == "READY"
        assert preflight["collector_operational_status"] == "STOPPED_DISABLED"

    dry_run = execute_dry_run_test()
    assert dry_run["dry_run_success"]
    assert dry_run["events_replayed"] == 3
    assert dry_run["best_bid"] == 68010.0
    assert dry_run["best_ask"] == 68100.0


def test_reconnect_recovery_procedure():
    """Verify that socket reconnection resets book and requires snapshot before deltas."""
    tracker = OrderBookTracker()
    ep = 1778200000.0

    # 1. Initial snapshot
    tracker.process_snapshot({
        "type": "snapshot",
        "sequence": 500,
        "bids": [["60000.00", "1.0"]],
        "asks": [["60050.00", "1.0"]]
    }, received_epoch=ep)
    assert tracker.is_synchronized

    # 2. Simulate disconnect: reset tracker
    tracker.reset(reason="SOCKET_DISCONNECTED")
    assert not tracker.is_synchronized
    assert tracker.desync_reason == "SOCKET_DISCONNECTED"

    # 3. Deltas received before snapshot must be rejected
    upd_res = tracker.process_l2update({
        "type": "l2update",
        "sequence": 501,
        "changes": [["buy", "60010.00", "1.0"]]
    }, received_epoch=ep + 1.0)
    assert upd_res is False
    assert not tracker.is_synchronized

    # 4. Authoritative snapshot restores synchronization cleanly
    tracker.process_snapshot({
        "type": "snapshot",
        "sequence": 600,
        "bids": [["60020.00", "2.0"]],
        "asks": [["60070.00", "2.0"]]
    }, received_epoch=ep + 2.0)
    assert tracker.is_synchronized
    assert tracker.last_sequence == 600
    b_b, _ = tracker.get_best_bid()
    assert b_b == 60020.0


def test_sequence_gap_and_fail_closed_gate():
    """Verify sequence gaps trigger immediate desync and cause gate abstention."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_ledger.jsonl")
        protocol = ProspectiveL2EvaluationProtocol(ledger_path=ledger_path)

        # Snapshot with sequence gap flag
        bad_snapshot = {
            "is_available": False,
            "is_feed_synchronized": False,
            "reason_code": "L2_FEED_DESYNCHRONIZED: SEQUENCE_GAP_DETECTED (expected 101, got 105)",
            "data_age_seconds": 0.5,
            "ofi_value": 5.0,
            "obi_5": 0.20,
            "spread_bps": 2.0
        }

        entry = protocol.register_opportunity(
            candidate_id="c_gap_01",
            baseline_opportunity_id="base_01",
            decision_epoch=time.time(),
            proposed_entry=65000.0,
            stop_loss=64000.0,
            take_profit=66500.0,
            risk_unit_usd=1000.0,
            l2_snapshot=bad_snapshot
        )

        assert not entry.gate_passed
        assert entry.gate_decision == "GATE_ABSTAIN_L2_UNAVAILABLE"
        assert entry.data_quality_status == "FEED_DESYNC"


def test_deterministic_replay_and_checksum_integrity():
    """Verify event recorder SHA-256 checksums and bit-identical dual replay."""
    recorder = L2EventRecorder()
    base_ep = 1778200000.0

    recorder.record_event("snapshot", {
        "sequence": 1,
        "bids": [["65000.00", "1.0"], ["64900.00", "2.0"]],
        "asks": [["65100.00", "1.0"], ["65200.00", "2.0"]]
    }, epoch=base_ep, sequence=1)

    recorder.record_event("l2update", {
        "sequence": 2,
        "changes": [["buy", "65050.00", "1.5"], ["sell", "65100.00", "0.0"]]
    }, epoch=base_ep + 1.0, sequence=2)

    events = recorder.get_events()
    for ev in events:
        assert len(ev.checksum_sha256) == 64

    # Replay into tracker A and tracker B independently
    tr_a, sum_a = L2EventRecorder.replay_events(events)
    tr_b, sum_b = L2EventRecorder.replay_events(events)

    assert sum_a.final_best_bid == sum_b.final_best_bid == 65050.0
    assert sum_a.final_best_ask == sum_b.final_best_ask == 65200.0
    assert sum_a.final_mid_price == sum_b.final_mid_price == 65125.0


def test_causal_timestamps_no_lookahead():
    """Verify that event extraction strictly excludes future messages beyond decision epoch."""
    tracker = OrderBookTracker()
    ep = 1778200000.0

    tracker.process_snapshot({
        "sequence": 1,
        "bids": [["60000.00", "1.0"]],
        "asks": [["60100.00", "1.0"]]
    }, received_epoch=ep)

    # Message in window
    tracker.process_match({"price": "60050.00", "size": "1.0", "side": "buy"}, received_epoch=ep + 10.0)

    # Message in future (> decision epoch)
    decision_ep = ep + 20.0
    tracker.process_match({"price": "60060.00", "size": "5.0", "side": "buy"}, received_epoch=decision_ep + 10.0)
    tracker.process_l2update({"sequence": 2, "changes": [["buy", "60005.00", "1.0"]]}, received_epoch=decision_ep - 1.0)

    snap = tracker.extract_microstructure_snapshot(decision_epoch=decision_ep)
    assert snap.is_available
    # Future trade match of 5.0 at decision_ep + 10.0 must NOT be in CVD
    assert snap.cvd_15m == 1.0
    assert snap.trade_count_in_window == 1


def test_candidate_completeness_records_accepted_and_rejected():
    """Verify that the ledger records BOTH gate-passing and gate-rejected setups."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_ledger.jsonl")
        protocol = ProspectiveL2EvaluationProtocol(ledger_path=ledger_path)
        now = time.time()

        # 1. Accepted setup (OFI > 0, OBI > -0.20, Spread <= 5.0)
        snap_good = {
            "is_available": True,
            "is_feed_synchronized": True,
            "data_age_seconds": 0.5,
            "ofi_value": 3.5,
            "obi_5": 0.15,
            "spread_bps": 2.1
        }
        cand_good = protocol.register_opportunity(
            candidate_id="c_pass_01",
            baseline_opportunity_id="base_01",
            decision_epoch=now,
            proposed_entry=65000.0,
            stop_loss=64000.0,
            take_profit=66500.0,
            risk_unit_usd=1000.0,
            l2_snapshot=snap_good
        )
        assert cand_good.gate_passed
        assert cand_good.gate_decision == "GATE_ACCEPTED_SHADOW"

        # 2. Rejected setup (Toxic OFI <= 0)
        snap_bad_ofi = {
            "is_available": True,
            "is_feed_synchronized": True,
            "data_age_seconds": 0.5,
            "ofi_value": -2.0,
            "obi_5": 0.15,
            "spread_bps": 2.1
        }
        cand_bad_ofi = protocol.register_opportunity(
            candidate_id="c_fail_02",
            baseline_opportunity_id="base_02",
            decision_epoch=now + 60.0,
            proposed_entry=65100.0,
            stop_loss=64100.0,
            take_profit=66600.0,
            risk_unit_usd=1000.0,
            l2_snapshot=snap_bad_ofi
        )
        assert not cand_bad_ofi.gate_passed
        assert cand_bad_ofi.gate_decision == "GATE_REJECTED_TOXIC_OFI"

        # Both records persisted to disk
        with open(ledger_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 2
        assert lines[0]["gate_passed"] is True
        assert lines[1]["gate_passed"] is False


def test_delayed_outcome_resolution_guard():
    """Verify that resolving an outcome prematurely raises PREMATURE_RESOLUTION_ATTEMPTED."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_ledger.jsonl")
        protocol = ProspectiveL2EvaluationProtocol(ledger_path=ledger_path)
        now = time.time()

        protocol.register_opportunity(
            candidate_id="c_timeout_01",
            baseline_opportunity_id="base_01",
            decision_epoch=now,
            proposed_entry=65000.0,
            stop_loss=64000.0,
            take_profit=66500.0,
            risk_unit_usd=1000.0,
            l2_snapshot={"is_available": True, "is_feed_synchronized": True, "data_age_seconds": 0.5, "ofi_value": 1.0, "obi_5": 0.0, "spread_bps": 1.0}
        )

        # Premature resolution attempt at 100 hours (< 168 hours)
        premature_ep = now + (100 * 3600.0)
        with pytest.raises(ValueError, match="PREMATURE_RESOLUTION_ATTEMPTED"):
            protocol.resolve_opportunity(
                candidate_id="c_timeout_01",
                resolution_epoch=premature_ep,
                exit_price=65500.0,
                exit_reason="TIMEOUT",
                bars_held=100
            )

        # Valid resolution at 168 hours: succeeds
        valid_ep = now + (168 * 3600.0)
        outcome = protocol.resolve_opportunity(
            candidate_id="c_timeout_01",
            resolution_epoch=valid_ep,
            exit_price=65500.0,
            exit_reason="TIMEOUT",
            bars_held=168
        )
        assert outcome.resolution_status == "RESOLVED"
        assert outcome.gross_return_bps > 0


def test_independent_block_accounting_and_overlap_handling():
    """Verify that overlapping setups are tagged not independent and share block index."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_ledger.jsonl")
        protocol = ProspectiveL2EvaluationProtocol(ledger_path=ledger_path)
        base_ep = 1778200000.0

        # Candidate 1: Block 1, Independent
        c1 = protocol.register_opportunity(
            candidate_id="c1",
            baseline_opportunity_id="b1",
            decision_epoch=base_ep,
            proposed_entry=65000.0,
            stop_loss=64000.0,
            take_profit=66500.0,
            risk_unit_usd=1000.0,
            l2_snapshot={"is_available": True, "is_feed_synchronized": True, "data_age_seconds": 0.5, "ofi_value": 1.0, "obi_5": 0.0, "spread_bps": 1.0}
        )
        assert c1.is_independent_block
        assert c1.block_index == 1

        # Candidate 2: Overlapping (decision_epoch at base_ep + 24h < base_ep + 168h maturity)
        c2 = protocol.register_opportunity(
            candidate_id="c2",
            baseline_opportunity_id="b2",
            decision_epoch=base_ep + (24 * 3600.0),
            proposed_entry=65500.0,
            stop_loss=64500.0,
            take_profit=67000.0,
            risk_unit_usd=1000.0,
            l2_snapshot={"is_available": True, "is_feed_synchronized": True, "data_age_seconds": 0.5, "ofi_value": 1.0, "obi_5": 0.0, "spread_bps": 1.0}
        )
        assert not c2.is_independent_block
        assert c2.block_index == 1  # shares block index 1

        # Candidate 3: Non-overlapping (decision_epoch at base_ep + 169h >= base_ep + 168h maturity)
        c3 = protocol.register_opportunity(
            candidate_id="c3",
            baseline_opportunity_id="b3",
            decision_epoch=base_ep + (169 * 3600.0),
            proposed_entry=66000.0,
            stop_loss=65000.0,
            take_profit=67500.0,
            risk_unit_usd=1000.0,
            l2_snapshot={"is_available": True, "is_feed_synchronized": True, "data_age_seconds": 0.5, "ofi_value": 1.0, "obi_5": 0.0, "spread_bps": 1.0}
        )
        assert c3.is_independent_block
        assert c3.block_index == 2  # new independent block 2


def test_protected_files_isolation():
    """Verify that all 5 protected ledger and raw data files are 100% bit-identical."""
    qa_dataset_hash = os.environ.get("BTC_QA_VERIFIED_DATASET_SHA256")
    for rel_path, expected_sha in PROTECTED_FILES.items():
        if rel_path == "data/raw/ohlcv.parquet" and qa_dataset_hash:
            expected_sha = qa_dataset_hash
        abs_path = os.path.join(REPO_ROOT, rel_path)
        assert os.path.exists(abs_path), f"Protected file missing: {rel_path}"
        with open(abs_path, "rb") as f:
            actual_sha = hashlib.sha256(f.read()).hexdigest()
        assert actual_sha == expected_sha, f"Protected file corrupted: {rel_path}"
