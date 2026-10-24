"""
tests/test_entry_contracts_and_resolver.py
==========================================
Comprehensive regression and verification test suite for BTCognitive V30.1:
1. Mathematical cost reconciliation (87 bps vs 91.04 bps, break-even win rate, illustrative case).
2. Verification of the 70% target-first scenario under varying friction and volatility regimes.
3. Strict validation and immutability of CandidateSetup and ResolutionOutcome contracts.
4. DeterministicBarrierResolver test coverage:
   - Long/Short barrier touches (TP-first, SL-first).
   - Conservative intrabar collision rule (SL_FIRST + is_ambiguous_touch=True).
   - Opening gap penetration (positive and adverse gaps).
   - Horizon expiry / timeout at final close.
   - MFE / MAE excursion tracking in R-multiples.
   - Causal timestamp enforcement.
"""

import pytest
import numpy as np
from dataclasses import FrozenInstanceError

from engine.probabilistic_entry_engine import ProbabilisticEntryEngine
from engine.entry_contracts import CandidateSetup, ResolutionOutcome, compute_candidate_id
from engine.barrier_resolver import DeterministicBarrierResolver


# ============================================================================
# 1. Mathematical Cost & Expectancy Reconciliation
# ============================================================================

def test_reconciled_cost_accounting_87bps():
    """Verify that ProbabilisticEntryEngine computes exactly 87 bps round-trip without duplicate slippage."""
    engine = ProbabilisticEntryEngine()

    # Verify per-side components
    assert engine.commission_bps_one_way == 40.0
    assert engine.half_spread_bps == 1.5
    assert engine.slippage_bps_one_way == 2.0
    assert engine.fee_one_way_bps == 43.5
    assert engine.round_trip_friction_bps == 87.0
    assert np.isclose(engine.half_friction_rate, 0.00435, atol=1e-6)

    # Test decision gate at 1% volatility (sigma = 0.010, k_sl = 1.0)
    decision = engine.evaluate_decision_gate(
        side="LONG",
        entry_price=80000.0,
        sigma_t0=0.010,
        k_tp=1.5,
        k_sl=1.0,
        cost_scenario="COINBASE_RETAIL_87BPS"
    )

    # Risk unit: 80000 * (1.0 * 0.010) = 800 USD
    # Friction USD: 80000 * (87 / 10000) = 696.0 USD
    # Friction R: 696 / 800 = 0.87 R
    assert decision["risk_unit_usd"] == 800.0
    assert np.isclose(decision["friction_r"], 0.8700, atol=1e-4)
    assert decision["round_trip_friction_bps"] == 87.0


def test_illustrative_v30_case_reconciliation():
    """
    Reconcile the V30 audit illustrative case:
    p_tp = 0.592, p_sl = 0.328, p_timeout = 0.080
    R_tp = +1.5R, R_sl = -1.0R, R_timeout = -0.10R
    sigma = 0.00837
    """
    p_tp = 0.592
    p_sl = 0.328
    p_timeout = 0.080
    assert np.isclose(p_tp + p_sl + p_timeout, 1.0, atol=1e-6)

    # Gross expectancy in R
    expected_gross_r = p_tp * 1.5 - p_sl * 1.0 + p_timeout * (-0.10)
    assert np.isclose(expected_gross_r, 0.5520, atol=1e-4)

    # Friction under legacy 91.04 bps:
    # 0.009104 / 0.00837 = 1.0877 R
    friction_r_legacy = 0.009104 / 0.00837
    expected_net_r_legacy = expected_gross_r - friction_r_legacy
    assert np.isclose(expected_net_r_legacy, -0.5357, atol=1e-3)

    # Friction under reconciled 87.0 bps:
    # 0.00870 / 0.00837 = 1.0394 R
    friction_r_87bps = 0.00870 / 0.00837
    expected_net_r_87bps = expected_gross_r - friction_r_87bps
    assert np.isclose(expected_net_r_87bps, -0.4874, atol=1e-3)


