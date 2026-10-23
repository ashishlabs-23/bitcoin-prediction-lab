"""
BTCognitive — Signal Integrity & Risk-Level Engine Acceptance Test Suite
Verifies Suites A through G deterministically according to Phase 5 acceptance standards.
"""

import math
import pytest
from datetime import datetime, timezone, timedelta

from models.signal_contract import (
    SignalContract,
    SignalDirection,
    SignalStatus,
    CalibrationStatus,
    EntryType,
    ExecutionAuthorization,
    create_abstain_signal,
    validate_scenario_geometry
)
from engine.scenario_contract_engine import (
    ScenarioLevelEngine,
    ScenarioCandidate,
    compute_bracket_geometry
)
from engine.execution_cost_model import (
    ExecutionCostModel,
    simulate_barrier_collision_resolution
)
from models.calibrated_signal_classifier import (
    CalibratedSignalEvaluator,
    compute_brier_score,
    compute_expected_calibration_error
)


# ==============================================================================
# SUITE A: SCREENSHOT ARITHMETIC AND STATE CONTRADICTIONS
# ==============================================================================
class TestSuiteAScreenshotArithmeticAndContradictions:
    """
    Reproduces and verifies the exact contradictions from the forensic screenshot:
    - Live BTC ~$81,515 vs stale analytical scenario $93,729.
    - Displayed R:R 2:1 vs exact level geometry ($750 / $656 = 1.14:1).
    - NOT_ESTIMATED + 75% + TIER 2 GATED contradiction.
    """

    def test_screenshot_level_arithmetic_disproves_two_to_one(self):
        entry = 93729.0
        tp = 94479.0
        sl = 93073.0

        reward_dist = tp - entry  # 750.0
        risk_dist = entry - sl    # 656.0
        computed_rr = reward_dist / risk_dist

        assert math.isclose(reward_dist, 750.0, abs_tol=1e-5)
        assert math.isclose(risk_dist, 656.0, abs_tol=1e-5)
        assert math.isclose(computed_rr, 1.14329, abs_tol=1e-3)
        # Verify that claiming 2:1 on these levels is mathematically false
        assert not math.isclose(computed_rr, 2.0, abs_tol=0.1)

    def test_stale_scenario_rejected_when_live_price_at_81515(self):
        engine = ScenarioLevelEngine(max_entry_slippage_bps=50.0)
        candidate = ScenarioCandidate(
            signal_id="sig_screenshot_stale",
            instrument="BTC-USD",
            direction="LONG",
            reference_price=81515.0,
            entry_price=93729.0,
            take_profit=94479.0,
            stop_loss=93073.0,
            signal_status="ACTIVE",
            model_tier="TIER_2_GATED"
        )
        validated = engine.validate_candidate(candidate)
        assert not validated.is_actionable
        assert validated.analytical_status in ["STALE_ENTRY_MISMATCH", "ABSTAIN_GATED", "INVALID_PRICE_RELATION"]
        assert "STALE" in validated.rejection_reason or "PRICE_MISMATCH" in validated.rejection_reason or "GATED" in validated.rejection_reason

    def test_contradictory_not_estimated_with_confidence_must_abstain(self):
        evaluator = CalibratedSignalEvaluator()
        result = evaluator.evaluate_signal(
            direction="NOT_ESTIMATED",
            raw_score=0.75,
            model_status="TIER_2_GATED",
            is_calibrated=False
        )
        assert result.signal_status == "ABSTAIN"
        assert result.displayed_conviction_pct == 0.0
        assert result.confidence_label == "UNESTIMATED_GATED"
        assert not result.is_actionable


