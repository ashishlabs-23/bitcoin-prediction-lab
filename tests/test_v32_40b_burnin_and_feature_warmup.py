"""
tests/test_v32_40b_burnin_and_feature_warmup.py — Unit & Boundary Tests for Feature-Window Warm-Up
===================================================================================================
BTCognitive V32.40B: Burn-In Integrity Audit & Causal Feature Warm-Up Gate Verification

Verifies:
1. Snapshot populates instantaneous book features (OBI_5, OBI_10, spread_bps, depth) immediately upon sync.
2. Initial snapshot does NOT supply historical order flow; OFI windows (1m, 5m, 15m) are strictly unavailable during warm-up.
3. OFI_1m unavailable for elapsed < 60.0s; becomes available at exactly 60.0s with valid updates.
4. OFI_5m unavailable for elapsed < 300.0s; becomes available at exactly 300.0s with valid updates.
5. OFI_15m unavailable for elapsed < 900.0s; becomes available at exactly 900.0s with valid updates.
6. Sequence gaps immediately reset synchronization and invalidate warm-up; requiring fresh snapshot and full 15m post-gap history.
7. Reconnect / manual reset invalidates warm-up and forces full re-qualification.
8. Heartbeat staleness (>5.0s) immediately marks all features unavailable fail-closed.
9. Shadow gating engine cleanly returns GATE_ABSTAIN_L2_UNAVAILABLE during warm-up (ofi_value is None), not toxic rejection.
"""

import pytest
import time
from typing import Dict, Any

from engine.l2_microstructure_features import (
    OrderBookTracker,
    L2MicrostructureSnapshot,
    compute_obi,
    compute_spread_bps,
    compute_ofi_from_top_of_book_events,
)
from engine.prospective_l2_shadow_gating import L2ShadowGatingEngine


def test_snapshot_supplies_book_state_not_order_flow():
    """
    Test 1: An initial snapshot establishes instantaneous book state (OBI_5, spread, depth)
    but does NOT supply order flow. OFI_15m must remain None and feature_status must show WARMING_UP.
    """
    tracker = OrderBookTracker()
    ep = 1792900000.0
    tracker.process_snapshot({
        "type": "snapshot",
        "sequence": 1000,
        "bids": [[f"{80000 - i * 10}.00", f"{1.0 + i * 0.1}"] for i in range(25)],
        "asks": [[f"{80010 + i * 10}.00", f"{1.0 + i * 0.1}"] for i in range(25)]
    }, received_epoch=ep)

    # 1 second after snapshot (like the 15-second smoke test)
    snap = tracker.extract_microstructure_snapshot(decision_epoch=ep + 1.0)
    assert snap.is_available is True
    assert snap.is_feed_synchronized is True
    assert snap.best_bid == 80000.0
    assert snap.best_ask == 80010.0
    assert snap.mid_price == 80005.0
    assert snap.spread_bps > 0.0
    assert snap.obi_5 is not None
    assert snap.bid_depth_5 > 0.0

    # Instantaneous book features are READY
    assert snap.feature_status.get("spread_bps") == "READY"
    assert snap.feature_status.get("obi_5") == "READY"

    # Rolling window features MUST be warming up
    assert snap.ofi_15m is None
    assert snap.ofi_5m is None
    assert snap.ofi_1m is None
    assert snap.ofi_value is None
    assert "WARMING_UP" in snap.feature_status.get("ofi_15m", "")
    assert "WARMING_UP" in snap.feature_status.get("ofi_5m", "")
    assert "WARMING_UP" in snap.feature_status.get("ofi_1m", "")
    assert snap.is_window_warmed_up is False
    assert snap.is_feature_available("ofi_15m") is False
    assert snap.is_feature_available("obi_5") is True


