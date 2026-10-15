"""
tests/test_shadow_mode_decision.py — Phase 8 & 9 Shadow Decision Engine Tests
=============================================================================
Verifies:
1. Origin hash commitment is computed and record is persisted immutably in SQLite.
2. Economic hurdle gating: requires net edge >= +10.0 bps over 35 bps base friction;
   sub-hurdle setups are strictly rejected with ABSTAIN_INSUFFICIENT_NET_EDGE.
3. Quality gating: stale feeds or degraded calibration trigger ABSTAIN_STALE_FEED or
   ABSTAIN_DEGRADED_CALIBRATION.
4. Immutable forward resolution: resolves at maturity without altering origin parameters or hash.
5. Anti-execution safety guard: execute_live_order raises RuntimeError.
"""

import pytest
import sqlite3
import tempfile
import os

from engine.forecasting_ladder import (
    MultiHorizonForecastOutput,
    ModelLadderTier
)
from engine.shadow_decision_engine import (
    ShadowDecisionEngine,
    DecisionGateStatus
)


@pytest.fixture
def temp_shadow_engine(tmp_path):
    test_db = str(tmp_path / "test_shadow_memory.db")
    return ShadowDecisionEngine(db_path=test_db)


@pytest.fixture
def mock_forecast():
    return MultiHorizonForecastOutput(
        forecast_id="fc_test_001",
        generation_timestamp="2026-08-30T12:00:00Z",
        horizon="24h",
        current_price=65000.0,
        model_tier=ModelLadderTier.CHALLENGER_C_QUANTILE,
        model_version="test-model-v1",
        feature_schema_version="pit_v1.0.0",
        return_p10=-0.03,
        return_p50=0.005,
        return_p90=0.04,
        price_lower_p10=63050.0,
        price_mid_p50=65325.0,
        price_upper_p90=67600.0,
        forecast_vol_annualized=0.55,
        interval_width_pct=7.0,
        empirical_coverage_pct=91.0,
        directional_state="NO_DIRECTIONAL_EDGE"
    )


def test_origin_hash_commitment_and_sqlite_persistence(temp_shadow_engine, mock_forecast):
    """Shadow decision records have SHA256 origin commitment and persist in SQLite."""
    rec = temp_shadow_engine.evaluate_decision_gate(
        forecast=mock_forecast,
        feed_freshness_status="FRESH",
        calibration_coverage_pct=91.0,
        directional_signal="NONE"
    )

    assert len(rec.origin_commitment_hash) == 64
    assert rec.gate_status == DecisionGateStatus.ABSTAIN_NO_DIRECTIONAL_EDGE
    assert rec.proposed_action == "ABSTAIN"
    assert rec.is_resolved is False
    assert rec.live_trading_prohibited is True

    # Check database persistence
    conn = sqlite3.connect(temp_shadow_engine.db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM shadow_decision_records WHERE record_id = ?", (rec.record_id,)).fetchone()
    conn.close()

    assert row is not None
    assert row["origin_commitment_hash"] == rec.origin_commitment_hash
    assert row["is_resolved"] == 0


def test_economic_hurdle_gate_rejection(temp_shadow_engine, mock_forecast):
    """Sub-hurdle setup (gross edge < 45 bps) is rejected with ABSTAIN_INSUFFICIENT_NET_EDGE."""
    # Gross edge = 40 bps. Base friction = 35 bps. Net edge = +5 bps (less than +10 bps hurdle)
    rec = temp_shadow_engine.evaluate_decision_gate(
        forecast=mock_forecast,
        feed_freshness_status="FRESH",
        calibration_coverage_pct=91.0,
        estimated_gross_return_bps=40.0,
        directional_signal="LONG"
    )

    assert rec.gate_status == DecisionGateStatus.ABSTAIN_INSUFFICIENT_NET_EDGE
    assert rec.proposed_action == "ABSTAIN"
    assert rec.expected_net_edge_bps == 5.0
    assert rec.economic_hurdle_bps == 10.0


def test_economic_hurdle_gate_approval(temp_shadow_engine, mock_forecast):
    """Setup clearing economic hurdle (gross edge = 80 bps -> net edge = +45 bps) records research candidate."""
    rec = temp_shadow_engine.evaluate_decision_gate(
        forecast=mock_forecast,
        feed_freshness_status="FRESH",
        calibration_coverage_pct=91.0,
        estimated_gross_return_bps=80.0,
        directional_signal="LONG"
    )

    assert rec.gate_status == DecisionGateStatus.RESEARCH_DECISION_RECORDED
    assert rec.proposed_action == "RESEARCH_LONG"
    assert rec.expected_net_edge_bps == 45.0


def test_quality_gating_abstention(temp_shadow_engine, mock_forecast):
    """Stale feeds and degraded calibration trigger immediate abstention."""
    # Stale feed
    rec_stale = temp_shadow_engine.evaluate_decision_gate(
        forecast=mock_forecast,
        feed_freshness_status="STALE",
        directional_signal="LONG"
    )
    assert rec_stale.gate_status == DecisionGateStatus.ABSTAIN_STALE_FEED

    # Degraded calibration (< 85%)
    rec_deg = temp_shadow_engine.evaluate_decision_gate(
        forecast=mock_forecast,
        feed_freshness_status="FRESH",
        calibration_coverage_pct=82.0,
        directional_signal="LONG"
    )
    assert rec_deg.gate_status == DecisionGateStatus.ABSTAIN_DEGRADED_CALIBRATION


def test_immutable_forward_resolution(temp_shadow_engine, mock_forecast):
    """Resolving outcome at maturity updates resolution fields without mutating origin parameters."""
    rec = temp_shadow_engine.evaluate_decision_gate(
        forecast=mock_forecast,
        feed_freshness_status="FRESH",
        calibration_coverage_pct=91.0,
        estimated_gross_return_bps=80.0,
        directional_signal="LONG"
    )
    orig_hash = rec.origin_commitment_hash

    # Resolve at maturity with actual price = 66300.0 (inside [63050, 67600])
    res_rec = temp_shadow_engine.resolve_decision_outcome(
        record_id=rec.record_id,
        actual_price=66300.0,
        resolution_timestamp_iso="2026-08-31T12:00:00Z"
    )

    assert res_rec is not None
    assert res_rec.is_resolved is True
    assert res_rec.was_contained is True
    assert res_rec.actual_price_at_maturity == 66300.0
    assert res_rec.origin_commitment_hash == orig_hash  # Unmutated origin hash!
    # Expected return = (66300 - 65000) / 65000 * 10000 = +200 bps
    # Net realized PnL = +200 - 35 = +165 bps
    assert res_rec.actual_return_bps == 200.0
    assert res_rec.realized_net_pnl_bps == 165.0


def test_live_capital_execution_permanently_prohibited(temp_shadow_engine):
    """Invoking order execution raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Live capital execution is permanently disabled"):
        temp_shadow_engine.execute_live_order(symbol="BTC/USD", amount=1.0)
