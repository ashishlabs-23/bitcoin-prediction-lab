"""
tests/test_strategy_selection_engine.py
=========================================
Comprehensive tests for True Multi-Factor 5-Archetype Strategy Selection Engine:
1. Independent candidate evaluations across all 5 canonical MEIE archetypes.
2. Hard Eligibility Gating (Data, Evidence, Execution, Risk) prevents small N or negative EV from winning.
3. User Direction Preference and AI Rejection Guardrail (user requested SHORT overridden when evidence is LONG).
4. Dynamic market conditions shifting winning strategies (Ignition vs Vacuum vs Abstain).
5. Indicator config hashing and provenance tracking.
"""

import pytest
from engine.strategy_selection import (
    StrategySelectionEngine,
    strategy_selection_engine,
    compute_indicator_config_hash,
    CANONICAL_STRATEGY_ARCHETYPES,
    SUPPORTED_INDICATORS,
    INDICATOR_PRESETS
)


def test_canonical_archetypes_count_and_names():
    """Verify that exactly the 5 canonical MEIE archetypes are present."""
    assert len(CANONICAL_STRATEGY_ARCHETYPES) == 5
    expected = ["MEIE-IGNITION", "MEIE-ABSORPTION", "MEIE-VACUUM", "MEIE-TOXICITY", "MEIE-COMBINED"]
    assert CANONICAL_STRATEGY_ARCHETYPES == expected
    assert "MEIE-FUNDING-SQUEEZE" not in CANONICAL_STRATEGY_ARCHETYPES


def test_indicator_config_hash_deterministic():
    """Verify that indicator config hashing is deterministic and order-independent."""
    h1 = compute_indicator_config_hash(["ofi", "hawkes", "funding"])
    h2 = compute_indicator_config_hash(["funding", "ofi", "hawkes"])
    assert h1 == h2
    assert h1.startswith("0x")
    assert len(h1) == 10  # '0x' + 8 hex chars


def test_all_five_archetypes_evaluated_independently():
    """
    Verify that each of the 5 archetypes computes its OWN independent EV,
    drag, and sample size from its unique microstructure mechanics.
    """
    engine = StrategySelectionEngine()
    indicators = ["ofi", "hawkes", "vpin", "rv_5m", "liquidations"]
    res = engine.evaluate_dual_hypothesis(
        enabled_indicators=indicators,
        live_price=64000.0,
        regime="VOL_EXPANDING",
        c2_health="CALIBRATED"
    )

    matrix = res["candidate_matrix"]
    assert len(matrix) == 5

    strat_ids = [item["strategy_id"] for item in matrix]
    for expected_strat in CANONICAL_STRATEGY_ARCHETYPES:
        assert expected_strat in strat_ids

    # Check that EV values are not all identical clones
    long_evs = set(item["long_net_ev_bps"] for item in matrix)
    assert len(long_evs) >= 3, "Archetypes must have distinct, independently computed EVs"


def test_hard_eligibility_gate_filters_low_sample_n():
    """
    Verify that a strategy with small sample size (N < 30) is hard-gated by Evidence_i
    and cannot participate in ranking, regardless of nominal EV.
    """
    engine = StrategySelectionEngine()
    mock_candidate = {
        "strategy_id": "MEIE-IGNITION",
        "has_required_data": True,
        "optimal_direction": "LONG",
        "optimal_net_ev_bps": 25.0,  # High nominal EV!
        "long_hypothesis": {
            "n_samples": 7,           # But tiny sample size N=7
            "ci_lower_pct": 52.0
        },
        "short_hypothesis": {
            "n_samples": 7,
            "ci_lower_pct": 30.0
        }
    }

    is_eligible, gate_status, reason = engine.check_hard_eligibility_gates(mock_candidate)
    assert is_eligible is False
    assert gate_status == "FAIL_LOW_SAMPLE_N"
    assert "below minimum threshold of 30 bars" in reason


