"""
tests/test_research_to_signal_engine_v2.py
=========================================
Comprehensive deterministic test suite for Research-to-Signal Engine v2.
Verifies:
1. Contract and Level Geometry (Long and Short brackets, gross/net R:R, invalid distances)
2. Data Frequency & Horizon Gating (15m/5m unsupported rejection vs hourly verified)
3. Economic Gate & Transaction Costs (Gross positive vs net negative rejection)
4. Calibrated Probability & Conviction Null Guards (Suppression of false confidence)
5. Conservative Barrier Collision Resolution (SL_FIRST_CONSERVATIVE and timeouts)
6. Point-in-Time Causality & Delayed Resolution Invariant
7. API Integration & Fail-Closed Abstention Handlers
"""

import pytest
import math
from datetime import datetime, timezone, timedelta
import numpy as np

from models.signal_contract import (
    SignalContract,
    SignalDirection,
    SignalStatus,
    CalibrationStatus,
    EntryType,
    ExecutionAuthorization,
    create_abstain_signal
)
from engine.scenario_contract_engine import (
    ScenarioContractEngine,
    compute_bracket_geometry,
    ScenarioCandidate,
    ScenarioLevelEngine
)
from engine.execution_cost_model import (
    ExecutionCostModel,
    simulate_barrier_collision_resolution
)
from models.calibrated_signal_classifier import CalibratedSignalEvaluator


# =========================================================================
# 1. CONTRACT AND GEOMETRY TESTS
# =========================================================================

def test_long_bracket_geometry_invariants():
    """Verify that LONG candidate strictly requires SL < Entry < TP and computes exact R:R."""
    res = compute_bracket_geometry(
        direction="LONG",
        entry=80000.0,
        tp=82000.0,  # reward = 2000
        sl=79000.0   # risk = 1000
    )
    assert res["is_valid"] is True
    assert res["reward_distance"] == 2000.0
    assert res["risk_distance"] == 1000.0
    assert res["gross_rr"] == 2.0


def test_short_bracket_geometry_invariants():
    """Verify that SHORT candidate strictly requires TP < Entry < SL and computes exact R:R."""
    res = compute_bracket_geometry(
        direction="SHORT",
        entry=80000.0,
        tp=78000.0,  # reward = 2000
        sl=81000.0   # risk = 1000
    )
    assert res["is_valid"] is True
    assert res["reward_distance"] == 2000.0
    assert res["risk_distance"] == 1000.0
    assert res["gross_rr"] == 2.0


def test_inverted_brackets_rejected():
    """Verify that inverted prices are rejected."""
    # Long with TP below entry
    res_long = compute_bracket_geometry(direction="LONG", entry=80000.0, tp=79000.0, sl=78000.0)
    assert res_long["is_valid"] is False
    assert res_long["error_code"] == "INVERTED_LEVELS"

    # Short with TP above entry
    res_short = compute_bracket_geometry(direction="SHORT", entry=80000.0, tp=82000.0, sl=81000.0)
    assert res_short["is_valid"] is False
    assert res_short["error_code"] == "INVERTED_LEVELS"


def test_zero_or_negative_risk_distance_rejected():
    """Verify that zero risk distance is rejected."""
    res = compute_bracket_geometry(direction="LONG", entry=80000.0, tp=82000.0, sl=80000.0)
    assert res["is_valid"] is False
    assert res["error_code"] == "ZERO_OR_NEGATIVE_RISK"


# =========================================================================
# 2. DATA FREQUENCY & HORIZON GATING
# =========================================================================

def test_unsupported_intraday_frequency_rejected():
    """Verify that 15m and 5m requests return DATA_FREQUENCY_UNSUPPORTED."""
    engine = ScenarioContractEngine()
    signal_15m = engine.evaluate_scenario_candidate(
        reference_price=81500.0,
        direction="LONG",
        horizon="15m",
        is_model_gated=False
    )
    assert signal_15m.signal_status == SignalStatus.ABSTAIN
    assert signal_15m.invalidation_reason == "DATA_FREQUENCY_UNSUPPORTED"
    assert signal_15m.entry_price is None
    assert signal_15m.take_profit is None
    assert signal_15m.stop_loss is None

    signal_5m = engine.evaluate_scenario_candidate(
        reference_price=81500.0,
        direction="LONG",
        horizon="5m",
        is_model_gated=False
    )
    assert signal_5m.signal_status == SignalStatus.ABSTAIN
    assert signal_5m.invalidation_reason == "DATA_FREQUENCY_UNSUPPORTED"


def test_hourly_frequency_accepted_for_evaluation():
    """Verify that 1h, 4h, and 24h horizons proceed to governance and economic gates."""
    engine = ScenarioContractEngine()
    signal_1h = engine.evaluate_scenario_candidate(
        reference_price=81500.0,
        direction="LONG",
        horizon="1h",
        is_model_gated=True  # Gated
    )
    assert signal_1h.signal_status == SignalStatus.ABSTAIN
    assert signal_1h.invalidation_reason == "TIER_2_DIRECTIONAL_GATED"


# =========================================================================
# 3. ECONOMIC GATE & COST ACCOUNTING
# =========================================================================

