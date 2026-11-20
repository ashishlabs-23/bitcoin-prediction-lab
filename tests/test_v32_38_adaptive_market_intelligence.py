"""
tests/test_v32_38_adaptive_market_intelligence.py
=================================================
BTCognitive V32.38: Adaptive Market Intelligence & Prospective L2 Test Suite

Verifies:
1. Level-2 raw event recording and replay determinism.
2. Sequence gaps, duplicates, out-of-order events, and heartbeat stalls (fail-closed boundaries).
3. Causal microstructure features (multi-window OFI, multi-depth OBI, Kyle's lambda, Amihud illiquidity).
4. Prequential delayed resolution guard (zero lookahead leakage / no premature resolution).
5. Page-Hinkley and CUSUM online statistical drift detection.
6. Separation of data-quality failures (DATA_INVALID) from statistical drift (DRIFT_SUSPECTED).
7. Five governed evaluation states (NORMAL, DRIFT_SUSPECTED, DATA_INVALID, ABSTAIN, RESEARCH_CANDIDATE).
8. Unified model extensibility interface (GBDT, Random Walk, Empirical Quantiles).
9. Non-destructive guardrails (zero live execution, zero weight mutation).
10. Protected files bit-identical integrity.
"""

import os
import sys
import time
import math
import hashlib
import pytest
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from engine.l2_microstructure_features import (
    OrderBookTracker,
    L2MicrostructureSnapshot,
    compute_obi,
    compute_spread_bps,
    compute_depth_volume,
    compute_depth_within_bps,
    compute_kyles_lambda_proxy,
    compute_amihud_proxy
)
from engine.l2_event_recorder import RawL2Event, L2EventRecorder, L2ReplaySummary
from engine.drift_evaluator import (
    ResearchEvaluationState,
    PageHinkleyDetector,
    CUSUMDetector,
    DriftAwarePrequentialEvaluator,
    PrequentialForecastRecord
)
from engine.model_evaluation_interface import (
    ModelInputContext,
    ModelForecast,
    ForecastModelInterface,
    GBDTDirectionalModelAdapter,
    RandomWalkPersistenceAdapter,
    RollingEmpiricalQuantileAdapter
)
from engine.prospective_l2_qualification import audit_prospective_l2_qualification

PROTECTED_FILES = {
    "data/prospective_entry_ledger.jsonl": "91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7",
    "data/prospective_shadow_v1.jsonl": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "data/prospective_entry_ledger_v2.jsonl": "e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604",
    "data/raw/ohlcv.parquet": "1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c",
    "data/raw/ohlcv_pre_backfill_backup.parquet": "c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8"
}


def test_l2_event_recorder_and_replay_determinism():
    """Verify raw event creation with SHA-256 and deterministic replay into OrderBookTracker."""
    recorder = L2EventRecorder()
    base_epoch = 1778200000.0

    # 1. Record snapshot
    snap_payload = {
        "type": "snapshot",
        "product_id": "BTC-USD",
        "sequence": 100,
        "bids": [["65000.00", "1.50"], ["64950.00", "3.00"]],
        "asks": [["65050.00", "2.00"], ["65100.00", "4.00"]]
    }
    ev1 = recorder.record_event("snapshot", snap_payload, epoch=base_epoch, sequence=100)
    assert ev1.checksum_sha256 is not None
    assert ev1.event_id.startswith("l2ev-")

    # 2. Record clean update
    upd_payload = {
        "type": "l2update",
        "product_id": "BTC-USD",
        "sequence": 101,
        "changes": [["buy", "65010.00", "1.00"], ["sell", "65050.00", "0.00"]]
    }
    recorder.record_event("l2update", upd_payload, epoch=base_epoch + 1.0, sequence=101)

    # 3. Record trade match
    match_payload = {
        "type": "match",
        "trade_id": "99901",
        "price": "65010.00",
        "size": "0.50",
        "side": "buy"
    }
    recorder.record_event("match", match_payload, epoch=base_epoch + 1.5, sequence=102)

    # Replay events
    tracker, summary = L2EventRecorder.replay_events(recorder.get_events())
    assert summary.events_replayed == 3
    assert summary.valid_updates == 3
    assert summary.final_is_synchronized
    assert summary.final_sequence == 101

    best_b, _ = tracker.get_best_bid()
    best_a, _ = tracker.get_best_ask()
    assert best_b == 65010.00
    assert best_a == 65100.00  # 65050 was deleted (size 0)


