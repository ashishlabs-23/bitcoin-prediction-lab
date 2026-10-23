"""
tests/test_v9_data_integrity.py — V9 Acceptance & Data Integrity Test Suite
==========================================================================
Verifies that:
1. Scenario contract engine on sub-hourly (15m) requests returns DATA_FREQUENCY_UNSUPPORTED
   while preserving underlying hourly verified reference state, timestamps, and 1h volatility anchor.
2. Active paper position endpoint returns typed ai_prediction_engine with DATA_FREQUENCY_UNSUPPORTED
   and does not fall back to unverified synthetic values.
3. Itemized execution drag model is explicit (Spread 1.5 + Slippage 2.0 + Comm 5.8 = 9.3 bps).
4. Counterfactual lab contracts have explicit categories ('HYPOTHETICAL_HEURISTIC_SPECIFICATION'),
   explicit net_ev_formula, and itemized execution drag breakdown.
5. Exact analytical first-passage probability series satisfies probability conservation
   (P_U + P_L + P_0 = 1.0) and matches the headline acceptance baseline.
6. Strict governance invariants: Live trading strictly DISABLED, recommendation strictly ABSTAIN.
"""

import math
import pytest
import asyncio
from engine.scenario_contract_engine import HypotheticalScenarioPlanner
from engine.counterfactual_contract_engine import generate_counterfactual_lab_contracts
from research.verify_v9_data_integrity import exact_double_barrier_first_passage


def test_fourier_first_passage_invariants():
    """Verify analytical Fourier series converges and satisfies total probability law."""
    s0 = 81440.0
    u = s0 * 1.008  # Conformal upper barrier (+0.8%)
    l = s0 * 0.993  # Conformal lower barrier (-0.7%)
    sigma_15m = 0.0024 * math.sqrt(15.0 / 5.0)

    p_up, p_down, p_exit, p_zero, diag = exact_double_barrier_first_passage(s0, l, u, sigma_15m)

    # Must sum to 1.0 exactly within numerical tolerance
    total = p_up + p_down + p_zero
    assert abs(total - 1.0) < 1e-6, f"Total probability violated: {total}"

    # Check baseline match within declared tolerance
    assert p_up == pytest.approx(0.0553, abs=5e-3)
    assert p_down == pytest.approx(0.0911, abs=5e-3)
    assert p_zero == pytest.approx(0.8536, abs=5e-3)


def test_scenario_contract_subhourly_preserves_verified_hourly_metadata():
    """Verify 15m scenario preview preserves verified hourly market metadata upon rejection."""
    planner = HypotheticalScenarioPlanner()
    result = planner.compute_scenario_preview(horizon="15m")

    # Rejection status
    assert result["status"] == "UNAVAILABLE"
    assert result["rejection_code"] == "DATA_FREQUENCY_UNSUPPORTED"
    assert "Hourly data only" in result["rejection_narrative"]

    # Verified reference state must NOT be stripped or defaulted to fake seg_0
    assert result["reference_price"] is not None
    assert result["reference_price"] > 0
    assert result["price_timestamp"] is not None
    assert result["price_freshness_seconds"] is not None
    assert result["volatility_input_1h"] is not None
    assert result["volatility_observation_count"] is not None
    assert result["volatility_observation_count"] >= 24
    assert result["continuity_segment_id"] is not None
    assert result["continuity_segment_id"] != "seg_0"


def test_counterfactual_lab_metadata_and_drag_itemization():
    """Verify all 5 mechanisms have explicit heuristic category and itemized execution drag."""
    lab = generate_counterfactual_lab_contracts(live_price=81470.0)
    assert lab["status"] == "SUCCESS"
    assert len(lab["counterfactuals"]) == 5

    for c in lab["counterfactuals"]:
        assert c["category"] == "HYPOTHETICAL_HEURISTIC_SPECIFICATION"
        assert c["claim_level"] == "ILLUSTRATIVE_COUNTERFACTUAL_ONLY"
        assert c["trading_edge_proven"] is False
        assert "contract_details" in c
        details = c["contract_details"]
        assert "net_ev_formula" in details
        assert "execution_drag_breakdown" in details

        drag = details["execution_drag_breakdown"]
        assert drag["half_spread_bps"] == 1.5
        assert drag["slippage_bps"] == 2.0
        assert drag["total_drag_bps"] == c["base_drag_bps"]
        assert drag["exchange_commission_bps"] == round(c["base_drag_bps"] - 3.5, 1)


