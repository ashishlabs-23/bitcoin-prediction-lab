"""
tests/test_v32_16_audit_resolutions.py — Audit Verification & Remediation Suite
==============================================================================
Tests all technical resolutions specified in the technical review:
1. Removal of fallback placeholder constants (0.65, 2.2, 0.28, -0.00015). Missing telemetry returns UNAVAILABLE and ABSTAIN.
2. Single authoritative cost source: strategy selection and entry engine both derive costs from ExecutionCostModel.
3. Spot short mapping: candidate generation maps SHORT on spot markets to CASH (defensive cash hold).
4. V2 prospective ledger provenance: verifies all 5 mandatory fields (feature_source, cost_scenario, cost_model_version, sigma_horizon, rule_hash).
5. Sigma semantics: verifies sigma_1h is scaled by sqrt(H) for 24-hour horizon trades.
"""

import json
import pytest
import numpy as np
from pathlib import Path

from engine.strategy_selection import StrategySelectionEngine
from engine.evidence_router import AdaptiveEvidenceRouter
from engine.execution_cost_model import ExecutionCostModel
from engine.probabilistic_entry_engine import ProbabilisticEntryEngine
from engine.smart_entry_engine import SmartEntryEngine
from engine.entry_contracts import CandidateSetup


def test_missing_telemetry_causes_archetype_abstain():
    """Missing required telemetry in market snapshot causes archetype to abstain."""
    engine = StrategySelectionEngine()
    
    # Empty market snapshot (no OFI, no Hawkes)
    snap = {}
    eval_res = engine.evaluate_candidate_archetype(
        strategy_id="MEIE-IGNITION",
        enabled_indicators=["ofi", "hawkes"],
        market_snapshot=snap
    )
    
    assert eval_res["has_required_data"] is False
    assert eval_res["optimal_direction"] == "ABSTAIN"
    assert eval_res["disqualification_reason"] == "UNAVAILABLE_ORDER_FLOW_TELEMETRY"
    assert eval_res["long_hypothesis"]["tp_first_pct"] == 50.0
    assert eval_res["short_hypothesis"]["tp_first_pct"] == 50.0


def test_no_placeholder_constants_in_strategy_and_router():
    """Verify that placeholder fallback constants are not used in strategy_selection and evidence_router."""
    repo_root = Path(__file__).resolve().parent.parent
    strat_file = (repo_root / "engine" / "strategy_selection.py").read_text(encoding="utf-8")
    router_file = (repo_root / "engine" / "evidence_router.py").read_text(encoding="utf-8")
    
    # Assert no fallback substitutions of 0.65, 2.2, 0.28, -0.00015
    assert "0.65 if \"ofi\" in active_set" not in strat_file
    assert "2.2 if \"hawkes\" in active_set" not in strat_file
    assert "0.28 if \"vpin\" in active_set" not in strat_file
    assert "-0.00015 if \"funding\" in active_set" not in strat_file
    
    assert "else 0.65" not in router_file
    assert "else 2.2" not in router_file
    assert "else 0.28" not in router_file


def test_single_cost_source_consistency():
    """Verify strategy selection and entry engine share identical costs from ExecutionCostModel."""
    scenarios = [
        "COINBASE_ADVANCED_87BPS",
        "COINBASE_INDIA_INTL_27BPS",
        "COINBASE_EU_UK_RETAIL_107BPS",
        "COINBASE_US_RETAIL_187BPS"
    ]
    
    strat_engine = StrategySelectionEngine()
    entry_engine = ProbabilisticEntryEngine()
    
    for scenario in scenarios:
        expected_bps = ExecutionCostModel.get_round_trip_friction_bps(venue=scenario, is_taker_entry=True, is_taker_exit=True)
        
        # Test strategy selection cost drag
        snap = {
            "ofi": 0.8,
            "hawkes": 2.5,
            "cost_scenario": scenario
        }
        eval_strat = strat_engine.evaluate_candidate_archetype(
            strategy_id="MEIE-IGNITION",
            enabled_indicators=["ofi", "hawkes"],
            market_snapshot=snap
        )
        assert eval_strat["long_hypothesis"]["drag_bps"] == expected_bps
        
        # Test entry engine cost drag
        eval_entry = entry_engine.evaluate_decision_gate(
            side="LONG",
            entry_price=80000.0,
            sigma_t0=0.005,
            cost_scenario=scenario
        )
        assert eval_entry["round_trip_friction_bps"] == expected_bps