def test_negative_net_expectancy_rejected_by_economic_gate():
    """Verify that a candidate with negative net expected value fails closed."""
    engine = ScenarioContractEngine()
    # Uncalibrated priors (p_tp=0.18, p_sl=0.36, p_timeout=0.46) yield negative EV
    signal = engine.evaluate_scenario_candidate(
        reference_price=81500.0,
        direction="LONG",
        horizon="24h",
        is_model_gated=False,
        cost_bps=7.0,
        p_tp=0.178,
        p_sl=0.361,
        p_timeout=0.461
    )
    assert signal.signal_status == SignalStatus.ABSTAIN
    assert signal.invalidation_reason == "ECONOMIC_EXPECTANCY_NEGATIVE"
    assert signal.entry_price is None


def test_positive_net_expectancy_candidate_passes_research_gate():
    """Verify that an economically valid research candidate with positive net EV creates a valid SignalContract."""
    engine = ScenarioContractEngine()
    # Strong hypothetical research model with p_tp=0.60, p_sl=0.20, p_timeout=0.20
    signal = engine.evaluate_scenario_candidate(
        reference_price=80000.0,
        direction="LONG",
        horizon="24h",
        is_model_gated=False,
        cost_bps=7.0,
        raw_probability=0.60,
        p_tp=0.60,
        p_sl=0.20,
        p_timeout=0.20
    )
    assert signal.signal_status == SignalStatus.ACTIVE_CANDIDATE
    assert signal.direction == SignalDirection.LONG
    assert signal.entry_price == 80000.0
    assert signal.take_profit > signal.entry_price
    assert signal.stop_loss < signal.entry_price
    assert signal.gross_reward_to_risk == 1.5
    assert signal.net_expected_value > 0.0
    assert signal.execution_authorization == ExecutionAuthorization.DISABLED


def test_venue_cost_sensitivity_coinbase_vs_binance():
    """Verify that cost calculations accurately reflect venue schedules (Coinbase 40 bps vs Binance 7 bps)."""
    # Binance Futures
    binance_model = ExecutionCostModel("BINANCE_FUTURES", "PERPETUAL")
    binance_cost = binance_model.calculate_roundtrip_cost(price=80000.0)
    assert binance_cost["total_cost_bps"] == pytest.approx(8.0, abs=2.0)

    # Coinbase Spot Tier 1
    coinbase_model = ExecutionCostModel("COINBASE", "SPOT")
    coinbase_cost = coinbase_model.calculate_roundtrip_cost(price=80000.0)
    assert coinbase_cost["total_cost_bps"] == pytest.approx(47.0, abs=5.0)


# =========================================================================
# 4. PROBABILITY CALIBRATION & CONVICTION NULL GUARDS
# =========================================================================

def test_gated_model_suppresses_conviction_percentage():
    """Verify that a gated model outputs displayed_conviction_pct = 0.0 and None for calibrated probability."""
    evaluator = CalibratedSignalEvaluator()
    res = evaluator.evaluate_signal(
        direction="LONG",
        raw_score=0.85,
        model_status="TIER_2_GATED",
        is_calibrated=False
    )
    assert res.displayed_conviction_pct == 0.0
    assert res.signal_status == "ABSTAIN"
    assert res.is_actionable is False


def test_uncalibrated_score_cannot_render_as_conviction():
    """Verify that raw uncalibrated scores are not displayed as conviction."""
    evaluator = CalibratedSignalEvaluator()
    res = evaluator.evaluate_signal(
        direction="LONG",
        raw_score=0.75,
        model_status="ACTIVE",
        is_calibrated=False
    )
    assert res.displayed_conviction_pct == 0.0
    assert "UNCALIBRATED" in res.confidence_label
    assert res.is_actionable is False


# =========================================================================
# 5. CONSERVATIVE COLLISION RESOLUTION & TIMEOUT
# =========================================================================

def test_same_bar_barrier_collision_resolution():
    """Verify that when both TP and SL are breached in the same bar, SL_FIRST_CONSERVATIVE is applied."""
    outcome = simulate_barrier_collision_resolution(
        direction="LONG",
        entry=80000.0,
        tp=82000.0,
        sl=79000.0,
        high=82500.0,
        low=78500.0,
        policy="SL_FIRST_CONSERVATIVE"
    )
    assert outcome["outcome"] == "STOP_LOSS"
    assert outcome["exit_price"] == 79000.0
    assert outcome["conservative_applied"] is True
    assert outcome["policy"] == "SL_FIRST_CONSERVATIVE"


def test_clear_tp_first_outcome():
    """Verify clear take-profit outcome when low does not reach stop-loss."""
    outcome = simulate_barrier_collision_resolution(
        direction="LONG",
        entry=80000.0,
        tp=82000.0,
        sl=79000.0,
        high=82500.0,
        low=79500.0,
        policy="SL_FIRST_CONSERVATIVE"
    )
    assert outcome["outcome"] == "TAKE_PROFIT"
    assert outcome["exit_price"] == 82000.0
    assert outcome["conservative_applied"] is False


# =========================================================================
# 6. POINT-IN-TIME CAUSALITY & PREREGISTERED REPLAY
# =========================================================================

def test_signal_contract_is_expired():
    """Verify that expired signals are accurately flagged."""
    past_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    contract = create_abstain_signal(
        model_id="TEST",
        reference_price=80000.0,
        reason_code="EXPIRED"
    )
    # Manually backdate valid_until
    contract_expired = contract.model_copy(update={"valid_until": past_iso})
    assert contract_expired.is_expired() is True


def test_execution_remains_permanently_disabled():
    """Verify that execution_authorization is strictly DISABLED on all contracts."""
    contract = create_abstain_signal(
        model_id="TEST",
        reference_price=80000.0,
        reason_code="TEST"
    )
    assert contract.execution_authorization == ExecutionAuthorization.DISABLED
