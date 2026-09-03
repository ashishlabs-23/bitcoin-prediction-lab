"""
tests/test_opportunity_definition.py — Level 0.5 Opportunity & Target Engine Tests
==================================================================================
Validates:
  1. TargetContract formulation and cryptographic parameter hashing.
  2. EventClusterer overlap control (N_raw vs N_blocks).
  3. MechanismCoOccurrenceLedger simultaneous trigger disentanglement.
  4. OpportunityCensusLedger 6-stage funnel & OCR/Capture rates.
  5. PortfolioExposureLedger nonlinear aggregate impact.
"""

import os
import sys
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.opportunity_definition import (
    TargetContract,
    EventClusterer,
    MechanismCoOccurrenceLedger,
    OpportunityCensusLedger,
    PortfolioExposureLedger,
    CausalRole
)


def test_target_contract_hashing():
    """Verifies TargetContract creation and deterministic parameter hashing."""
    contract1 = TargetContract(
        entry_price=65000.0,
        tp_price=66300.0,
        sl_price=64350.0,
        direction="LONG",
        max_hold_seconds=1800,
        pt_mult=2.0,
        sl_mult=1.0
    )
    assert len(contract1.contract_hash) == 16

    # Identical parameters must yield identical hash
    contract2 = TargetContract(
        entry_price=65000.0,
        tp_price=66300.0,
        sl_price=64350.0,
        direction="LONG",
        max_hold_seconds=1800,
        pt_mult=2.0,
        sl_mult=1.0
    )
    assert contract1.contract_hash == contract2.contract_hash

    # Altered horizon must yield different hash
    contract3 = TargetContract(
        entry_price=65000.0,
        tp_price=66300.0,
        sl_price=64350.0,
        direction="LONG",
        max_hold_seconds=3600,
        pt_mult=2.0,
        sl_mult=1.0
    )
    assert contract1.contract_hash != contract3.contract_hash


def test_event_clusterer_overlap_control():
    """Verifies event de-duplication within holding window (N_raw vs N_blocks)."""
    clusterer = EventClusterer(cluster_window_seconds=1800)

    t0 = "2026-08-31T12:00:00Z"
    t1 = "2026-08-31T12:05:00Z"
    t2 = "2026-08-31T12:12:00Z"
    t3 = "2026-08-31T12:45:00Z" # Beyond 1800s window

    # Trigger 1: Starts new block
    res0 = clusterer.process_trigger("IGNITION", t0, 65000.0)
    assert res0["is_primary_block_event"] is True
    assert res0["cluster_trigger_index"] == 1

    # Trigger 2 & 3: Part of same cluster block
    res1 = clusterer.process_trigger("IGNITION", t1, 65100.0)
    assert res1["is_primary_block_event"] is False
    assert res1["cluster_id"] == res0["cluster_id"]
    assert res1["cluster_trigger_index"] == 2

    res2 = clusterer.process_trigger("IGNITION", t2, 65150.0)
    assert res2["is_primary_block_event"] is False
    assert res2["cluster_trigger_index"] == 3

    # Trigger 4: Outside 30m window -> spawns new independent block
    res3 = clusterer.process_trigger("IGNITION", t3, 65300.0)
    assert res3["is_primary_block_event"] is True
    assert res3["cluster_id"] != res0["cluster_id"]
    assert res3["cluster_trigger_index"] == 1


def test_mechanism_co_occurrence_disentanglement():
    """Verifies multi-mechanism simultaneous activation handling."""
    co_occ = MechanismCoOccurrenceLedger()

    # Single mechanism
    single_res = co_occ.analyze_composition(["IGNITION"])
    assert single_res["composition_type"] == "SINGLE"
    assert single_res["primary_mechanism"] == "IGNITION"
    assert single_res["co_occurrence_count"] == 1

    # Simultaneous concurrent mechanisms
    multi_res = co_occ.analyze_composition(["IGNITION", "VACUUM", "TOXICITY"])
    assert multi_res["composition_type"] == "CONCURRENT_MULTI"
    assert multi_res["co_occurrence_count"] == 3
    assert multi_res["composition_label"] == "IGNITION+TOXICITY+VACUUM"


def test_opportunity_census_funnel_and_ocr(tmp_path):
    """Verifies 6-stage opportunity funnel and conversion rates."""
    census_file = str(tmp_path / "test_opp_census.json")
    census = OpportunityCensusLedger(ledger_file=census_file)

    # Log 100 observations through the funnel
    for i in range(100):
        has_ev = (i % 2 == 0)      # 50 events
        is_qual = (i % 4 == 0)     # 25 qualified
        is_exec = (i % 5 == 0) and is_qual # 5 executable
        is_trade = is_exec         # 5 executed
        is_prof = is_trade and (i % 10 == 0) # 3 profitable

        census.log_observation(
            has_event=has_ev,
            is_qualified=is_qual,
            is_executable=is_exec,
            is_executed=is_trade,
            is_profitable=is_prof
        )

    metrics = census.get_funnel_metrics()
    assert metrics["funnel_counts"]["stage1_raw_observations"] == 100
    assert metrics["funnel_counts"]["stage2_mechanism_events"] == 50
    assert metrics["funnel_counts"]["stage3_qualified_opportunities"] == 25
    assert metrics["rates"]["r_opportunity_conversion_ocr"] > 0.0
    assert metrics["rates"]["r_execution_capture"] > 0.0


def test_portfolio_exposure_and_nonlinear_impact():
    """Verifies net directional exposure and nonlinear aggregate impact."""
    ledger = PortfolioExposureLedger(adv_usd=50_000_000.0)

    ledger.register_position("MEIE-IGNITION", "LONG", 50000.0)
    ledger.register_position("MEIE-VACUUM", "LONG", 50000.0)
    ledger.register_position("MEIE-ABSORPTION", "SHORT", 20000.0)

    summary = ledger.compute_aggregate_exposure_and_impact()
    assert summary["gross_portfolio_notional_usd"] == 120000.0
    assert summary["net_directional_notional_usd"] == 80000.0 # 100k long - 20k short
    assert summary["active_strategy_count"] == 3
    assert summary["nonlinear_aggregate_impact_bps"] > 0.0


def test_causal_role_taxonomy():
    """Verifies formal CausalRole enum taxonomy."""
    assert CausalRole.PRE_TREATMENT.value == "PRE_TREATMENT"
    assert CausalRole.TREATMENT.value == "TREATMENT"
    assert CausalRole.OUTCOME.value == "OUTCOME"
    assert CausalRole.MEDIATOR.value == "MEDIATOR"