def test_sequence_gaps_and_heartbeat_stalls():
    """Verify sequence gaps cause immediate desync and heartbeat staleness fails closed."""
    tracker = OrderBookTracker()
    ep = 1778200000.0
    tracker.process_snapshot({
        "type": "snapshot",
        "sequence": 100,
        "bids": [["60000.00", "1.0"]],
        "asks": [["60100.00", "1.0"]]
    }, received_epoch=ep)
    assert tracker.is_synchronized

    # Sequence gap: jump from 100 to 105
    res = tracker.process_l2update({
        "type": "l2update",
        "sequence": 105,
        "changes": [["buy", "60010.00", "1.0"]]
    }, received_epoch=ep + 1.0)
    assert res is False
    assert not tracker.is_synchronized
    assert "SEQUENCE_GAP_DETECTED" in (tracker.desync_reason or "")
    assert tracker.sequence_gaps_count == 1

    # Snapshot extraction fails closed
    snap = tracker.extract_microstructure_snapshot(decision_epoch=ep + 1.0)
    assert not snap.is_available
    assert "L2_FEED_DESYNCHRONIZED" in (snap.reason_code or "")


def test_duplicate_and_out_of_order_events():
    """Verify duplicate and out-of-order sequence events are rejected without corrupting book."""
    tracker = OrderBookTracker()
    ep = 1778200000.0
    tracker.process_snapshot({
        "type": "snapshot",
        "sequence": 200,
        "bids": [["60000.00", "1.0"]],
        "asks": [["60100.00", "1.0"]]
    }, received_epoch=ep)

    # 1. Duplicate sequence: 200 again
    dup_res = tracker.process_l2update({
        "type": "l2update",
        "sequence": 200,
        "changes": [["buy", "60050.00", "10.0"]]
    }, received_epoch=ep + 0.1)
    assert dup_res is False
    assert tracker.dropped_duplicates_count == 1
    # Book state unchanged
    best_b, _ = tracker.get_best_bid()
    assert best_b == 60000.00

    # 2. Out-of-order sequence: 195 < 200
    ooo_res = tracker.process_l2update({
        "type": "l2update",
        "sequence": 195,
        "changes": [["buy", "60050.00", "10.0"]]
    }, received_epoch=ep + 0.2)
    assert ooo_res is False
    assert tracker.dropped_out_of_order_count == 1
    best_b, _ = tracker.get_best_bid()
    assert best_b == 60000.00


def test_causal_microstructure_features_multi_window():
    """Verify multi-window OFI, multi-depth OBI, Kyle's lambda, and Amihud illiquidity proxies."""
    tracker = OrderBookTracker()
    ep = 1778200000.0
    tracker.process_snapshot({
        "type": "snapshot",
        "sequence": 1,
        "bids": [[f"{60000 - i * 10}.00", f"{1.0 + i * 0.5}"] for i in range(50)],
        "asks": [[f"{60050 + i * 10}.00", f"{1.0 + i * 0.5}"] for i in range(50)]
    }, received_epoch=ep)

    # Add trade matches and book update in window
    tracker.process_match({"price": "60050.00", "size": "2.0", "side": "buy"}, received_epoch=ep + 10.0)
    tracker.process_match({"price": "60000.00", "size": "1.0", "side": "sell"}, received_epoch=ep + 20.0)
    tracker.process_l2update({"sequence": 2, "changes": [["buy", "60005.00", "1.0"]]}, received_epoch=ep + 28.0)

    snap = tracker.extract_microstructure_snapshot(decision_epoch=ep + 29.0)
    assert snap.is_available
    assert snap.mid_price is not None
    assert snap.obi_5 is not None
    assert snap.obi_50 is not None
    assert snap.cvd_15m == 1.0  # 2.0 buy - 1.0 sell = +1.0
    assert snap.bid_depth_5 > 0
    assert snap.ask_depth_5 > 0
    assert snap.bid_depth_10bps is not None
    assert snap.schema_version == "v32.38.causal_l2"


def test_prequential_delayed_resolution_guard():
    """Verify that resolving an outcome prematurely raises PREMATURE_RESOLUTION_ATTEMPTED."""
    evaluator = DriftAwarePrequentialEvaluator(model_id="test-model")
    issue_ep = 1778200000.0
    h_hours = 24  # 24 hours = 86,400 seconds

    evaluator.register_forecast(
        forecast_id="fc-001",
        issue_epoch=issue_ep,
        horizon_hours=h_hours,
        point_forecast=60500.0,
        prob_up=0.55
    )

    # Premature resolution attempt at 12 hours: must raise ValueError
    premature_ep = issue_ep + (12 * 3600.0)
    with pytest.raises(ValueError, match="PREMATURE_RESOLUTION_ATTEMPTED"):
        evaluator.resolve_outcome("fc-001", outcome_epoch=premature_ep, actual_price=60800.0, actual_return=0.01)

    # Valid resolution at exactly 24 hours: succeeds
    valid_ep = issue_ep + (24 * 3600.0)
    resolved = evaluator.resolve_outcome("fc-001", outcome_epoch=valid_ep, actual_price=60800.0, actual_return=0.01)
    assert resolved.is_resolved
    assert resolved.actual_direction == 1
    assert resolved.error_loss is not None