def test_exact_window_boundary_transitions():
    """
    Test 2: Test exact boundary transitions for 1m (60s), 5m (300s), and 15m (900s).
    """
    tracker = OrderBookTracker()
    t0 = 1792900000.0
    tracker.process_snapshot({
        "type": "snapshot",
        "sequence": 1,
        "bids": [["80000.00", "5.0"], ["79990.00", "10.0"]],
        "asks": [["80010.00", "5.0"], ["80020.00", "10.0"]]
    }, received_epoch=t0)

    # Add periodic updates every 10 seconds up to 1000 seconds
    for step in range(1, 101):
        ts = t0 + step * 10.0
        tracker.process_l2update({
            "type": "l2update",
            "sequence": step + 1,
            "changes": [["buy", "80001.00", "5.0"]] if step % 2 == 1 else [["buy", "80000.00", "5.0"]]
        }, received_epoch=ts)

    # A. 59.9s -> OFI_1m warming up
    snap_59 = tracker.extract_microstructure_snapshot(decision_epoch=t0 + 59.9)
    assert snap_59.ofi_1m is None
    assert snap_59.is_feature_available("ofi_1m") is False

    # B. 60.0s -> OFI_1m ready
    snap_60 = tracker.extract_microstructure_snapshot(decision_epoch=t0 + 60.0)
    assert snap_60.ofi_1m is not None
    assert snap_60.is_feature_available("ofi_1m") is True
    assert snap_60.ofi_5m is None
    assert snap_60.ofi_15m is None

    # C. 299.9s -> OFI_5m warming up
    snap_299 = tracker.extract_microstructure_snapshot(decision_epoch=t0 + 299.9)
    assert snap_299.ofi_5m is None
    assert snap_299.is_feature_available("ofi_5m") is False

    # D. 300.0s -> OFI_5m ready
    snap_300 = tracker.extract_microstructure_snapshot(decision_epoch=t0 + 300.0)
    assert snap_300.ofi_5m is not None
    assert snap_300.is_feature_available("ofi_5m") is True
    assert snap_300.ofi_15m is None

    # E. 899.9s -> OFI_15m warming up
    snap_899 = tracker.extract_microstructure_snapshot(decision_epoch=t0 + 899.9)
    assert snap_899.ofi_15m is None
    assert snap_899.ofi_value is None
    assert snap_899.is_window_warmed_up is False
    assert snap_899.is_feature_available("ofi_15m") is False

    # F. 900.0s -> OFI_15m ready
    snap_900 = tracker.extract_microstructure_snapshot(decision_epoch=t0 + 900.0)
    assert snap_900.ofi_15m is not None
    assert snap_900.ofi_value == snap_900.ofi_15m
    assert snap_900.is_window_warmed_up is True
    assert snap_900.is_feature_available("ofi_15m") is True


def test_sequence_gap_invalidates_continuous_history_and_forces_rewarm():
    """
    Test 3: A sequence gap breaks stream continuity. Features must fail closed immediately,
    and post-recovery snapshot resets sync_epoch, requiring a full 15-minute re-warm.
    """
    tracker = OrderBookTracker()
    t0 = 1792900000.0
    tracker.process_snapshot({
        "type": "snapshot",
        "sequence": 100,
        "bids": [["80000.00", "2.0"]],
        "asks": [["80010.00", "2.0"]]
    }, received_epoch=t0)

    # Simulate 950 seconds of healthy streaming
    for i in range(1, 96):
        tracker.process_l2update({
            "sequence": 100 + i,
            "changes": [["buy", "80001.00", "2.0"]]
        }, received_epoch=t0 + i * 10.0)

    # At 950s, 15m window was ready
    snap_before_gap = tracker.extract_microstructure_snapshot(decision_epoch=t0 + 950.0)
    assert snap_before_gap.ofi_15m is not None
    assert snap_before_gap.is_feature_available("ofi_15m") is True

    # Induce sequence gap: expected 196, receive 210 (+14 gap)
    t_gap = t0 + 955.0
    gap_ok = tracker.process_l2update({
        "sequence": 210,
        "changes": [["buy", "80005.00", "1.0"]]
    }, received_epoch=t_gap)
    assert gap_ok is False
    assert tracker.is_synchronized is False
    assert tracker.sequence_gaps_count == 1

    # Immediate snapshot extraction must fail closed
    snap_gap = tracker.extract_microstructure_snapshot(decision_epoch=t_gap + 0.1)
    assert snap_gap.is_available is False
    assert "L2_FEED_DESYNCHRONIZED" in snap_gap.reason_code
    assert snap_gap.feature_status.get("ofi_15m") == "UNAVAILABLE_DESYNCHRONIZED"

    # Reconnection: New snapshot at t_recovery
    t_rec = t_gap + 2.0
    tracker.process_snapshot({
        "type": "snapshot",
        "sequence": 300,
        "bids": [["80000.00", "2.0"]],
        "asks": [["80010.00", "2.0"]]
    }, received_epoch=t_rec)
    assert tracker.is_synchronized is True

    # 1.0 seconds post-recovery: OBI_5 is ready, but OFI_15m MUST be warming up again!
    snap_post_rec = tracker.extract_microstructure_snapshot(decision_epoch=t_rec + 1.0)
    assert snap_post_rec.is_available is True
    assert snap_post_rec.is_feature_available("obi_5") is True
    assert snap_post_rec.ofi_15m is None
    assert snap_post_rec.is_feature_available("ofi_15m") is False
    assert "WARMING_UP" in snap_post_rec.feature_status.get("ofi_15m", "")