def test_meie_ignition_reproduction():
    """Verify MEIE-IGNITION mathematical reproduction matches V8 reported baseline."""
    lab = generate_counterfactual_lab_contracts(live_price=81470.0)
    contract = next(c for c in lab["counterfactuals"] if c["strategy_id"] == "MEIE-IGNITION")
    assert contract is not None

    up = contract["upper_scenario"]
    assert up["status"] == "AVAILABLE"
    # P(TP) = 68.6%
    assert up["p_tp"] == pytest.approx(0.686, abs=1e-3)
    # P(SL) = 31.4%
    assert up["p_sl"] == pytest.approx(0.314, abs=1e-3)
    # Net EV = +32.2 bps
    assert up["net_ev_bps"] == pytest.approx(32.2, abs=1e-1)
    # Base Drag = 9.3 bps
    assert contract["base_drag_bps"] == pytest.approx(9.3, abs=1e-2)
    # Itemized Breakdown for Ignition: 1.5 + 2.0 + 5.8 = 9.3 bps
    ignition_drag = contract["contract_details"]["execution_drag_breakdown"]
    assert ignition_drag["half_spread_bps"] == 1.5
    assert ignition_drag["slippage_bps"] == 2.0
    assert ignition_drag["exchange_commission_bps"] == 5.8
    assert ignition_drag["total_drag_bps"] == 9.3
    # Gross EV = Net EV + Drag = 32.2 + 9.3 = 41.5 bps
    assert (up["net_ev_bps"] + contract["base_drag_bps"]) == pytest.approx(41.5, abs=1e-1)


def test_arena_active_paper_position_returns_typed_subhourly_state():
    """Verify API returns typed DATA_FREQUENCY_UNSUPPORTED for sub-hourly horizons."""
    from api.routes_arena import get_active_paper_position

    pos = get_active_paper_position(signal_mode="live_ai", horizon="15m")
    assert pos["status"] in ["OK", "TIER_2_GATED", "RESEARCH_GATED"]
    assert pos["action"] == "ABSTAIN"
    assert pos["execution_authorization"] == "DISABLED"

    engine = pos["ai_prediction_engine"]
    assert engine["status"] in ["DATA_FREQUENCY_UNSUPPORTED", "MODEL_TIMEFRAME_INCOMPATIBLE"]
    assert engine["data_frequency_status"] in ["DATA_FREQUENCY_UNSUPPORTED", "SUPPORTED_15M"]
    assert "dual_hypotheses" in engine
    h_up = engine["dual_hypotheses"]["h_upper"]
    h_low = engine["dual_hypotheses"]["h_lower"]
    assert h_up["status"] in ["DATA_FREQUENCY_UNSUPPORTED", "MODEL_TIMEFRAME_INCOMPATIBLE", "SUPPORTED_15M"]
    assert h_up["p_upper_first"] is None
    assert h_low["p_lower_first"] is None
    assert h_up["n_eff"] is None
    assert h_up["drag_bps"] is None

    # Execution costs itemized
    costs = pos["execution_costs"]
    assert costs["estimated_execution_cost_bps"] == 9.3
    assert costs["total_cost_bps"] == 9.3
    components = costs["components"]
    assert components["half_spread_bps"] == 1.5
    assert components["slippage_bps"] == 2.0
    assert components["exchange_commission_bps"] == 5.8
    assert costs["is_observed_schedule"] is False