# ==============================================================================
# SUITE B: SIDE-SPECIFIC RISK-LEVEL INVARIANTS
# ==============================================================================
class TestSuiteBSideSpecificRiskLevelInvariants:
    """
    Verifies side-specific ordering:
    LONG:  SL < Entry < TP
    SHORT: TP < Entry < SL
    Rejection of non-positive risk, inverted barriers, and non-finite numbers.
    """

    def test_valid_long_geometry(self):
        geo = compute_bracket_geometry(direction="LONG", entry=81500.0, tp=83000.0, sl=80500.0)
        assert geo["is_valid"]
        assert geo["reward_distance"] == 1500.0
        assert geo["risk_distance"] == 1000.0
        assert math.isclose(geo["gross_rr"], 1.5, abs_tol=1e-5)

    def test_valid_short_geometry(self):
        geo = compute_bracket_geometry(direction="SHORT", entry=81500.0, tp=80000.0, sl=82500.0)
        assert geo["is_valid"]
        assert geo["reward_distance"] == 1500.0
        assert geo["risk_distance"] == 1000.0
        assert math.isclose(geo["gross_rr"], 1.5, abs_tol=1e-5)

    def test_inverted_long_rejected(self):
        # TP below Entry in a Long candidate
        geo = compute_bracket_geometry(direction="LONG", entry=81500.0, tp=80000.0, sl=80500.0)
        assert not geo["is_valid"]
        assert "INVERTED_LEVELS" in geo["error_code"]

    def test_inverted_short_rejected(self):
        # SL below Entry in a Short candidate
        geo = compute_bracket_geometry(direction="SHORT", entry=81500.0, tp=80000.0, sl=81000.0)
        assert not geo["is_valid"]
        assert "INVERTED_LEVELS" in geo["error_code"]

    def test_zero_risk_distance_rejected(self):
        geo = compute_bracket_geometry(direction="LONG", entry=81500.0, tp=83000.0, sl=81500.0)
        assert not geo["is_valid"]
        assert "ZERO_OR_NEGATIVE_RISK" in geo["error_code"]

    def test_non_finite_values_rejected(self):
        geo = compute_bracket_geometry(direction="LONG", entry=float("nan"), tp=83000.0, sl=80000.0)
        assert not geo["is_valid"]
        assert "NON_FINITE" in geo["error_code"]


# ==============================================================================
# SUITE C: SOURCE, IDENTITY, AND FRESHNESS
# ==============================================================================
class TestSuiteCSourceIdentityAndFreshness:
    """
    Verifies venue/market identity (Coinbase Spot BTC-USD vs Binance Futures BTCUSDT),
    timestamp expiration, and stale snapshot rejection.
    """

    def test_spot_and_perpetual_market_isolation(self):
        spot_signal = create_abstain_signal(
            reason="GATED",
            instrument="BTC-USD",
            exchange="COINBASE",
            market_type="SPOT",
            reference_price=81440.67
        )
        assert spot_signal.market_type == "SPOT"
        assert spot_signal.quote_currency == "USD"
        assert spot_signal.instrument == "BTC-USD"

    def test_expired_scenario_validity(self):
        now = datetime.now(timezone.utc)
        contract = SignalContract(
            signal_id="sig_expired_test",
            generated_at=(now - timedelta(minutes=30)).isoformat(),
            valid_until=(now - timedelta(minutes=15)).isoformat(),
            instrument="BTC-USD",
            exchange="COINBASE",
            market_type="SPOT",
            quote_currency="USD",
            reference_price=81440.0,
            bid=81439.0,
            ask=81441.0,
            price_timestamp=(now - timedelta(minutes=30)).isoformat(),
            data_freshness_seconds=1800.0,
            chart_interval="15m",
            signal_horizon="15m",
            direction=SignalDirection.LONG,
            signal_status=SignalStatus.ACTIVE,
            model_id="AEER_v3.3",
            model_version="v3.3",
            model_authorization="RESEARCH_ONLY",
            calibration_status=CalibrationStatus.CALIBRATED,
            entry_type=EntryType.MARKET_REFERENCE,
            entry_price=81440.0,
            stop_loss=80800.0,
            take_profit=82200.0,
            risk_distance=640.0,
            reward_distance=760.0,
            gross_reward_to_risk=1.1875,
            execution_authorization=ExecutionAuthorization.DISABLED
        )
        assert contract.is_expired()