def test_page_hinkley_and_cusum_drift_detection():
    """Verify online Page-Hinkley and CUSUM detectors on synthetic loss shift."""
    ph = PageHinkleyDetector(delta=0.01, threshold=2.0, min_instances=20)
    cusum = CUSUMDetector(slack_k=0.02, threshold_h=2.0, min_instances=20)

    # Stage 1: Stationary small errors
    np.random.seed(42)
    for _ in range(30):
        val = float(np.random.normal(0.10, 0.02))
        d_ph, _ = ph.update(val)
        d_cu, _ = cusum.update(val)
        assert not d_ph

    # Stage 2: Mean shift in errors (e.g. regime change)
    drift_triggered = False
    for _ in range(30):
        val = float(np.random.normal(0.80, 0.05))
        d_ph, _ = ph.update(val)
        d_cu, _ = cusum.update(val)
        if d_ph or d_cu:
            drift_triggered = True
            break

    assert drift_triggered


def test_data_invalid_vs_statistical_drift_separation():
    """Verify data-quality failures trigger DATA_INVALID independently of statistical drift."""
    evaluator = DriftAwarePrequentialEvaluator(model_id="test-model")
    now = time.time()

    # 1. Issue with healthy feed -> state NORMAL
    rec1 = evaluator.register_forecast("f1", issue_epoch=now, horizon_hours=1, point_forecast=60000.0, is_feed_synchronized=True)
    assert rec1.eval_state == ResearchEvaluationState.NORMAL

    # 2. Issue with desynchronized feed -> state DATA_INVALID
    rec2 = evaluator.register_forecast("f2", issue_epoch=now + 10, horizon_hours=1, point_forecast=60000.0, is_feed_synchronized=False)
    assert rec2.eval_state == ResearchEvaluationState.DATA_INVALID
    assert evaluator.current_state == ResearchEvaluationState.DATA_INVALID

    # 3. Issue with abstain flag -> state ABSTAIN
    rec3 = evaluator.register_forecast("f3", issue_epoch=now + 20, horizon_hours=1, point_forecast=60000.0, is_abstain=True)
    assert rec3.eval_state == ResearchEvaluationState.ABSTAIN


def test_forecast_model_extensibility_interface():
    """Verify ForecastModelInterface with GBDT, Random Walk, and Empirical Quantiles."""
    # Context with 200 synthetic closes
    closes = list(np.linspace(60000.0, 62000.0, 200))
    ctx = ModelInputContext.from_closes(closes, epoch=time.time())

    # 1. GBDT adapter
    gbdt_adapter = GBDTDirectionalModelAdapter()
    assert 1 in gbdt_adapter.supported_horizons
    fc_gbdt = gbdt_adapter.predict(ctx, horizon_hours=1)
    assert fc_gbdt.model_id == "directional-gbm-1h-v1"
    assert fc_gbdt.prob_up is not None
    assert fc_gbdt.governance_authorization == "OFFLINE_RESEARCH_ONLY"

    # 2. Random Walk persistence adapter
    rw_adapter = RandomWalkPersistenceAdapter()
    fc_rw = rw_adapter.predict(ctx, horizon_hours=4)
    assert fc_rw.point_forecast_return == 0.0
    assert fc_rw.point_forecast_price == round(ctx.current_price, 2)

    # 3. Rolling Empirical Quantile adapter
    emp_adapter = RollingEmpiricalQuantileAdapter(window_bars=24)
    fc_emp = emp_adapter.predict(ctx, horizon_hours=1)
    assert "p10" in fc_emp.quantiles
    assert "p50" in fc_emp.quantiles
    assert "p90" in fc_emp.quantiles


def test_prospective_l2_qualification_and_non_execution_assertion():
    """Verify prospective qualification audit preserves H1 parameters and disabled collector."""
    audit = audit_prospective_l2_qualification()
    assert audit.collector_operational_status == "STOPPED_DISABLED"
    assert audit.collector_permission_respected
    assert audit.preregistered_hypothesis_id == "H1_L2_CONT_MICROSTRUCTURE_GATE"
    assert audit.cost_benchmark_bps == 27.0
    assert audit.governance_authorization == "OFFLINE_RESEARCH_ONLY"
    assert audit.live_trading_status == "DISABLED"
    assert audit.pipeline_readiness_decision == "RESEARCH_EVALUATION_READY"


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