def test_seventy_percent_target_first_reconciliation():
    """
    Recalculate and reconcile the claimed 70% target-first scenario.
    Formula: E[R_gross] = 2.5 * p_TP - 0.928
    """
    p_tp = 0.70
    p_timeout = 0.080
    p_sl = 1.0 - p_tp - p_timeout  # 0.220

    # Gross expectancy
    expected_gross_r = p_tp * 1.5 - p_sl * 1.0 + p_timeout * (-0.10)
    formula_gross_r = 2.5 * p_tp - 0.928
    assert np.isclose(expected_gross_r, formula_gross_r, atol=1e-6)
    assert np.isclose(expected_gross_r, 0.8220, atol=1e-4)

    # Low-volatility regime (sigma = 0.837%):
    # Friction (87 bps) = 0.0087 / 0.00837 = 1.0394 R
    # Net expectancy = 0.8220 - 1.0394 = -0.2174 R
    friction_low_vol = 0.0087 / 0.00837
    assert np.isclose(expected_gross_r - friction_low_vol, -0.2174, atol=1e-3)

    # Higher-volatility regime (sigma = 1.5%):
    # Friction (87 bps) = 0.0087 / 0.0150 = 0.5800 R
    # Net expectancy = 0.8220 - 0.5800 = +0.2420 R (Strongly positive!)
    friction_high_vol = 0.0087 / 0.0150
    assert expected_gross_r - friction_high_vol > 0.20

    # Binance Futures regime (12 bps, sigma = 0.837%):
    # Friction (12 bps) = 0.0012 / 0.00837 = 0.1434 R
    # Net expectancy = 0.8220 - 0.1434 = +0.6786 R (Strongly positive!)
    friction_binance = 0.0012 / 0.00837
    assert expected_gross_r - friction_binance > 0.65

    # Break-even win rate at sigma = 0.837% with 87 bps:
    # p_TP_breakeven = (0.928 + 1.0394) / 2.5 = 78.70%
    p_tp_breakeven = (0.928 + friction_low_vol) / 2.5
    assert np.isclose(p_tp_breakeven, 0.7870, atol=1e-3)


# ============================================================================
# 2. CandidateSetup & ResolutionOutcome Contract Invariants
# ============================================================================

def test_candidate_setup_immutability():
    """Verify CandidateSetup is frozen and cannot be mutated."""
    candidate = CandidateSetup(
        candidate_id="cand_test_001",
        strategy_archetype="MOMENTUM_BREAKOUT",
        direction="LONG",
        instrument_id="BTC-USD",
        venue="COINBASE",
        market_type="SPOT",
        decision_timestamp_utc="2026-10-23T12:00:00Z",
        fill_timestamp_utc="2026-10-23T12:01:00Z",
        entry_reference_price=80000.0,
        proposed_entry_price=80000.0,
        take_profit_price=81200.0,
        stop_loss_price=79200.0,
        k_tp=1.5,
        k_sl=1.0,
        horizon_bars=24,
        sigma_at_t0=0.010,
        risk_unit_usd=800.0,
        cost_scenario="COINBASE_RETAIL_87BPS",
        round_trip_friction_bps=87.0,
        friction_r=0.87,
        p_tp=0.65,
        p_sl=0.27,
        p_timeout=0.08,
        expected_gross_r=0.697,
        expected_net_r=-0.173,
        features_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )

    with pytest.raises(FrozenInstanceError):
        candidate.proposed_entry_price = 81000.0


def test_candidate_setup_geometry_validation():
    """Verify CandidateSetup validates barrier geometry and causal timestamps."""
    base_kwargs = dict(
        candidate_id="cand_test_002",
        strategy_archetype="MOMENTUM",
        direction="LONG",
        instrument_id="BTC-USD",
        venue="COINBASE",
        market_type="SPOT",
        decision_timestamp_utc="2026-10-23T12:00:00Z",
        fill_timestamp_utc="2026-10-23T12:01:00Z",
        entry_reference_price=80000.0,
        proposed_entry_price=80000.0,
        take_profit_price=81200.0,
        stop_loss_price=79200.0,
        k_tp=1.5,
        k_sl=1.0,
        horizon_bars=24,
        sigma_at_t0=0.010,
        risk_unit_usd=800.0,
        cost_scenario="COINBASE_RETAIL_87BPS",
        round_trip_friction_bps=87.0,
        friction_r=0.87,
        p_tp=0.65,
        p_sl=0.27,
        p_timeout=0.08,
        expected_gross_r=0.697,
        expected_net_r=-0.173,
        features_hash="hash"
    )

    # Inverted LONG geometry (TP < entry)
    with pytest.raises(ValueError, match="Invalid LONG barrier geometry"):
        bad_long = dict(base_kwargs, take_profit_price=79000.0)
        CandidateSetup(**bad_long)

    # Inverted SHORT geometry (TP > entry)
    with pytest.raises(ValueError, match="Invalid SHORT barrier geometry"):
        bad_short = dict(base_kwargs, direction="SHORT", take_profit_price=82000.0, stop_loss_price=78000.0)
        CandidateSetup(**bad_short)

    # Causal violation (fill < decision)
    with pytest.raises(ValueError, match="Causal violation"):
        bad_ts = dict(base_kwargs, fill_timestamp_utc="2026-10-23T11:59:00Z")
        CandidateSetup(**bad_ts)