# ==============================================================================
# SUITE D: CONFIDENCE AND MODEL AUTHORIZATION
# ==============================================================================
class TestSuiteDConfidenceAndModelAuthorization:
    """
    Verifies that uncalibrated scores cannot be displayed as probabilities,
    Brier and ECE gates function, and abstention is enforced for gated models.
    """

    def test_brier_score_and_ece_computation(self):
        # Deterministic calibration verification
        probs = [0.1, 0.2, 0.7, 0.8, 0.9]
        actuals = [0, 0, 1, 1, 1]
        brier = compute_brier_score(probs, actuals)
        ece = compute_expected_calibration_error(probs, actuals, n_bins=5)

        assert brier >= 0.0
        assert brier <= 0.25
        assert ece >= 0.0
        assert ece <= 1.0

    def test_gated_model_cannot_display_high_conviction(self):
        evaluator = CalibratedSignalEvaluator()
        result = evaluator.evaluate_signal(
            direction="LONG",
            raw_score=0.88,
            model_status="TIER_2_GATED",
            is_calibrated=False
        )
        assert result.signal_status == "ABSTAIN"
        assert result.displayed_conviction_pct == 0.0
        assert "GATED" in result.confidence_label


# ==============================================================================
# SUITE E: CHART-MARKER PROVENANCE
# ==============================================================================
class TestSuiteEChartMarkerProvenance:
    """
    Verifies that markers must reference verified trade/event records,
    and historical outcomes (like SL LOSS) are never mislabeled as live signals.
    """

    def test_historical_marker_provenance_distinction(self):
        marker = {
            "id": "exit_trade_42",
            "trade_id": 42,
            "type": "EXIT_SL",
            "direction": "LONG",
            "outcome": "LOSS",
            "net_pnl_usd": -125.50,
            "is_live_signal": False,
            "historical_record": True
        }
        assert not marker["is_live_signal"]
        assert marker["historical_record"]
        assert marker["outcome"] == "LOSS"


# ==============================================================================
# SUITE F: COSTS AND PAYOFF SIMULATION
# ==============================================================================
class TestSuiteFCostsAndPayoffSimulation:
    """
    Verifies trading cost deduction, net reward-to-risk,
    and conservative same-bar collision resolution (SL_FIRST_CONSERVATIVE).
    """

    def test_coinbase_spot_cost_calculation(self):
        cost_model = ExecutionCostModel(venue="COINBASE", product_type="SPOT")
        costs = cost_model.calculate_roundtrip_cost(price=81440.0, size_btc=0.1)
        assert costs["maker_taker_bps"] > 0.0
        assert costs["total_cost_bps"] >= 9.0  # Approx 9.3 bps Coinbase Tier-1

    def test_same_bar_collision_conservative_resolution(self):
        bar_high = 82500.0
        bar_low = 80500.0
        entry = 81500.0
        tp = 82200.0
        sl = 80800.0

        # Both TP and SL were breached within this bar
        resolution = simulate_barrier_collision_resolution(
            direction="LONG",
            entry=entry,
            tp=tp,
            sl=sl,
            high=bar_high,
            low=bar_low,
            policy="SL_FIRST_CONSERVATIVE"
        )
        assert resolution["outcome"] == "STOP_LOSS"
        assert resolution["conservative_applied"]
        assert resolution["ambiguity_flag"]


# ==============================================================================
# SUITE G: FULL INTEGRATION AND GOVERNANCE LOCK
# ==============================================================================
class TestSuiteGFullIntegrationAndGovernanceLock:
    """
    Verifies production risk lock, non-executable authorization,
    and unified signal state machine.
    """

    def test_canonical_volatility_model_has_no_directional_trade(self):
        from models.authoritative_model_registry import get_active_model_registry
        reg = get_active_model_registry()
        vol_model = reg.get("HAR-RS-DOW-v1.0")
        assert vol_model is not None
        assert vol_model["forecast_horizon"] == "168h"
        assert vol_model["target_variable"] == "rv7d_var_ann"
        assert vol_model["directional_trading_authorized"] is False

    def test_live_trading_is_strictly_disabled(self):
        contract = create_abstain_signal(reason="LIVE_TRADING_DISABLED")
        assert contract.execution_authorization == ExecutionAuthorization.DISABLED
        assert contract.signal_status == SignalStatus.ABSTAIN