def test_reconnect_reset_forces_rewarm():
    """
    Test 4: tracker.reset() on connection drop invalidates sync_epoch and warm-up state.
    """
    tracker = OrderBookTracker()
    t0 = 1792900000.0
    tracker.process_snapshot({
        "sequence": 1,
        "bids": [["80000.00", "1.0"]],
        "asks": [["80010.00", "1.0"]]
    }, received_epoch=t0)

    # Reset (as done on reconnect)
    tracker.reset(reason="WEBSOCKET_RECONNECT")
    assert tracker.is_synchronized is False
    assert tracker.sync_epoch is None

    snap = tracker.extract_microstructure_snapshot(decision_epoch=t0 + 1000.0)
    assert snap.is_available is False
    assert snap.feature_status.get("ofi_15m") == "UNAVAILABLE_DESYNCHRONIZED"


def test_heartbeat_staleness_fails_closed():
    """
    Test 5: Heartbeat stall (>5.0s) causes fail-closed snapshot and unavailable features.
    """
    tracker = OrderBookTracker()
    t0 = 1792900000.0
    tracker.process_snapshot({
        "sequence": 1,
        "bids": [["80000.00", "1.0"]],
        "asks": [["80010.00", "1.0"]]
    }, received_epoch=t0)

    # 6.0 seconds without heartbeat/update
    snap_stale = tracker.extract_microstructure_snapshot(decision_epoch=t0 + 6.0, max_staleness_seconds=5.0)
    assert snap_stale.is_available is False
    assert "L2_DATA_STALE" in snap_stale.reason_code
    assert snap_stale.feature_status.get("spread_bps") == "UNAVAILABLE_STALE"
    assert snap_stale.feature_status.get("ofi_15m") == "UNAVAILABLE_STALE"


def test_gating_abstains_during_warmup_without_toxic_rejection():
    """
    Test 6: When ofi_value is None during warm-up, L2ShadowGatingEngine returns
    GATE_ABSTAIN_L2_UNAVAILABLE, NOT GATE_REJECTED_TOXIC_OFI.
    """
    engine = L2ShadowGatingEngine()
    snap_warming = L2MicrostructureSnapshot(
        is_available=True,
        reason_code=None,
        observation_time_utc="2026-10-25T14:00:00Z",
        observation_epoch=1792900000.0,
        best_bid=80000.0,
        best_ask=80010.0,
        mid_price=80005.0,
        spread_bps=1.25,
        obi_5=0.10,
        obi_10=0.10,
        obi_25=0.10,
        ofi_value=None,  # Warming up!
        cvd_value=0.0,
        trade_count_in_window=0,
        book_updates_in_window=5,
        data_age_seconds=0.1,
        is_feed_synchronized=True,
        feature_status={"ofi_15m": "UNAVAILABLE_WARMING_UP (elapsed=15.0s < 900.0s)"}
    )

    dec, reason = engine.evaluate_gate(snap_warming)
    assert dec == "GATE_ABSTAIN_L2_UNAVAILABLE"
    assert "warming up" in reason.lower()