def test_candidate_setup_serialization():
    """Verify dictionary serialization and round-trip restoration."""
    cid = compute_candidate_id("BREAKOUT", "LONG", "2026-10-23T12:00:00Z", 80000.0, 81200.0, 79200.0, 24)
    candidate = CandidateSetup(
        candidate_id=cid,
        strategy_archetype="BREAKOUT",
        direction="LONG",
        instrument_id="BTC-USD",
        venue="COINBASE",
        market_type="SPOT",
        decision_timestamp_utc="2026-10-23T12:00:00Z",
        fill_timestamp_utc="2026-10-23T12:01:00Z",
        entry_reference_price=80000.0,
        proposed_entry_price=80000.0,
        take_profit_price=81200.0,
        stop_loss_price=79200.0,
        k_tp=1.5,
        k_sl=1.0,
        horizon_bars=24,
        sigma_at_t0=0.010,
        risk_unit_usd=800.0,
        cost_scenario="COINBASE_RETAIL_87BPS",
        round_trip_friction_bps=87.0,
        friction_r=0.87,
        p_tp=0.60,
        p_sl=0.32,
        p_timeout=0.08,
        expected_gross_r=0.572,
        expected_net_r=-0.298,
        features_hash="abcdef"
    )

    data = candidate.to_dict()
    restored = CandidateSetup.from_dict(data)
    assert restored == candidate


# ============================================================================
# 3. Deterministic Barrier Resolver Tests
# ============================================================================

@pytest.fixture
def sample_long_candidate():
    return CandidateSetup(
        candidate_id="cand_long_01",
        strategy_archetype="MEAN_REVERSION",
        direction="LONG",
        instrument_id="BTC-USD",
        venue="COINBASE",
        market_type="SPOT",
        decision_timestamp_utc="2026-10-23T12:00:00Z",
        fill_timestamp_utc="2026-10-23T12:01:00Z",
        entry_reference_price=100.0,
        proposed_entry_price=100.0,
        take_profit_price=103.0,
        stop_loss_price=98.0,
        k_tp=1.5,
        k_sl=1.0,
        horizon_bars=3,
        sigma_at_t0=0.02,
        risk_unit_usd=2.0,
        cost_scenario="COINBASE_RETAIL_87BPS",
        round_trip_friction_bps=87.0,
        friction_r=0.435,
        p_tp=0.60,
        p_sl=0.32,
        p_timeout=0.08,
        expected_gross_r=0.572,
        expected_net_r=0.137,
        features_hash="hash"
    )


def test_resolver_long_tp_first(sample_long_candidate):
    """Test standard LONG TP-first resolution on bar 2."""
    bars = [
        {"timestamp_utc": "2026-10-23T12:01:00Z", "open": 100.0, "high": 101.5, "low": 99.0, "close": 101.0},
        {"timestamp_utc": "2026-10-23T12:02:00Z", "open": 101.0, "high": 103.5, "low": 100.5, "close": 103.2}
    ]
    outcome = DeterministicBarrierResolver.resolve_candidate(sample_long_candidate, bars)

    assert outcome.exit_reason == "TP_FIRST"
    assert outcome.exit_price == 103.0
    assert outcome.bars_held == 2
    assert outcome.gross_return_r == 1.5  # (103 - 100) / 2.0 = 1.5
    assert np.isclose(outcome.net_return_r, 1.5 - 0.435, atol=1e-4)
    assert not outcome.is_ambiguous_touch


def test_resolver_long_sl_first(sample_long_candidate):
    """Test standard LONG SL-first resolution on bar 1."""
    bars = [
        {"timestamp_utc": "2026-10-23T12:01:00Z", "open": 100.0, "high": 100.5, "low": 97.5, "close": 98.0}
    ]
    outcome = DeterministicBarrierResolver.resolve_candidate(sample_long_candidate, bars)

    assert outcome.exit_reason == "SL_FIRST"
    assert outcome.exit_price == 98.0
    assert outcome.bars_held == 1
    assert outcome.gross_return_r == -1.0  # (98 - 100) / 2.0 = -1.0
    assert np.isclose(outcome.net_return_r, -1.0 - 0.435, atol=1e-4)
    assert not outcome.is_ambiguous_touch


def test_resolver_conservative_intrabar_collision(sample_long_candidate):
    """
    Epistemic test: When both TP and SL are penetrated within the same bar,
    resolver MUST resolve to SL_FIRST with is_ambiguous_touch=True.
    """
    bars = [
        # Candle penetrates both 103.0 (High 104.0) and 98.0 (Low 97.0)
        {"timestamp_utc": "2026-10-23T12:01:00Z", "open": 100.0, "high": 104.0, "low": 97.0, "close": 101.0}
    ]
    outcome = DeterministicBarrierResolver.resolve_candidate(sample_long_candidate, bars)

    assert outcome.exit_reason == "INTRABAR_COLLISION_RESOLVED_SL"
    assert outcome.exit_price == 98.0
    assert outcome.bars_held == 1
    assert outcome.is_ambiguous_touch
    assert outcome.ambiguity_reason == "INTRABAR_COLLISION_BOTH_BARRIERS_TOUCHED"
    assert outcome.gross_return_r == -1.0


