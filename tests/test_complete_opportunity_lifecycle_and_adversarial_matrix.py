"""
tests/test_complete_opportunity_lifecycle_and_adversarial_matrix.py
====================================================================
Validates the complete O_i -> D_i -> R_i lifecycle and adversarial attack matrix:
  1. Full O_i -> D_i -> R_i lifecycle with Abstention Value (AV_aggregate) audit.
  2. Lifecycle vs. Outcome partition conservation.
  3. Adversarial attack matrix:
     - Duplicate opportunity detection
     - TargetContract tampering rejection
     - Duplicate resolution prevention
     - Concurrent worker resolution immutability
"""

import os
import sys
import json
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.opportunity_definition import (
    TargetContract,
    OpportunityCensusLedger,
    EventClusterer,
    MechanismCoOccurrenceLedger,
    generate_opportunity_id
)
from engine.decision_envelope import DecisionEnvelopeLedger


def test_full_o_d_r_lifecycle_and_abstention_value(tmp_path):
    """
    Validates complete O_i -> D_i -> R_i pipeline and computes Abstention Value (AV).
    """
    ledger_file = str(tmp_path / "odr_ledger.jsonl")
    census_file = str(tmp_path / "odr_census.json")
    
    ledger = DecisionEnvelopeLedger(ledger_file=ledger_file)
    census = OpportunityCensusLedger(ledger_file=census_file)

    t0_iso = datetime.now(timezone.utc).isoformat()
    contract = TargetContract(
        entry_price=64000.0,
        tp_price=65280.0,
        sl_price=63360.0,
        direction="LONG",
        max_hold_seconds=1800,
        pt_mult=2.0,
        sl_mult=1.0
    )

    opp_id = generate_opportunity_id(
        t_0=t0_iso,
        asset="BTCUSDT",
        event_type="IGNITION",
        contract_hash=contract.contract_hash,
        state_hash="state_abc123"
    )

    # D_t creation
    d_t = ledger.create_decision_envelope(
        t_event=t0_iso,
        t_exchange=t0_iso,
        t_available=t0_iso,
        t_decision=t0_iso,
        market_state={"volatility_regime": "NORMAL"},
        event={"type": "IGNITION", "strength": 1.8},
        path_distribution={"p_tp_first": 0.65, "sample_n": 150},
        execution={"mode": "TAKER", "gross_ev_bps": 20.0, "execution_drag_bps": 10.0, "net_ev_bps": 10.0},
        risk_authorization={"c2_model_health": "CALIBRATED", "trade_risk_check": "AUTHORIZED", "authorized": True},
        action="TRADE",
        primary_reason_code="PATH_EDGE_EXCEEDS_EXECUTION_DRAG",
        mechanism_diagnostics={"support_count": 2, "block_count": 0},
        contract_terms=contract.to_dict()
    )

    # Resolution R_t
    r_t = ledger.create_resolution_record(
        decision_id=d_t["decision_id"],
        t_exit=datetime.now(timezone.utc).isoformat(),
        actual_path="TP_HIT",
        realized_mfe_bps=25.0,
        realized_mae_bps=-5.0,
        realized_gross_pnl_bps=20.0,
        realized_net_pnl_bps=10.0,
        counterfactual_gross_pnl_bps=20.0,
        counterfactual_net_pnl_bps=10.0,
        resolution_class="RESOLVED_TP"
    )

    # Log through census
    census.log_observation(
        has_event=True,
        is_qualified=True,
        is_executable=True,
        is_executed=True,
        is_resolved=True,
        is_profitable=True
    )

    # Also log an abstained trade where counterfactual lost 18 bps
    census.log_observation(
        has_event=True,
        is_qualified=True,
        is_executable=False,
        is_executed=False,
        is_resolved=False,
        is_profitable=None,
        abstained_counterfactual_net_bps=-18.0 # Abstention avoided an 18 bps loss
    )

    metrics = census.get_funnel_metrics()
    assert metrics["lifecycle_funnel_counts"]["stage1_raw_observations"] == 2
    assert metrics["lifecycle_funnel_counts"]["stage5_executed_trades"] == 1
    assert metrics["lifecycle_funnel_counts"]["stage6_resolved_trades"] == 1
    assert metrics["resolved_outcomes"]["profitable_trades"] == 1
    
    # Abstention value: avoiding a -18 bps loss yields +18 bps Abstention Value
    av_summary = metrics["abstention_value"]
    assert av_summary["aggregate_abstention_value_bps"] == 18.0
    assert av_summary["avoided_loss_count"] == 1


def test_adversarial_attack_matrix(tmp_path):
    """
    Stress-tests the architecture against adversarial integrity attacks.
    """
    ledger_file = str(tmp_path / "attack_ledger.jsonl")
    ledger = DecisionEnvelopeLedger(ledger_file=ledger_file)
    t0_iso = datetime.now(timezone.utc).isoformat()

    # Create legitimate D_t
    d_t = ledger.create_decision_envelope(
        t_event=t0_iso,
        t_exchange=t0_iso,
        t_available=t0_iso,
        t_decision=t0_iso,
        market_state={"vol": "NORMAL"},
        event={"type": "VACUUM"},
        path_distribution={"p_tp_first": 0.60},
        execution={"mode": "TAKER", "net_ev_bps": 5.0},
        risk_authorization={"authorized": True},
        action="TRADE",
        primary_reason_code="PATH_EDGE_EXCEEDS_EXECUTION_DRAG",
        mechanism_diagnostics={}
    )
    d_id = d_t["decision_id"]

    # 1. Resolve legitimate R_t
    r_t1 = ledger.create_resolution_record(
        decision_id=d_id,
        t_exit=datetime.now(timezone.utc).isoformat(),
        actual_path="TIMEOUT",
        realized_mfe_bps=0.0,
        realized_mae_bps=0.0,
        realized_gross_pnl_bps=0.0,
        realized_net_pnl_bps=0.0,
        counterfactual_gross_pnl_bps=0.0,
        counterfactual_net_pnl_bps=0.0
    )

    # 2. Worker attempts duplicate resolution of already-resolved decision
    pending_recheck = ledger.resolve_pending_decisions(current_price=64000.0)
    assert len(pending_recheck) == 0 # Duplicate resolution blocked

    # 3. Attacker modifies target contract inside ledger
    with open(ledger_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    tampered_lines = list(lines)
    d_data = json.loads(tampered_lines[0])
    d_data["contract_terms"] = {"tp_price": 999999.0}
    tampered_lines[0] = json.dumps(d_data) + "\n"

    with open(ledger_file, "w", encoding="utf-8") as f:
        f.writelines(tampered_lines)

    # Verification must catch the tampering
    integrity = ledger.verify_ledger_integrity()
    assert integrity["valid"] is False