def test_spot_short_maps_strictly_to_cash():
    """Verify that spot SHORT signals map strictly to CASH (defensive cash hold)."""
    engine = SmartEntryEngine()
    
    # Create synthetic setup where direction is SHORT
    decision = {
        "side": "SHORT",
        "entry_reference_price": 80000.0,
        "tp_price": 78000.0,
        "sl_price": 81000.0,
        "volatility_sigma": 0.015,
        "sigma_horizon": 0.015,
        "k_tp": 1.5,
        "k_sl": 1.0,
        "probabilities": {"p_tp": 0.60, "p_sl": 0.32, "p_timeout": 0.08},
        "expected_net_r": 0.25,
        "expected_gross_r": 0.50,
        "friction_r": 0.25,
        "round_trip_friction_bps": 87.0
    }
    
    candidate = engine._build_candidate_setup(
        strategy_id="MEIE-IGNITION",
        direction="SHORT",
        entry_price=80000.0,
        decision=decision,
        features={"mom_1h": -0.5}
    )
    
    # Assert CandidateSetup has CASH direction and zero barrier risk
    assert candidate.direction == "CASH"
    assert candidate.take_profit_price == 80000.0
    assert candidate.stop_loss_price == 80000.0


def test_v2_prospective_ledger_provenance_fields(tmp_path):
    """Verify prospective entry ledger V2 contains all 5 mandatory provenance fields."""
    engine = ProbabilisticEntryEngine(data_dir=tmp_path)
    
    decision = engine.evaluate_decision_gate(
        side="LONG",
        entry_price=82000.0,
        sigma_t0=0.005,
        sigma_1h=0.005,
        horizon_bars=24,
        cost_scenario="COINBASE_INDIA_INTL_27BPS"
    )
    
    engine.log_prospective_decision(decision)
    
    # Read back logged row
    lines = engine.ledger_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    
    # Verify all 5 mandatory fields
    assert "feature_source" in record
    assert "cost_scenario" in record
    assert "cost_model_version" in record
    assert "sigma_horizon" in record
    assert "rule_hash" in record
    
    # Verify values
    assert record["ledger_version"] == "V2_PROSPECTIVE"
    assert record["cost_scenario"] == "COINBASE_INDIA_INTL_27BPS"
    assert record["cost_model_version"] == "EXECUTION_COST_MODEL_V2"
    assert record["sigma_scaling"] == "SQRT_H"
    assert record["sigma_horizon"] == pytest.approx(0.005 * np.sqrt(24), rel=1e-3)


def test_sigma_semantics_sqrt_h_scaling():
    """Verify sigma_1h is correctly scaled by sqrt(H) for 24-hour trade barriers."""
    engine = ProbabilisticEntryEngine()
    s_1h = 0.004  # 0.40% hourly volatility
    h_bars = 24
    expected_sigma_h = s_1h * np.sqrt(24)  # ~0.019596 (1.96%)
    
    decision = engine.evaluate_decision_gate(
        side="LONG",
        entry_price=80000.0,
        sigma_t0=s_1h,
        sigma_1h=s_1h,
        horizon_bars=h_bars,
        k_tp=1.5,
        k_sl=1.0
    )
    
    assert decision["sigma_1h"] == s_1h
    assert decision["sigma_horizon"] == pytest.approx(expected_sigma_h, rel=1e-3)
    assert decision["risk_unit_usd"] == pytest.approx(80000.0 * 1.0 * expected_sigma_h, rel=1e-2)