def test_resolver_opening_gap_through_tp(sample_long_candidate):
    """Verify opening gap beyond TP fills at Open price (positive gap fill)."""
    bars = [
        {"timestamp_utc": "2026-10-23T12:01:00Z", "open": 104.5, "high": 105.0, "low": 104.0, "close": 104.8}
    ]
    outcome = DeterministicBarrierResolver.resolve_candidate(sample_long_candidate, bars)

    assert outcome.exit_reason == "TP_FIRST"
    assert outcome.exit_price == 104.5
    assert outcome.gross_return_r == (104.5 - 100.0) / 2.0  # +2.25 R


def test_resolver_opening_gap_through_sl(sample_long_candidate):
    """Verify opening gap through SL fills at Open price (adverse gap fill)."""
    bars = [
        {"timestamp_utc": "2026-10-23T12:01:00Z", "open": 96.0, "high": 97.0, "low": 95.5, "close": 96.5}
    ]
    outcome = DeterministicBarrierResolver.resolve_candidate(sample_long_candidate, bars)

    assert outcome.exit_reason == "SL_FIRST"
    assert outcome.exit_price == 96.0
    assert outcome.gross_return_r == (96.0 - 100.0) / 2.0  # -2.0 R


def test_resolver_timeout_at_horizon(sample_long_candidate):
    """Verify position exits at Close of horizon candle when neither barrier is touched."""
    bars = [
        {"timestamp_utc": "2026-10-23T12:01:00Z", "open": 100.0, "high": 101.0, "low": 99.5, "close": 100.5},
        {"timestamp_utc": "2026-10-23T12:02:00Z", "open": 100.5, "high": 101.5, "low": 100.0, "close": 101.2},
        {"timestamp_utc": "2026-10-23T12:03:00Z", "open": 101.2, "high": 102.0, "low": 100.8, "close": 101.8}
    ]
    outcome = DeterministicBarrierResolver.resolve_candidate(sample_long_candidate, bars)

    assert outcome.exit_reason == "TIMEOUT"
    assert outcome.bars_held == 3
    assert outcome.exit_price == 101.8
    assert np.isclose(outcome.gross_return_r, (101.8 - 100.0) / 2.0, atol=1e-4)  # +0.9 R
    assert not outcome.is_ambiguous_touch
    # MFE should be (102.0 - 100.0) / 2.0 = 1.0 R
    assert np.isclose(outcome.mfe_r, 1.0, atol=1e-4)
    # MAE should be (99.5 - 100.0) / 2.0 = -0.25 R
    assert np.isclose(outcome.mae_r, -0.25, atol=1e-4)


def test_resolver_short_candidate_tp_first():
    """Verify SHORT candidate resolution when price drops to take-profit barrier."""
    short_candidate = CandidateSetup(
        candidate_id="cand_short_01",
        strategy_archetype="MEAN_REVERSION",
        direction="SHORT",
        instrument_id="BTC-USD",
        venue="COINBASE",
        market_type="SPOT",
        decision_timestamp_utc="2026-10-23T12:00:00Z",
        fill_timestamp_utc="2026-10-23T12:01:00Z",
        entry_reference_price=100.0,
        proposed_entry_price=100.0,
        take_profit_price=97.0,   # Drop to 97 is +1.5R
        stop_loss_price=102.0,    # Rise to 102 is -1.0R
        k_tp=1.5,
        k_sl=1.0,
        horizon_bars=3,
        sigma_at_t0=0.02,
        risk_unit_usd=2.0,
        cost_scenario="COINBASE_RETAIL_87BPS",
        round_trip_friction_bps=87.0,
        friction_r=0.435,
        p_tp=0.60,
        p_sl=0.32,
        p_timeout=0.08,
        expected_gross_r=0.572,
        expected_net_r=0.137,
        features_hash="hash"
    )

    bars = [
        {"timestamp_utc": "2026-10-23T12:01:00Z", "open": 100.0, "high": 101.0, "low": 98.5, "close": 99.0},
        {"timestamp_utc": "2026-10-23T12:02:00Z", "open": 99.0, "high": 99.5, "low": 96.5, "close": 96.8}
    ]
    outcome = DeterministicBarrierResolver.resolve_candidate(short_candidate, bars)

    assert outcome.exit_reason == "TP_FIRST"
    assert outcome.exit_price == 97.0
    assert outcome.bars_held == 2
    assert outcome.gross_return_r == 1.5  # (100 - 97) / 2.0 = 1.5
    assert not outcome.is_ambiguous_touch