def test_hard_eligibility_gate_toxic_flow_blocks_absorption():
    """
    Verify that elevated VPIN toxicity shocks trigger the Toxicity Filter,
    blocking passive MEIE-ABSORPTION.
    """
    engine = StrategySelectionEngine()
    snap_toxic = {"vpin": 0.75, "ofi": 0.2}

    res = engine.evaluate_dual_hypothesis(
        enabled_indicators=["ofi", "vpin"],
        live_price=64000.0,
        regime="VOL_EXPANDING",
        market_snapshot=snap_toxic
    )

    matrix = res["candidate_matrix"]
    absorption_entry = next(item for item in matrix if item["strategy_id"] == "MEIE-ABSORPTION")

    assert absorption_entry["is_eligible"] is False
    assert absorption_entry["eligibility_status"] == "FAIL_TOXIC_FLOW_BLOCK"
    assert absorption_entry["selection_score"] == 0.0


def test_user_direction_preference_rejection_guardrail():
    """
    CRITICAL GUARDRAIL TEST:
    When user specifies SHORT preference, but the statistical evidence shows
    negative SHORT EV (-4.2 bps) and robust LONG edge (+14.8 bps):
    The AI must REJECT the user's directional bias and ABSTAIN.
    """
    engine = StrategySelectionEngine()
    indicators = ["ofi", "hawkes", "funding", "rv_5m"]
    # In this bullish setup, OFI and Hawkes favor LONG
    res = engine.evaluate_dual_hypothesis(
        enabled_indicators=indicators,
        live_price=64000.0,
        regime="VOL_EXPANDING",
        c2_health="CALIBRATED",
        user_direction_preference="SHORT"  # User wants SHORT
    )

    audit = res["user_preference_audit"]
    assert audit["user_preference"] == "SHORT"
    assert audit["status"] == "REJECTED_BY_AI"
    assert "AI rejects user directional bias" in audit["rejection_narrative"]

    synth = res["synthesis"]
    assert synth["final_action"] == "ABSTAIN"
    assert synth["primary_reason_code"] == "USER_SHORT_PREFERENCE_REJECTED"


def test_dynamic_market_shift_vacuum_wins_on_liquidity_thinning():
    """
    Verify that when market exhibits liquidity vacuum characteristics (wide spread, low depth),
    MEIE-VACUUM legitimately outranks MEIE-IGNITION.
    """
    engine = StrategySelectionEngine()
    indicators = ["rv_5m", "liquidations", "vpin"]
    vacuum_snapshot = {
        "spread_bps": 5.5,     # Wide spread expansion
        "depth_score": 0.20,   # Orderbook depth collapsed
        "ofi": -0.4,
        "is_expansion": False
    }

    res = engine.evaluate_dual_hypothesis(
        enabled_indicators=indicators,
        live_price=64000.0,
        regime="VOL_COMPRESSING",
        market_snapshot=vacuum_snapshot
    )

    assert res["selected_strategy_id"] == "MEIE-VACUUM"
    matrix = res["candidate_matrix"]
    vacuum_item = next(m for m in matrix if m["strategy_id"] == "MEIE-VACUUM")
    assert vacuum_item["is_eligible"] is True
    assert vacuum_item["selection_score"] > 0


def test_dual_hypothesis_abstains_on_c2_failure():
    """Verify that if C2 conformal risk is uncalibrated, the system abstains."""
    engine = StrategySelectionEngine()
    res = engine.evaluate_dual_hypothesis(
        enabled_indicators=["ofi", "hawkes"],
        live_price=64000.0,
        regime="VOL_EXPANDING",
        c2_health="DEGRADED_UNSTABLE"
    )
    synth = res["synthesis"]
    assert synth["final_action"] == "ABSTAIN"


def test_indicator_presets():
    """Verify that all presets only contain supported indicators."""
    for preset_name, inds in INDICATOR_PRESETS.items():
        for ind in inds:
            assert ind in SUPPORTED_INDICATORS, f"Indicator {ind} in preset {preset_name} is not supported"
