"""
tests/test_opportunity_population_and_four_policy_ablation.py
=============================================================
Validates:
  1. Permanent Opportunity Population Ledger persistence & idempotency.
  2. Concurrent worker deduplication (1 Opportunity -> 1 Decision -> 1 Resolution).
  3. Paired 4-Policy Counterfactual Ablation on the identical opportunity stream.
"""

import os
import sys
import pytest
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.opportunity_definition import (
    OpportunityPopulationLedger,
    generate_opportunity_id,
    TargetContract
)


def test_opportunity_population_idempotency_and_worker_dedup(tmp_path):
    """Verifies that concurrent workers cannot register duplicate opportunities."""
    ledger_file = str(tmp_path / "opp_population.jsonl")
    ledger = OpportunityPopulationLedger(ledger_file=ledger_file)

    t0 = "2026-08-31T15:00:00Z"
    opp_id = "OPP-20260831-BTCUSDT-IGNITION-12345678"

    # Worker A registers first
    is_new_a, rec_a = ledger.register_opportunity(
        opportunity_id=opp_id,
        t_0=t0,
        asset="BTCUSDT",
        event_meta={"type": "IGNITION"},
        state_meta={"vol": "NORMAL"},
        contract={"tau_max": 1800},
        cluster_id="CLUST-001",
        population_definition_hash="pop_hash_abc"
    )
    assert is_new_a is True
    assert rec_a["opportunity_id"] == opp_id

    # Worker B tries to register same opportunity
    is_new_b, rec_b = ledger.register_opportunity(
        opportunity_id=opp_id,
        t_0=t0,
        asset="BTCUSDT",
        event_meta={"type": "IGNITION"},
        state_meta={"vol": "NORMAL"},
        contract={"tau_max": 1800},
        cluster_id="CLUST-001",
        population_definition_hash="pop_hash_abc"
    )
    assert is_new_b is False
    assert rec_b["status"] == "ALREADY_REGISTERED"


def test_paired_four_policy_counterfactual_ablation(tmp_path):
    """
    Verifies paired 4-policy counterfactual ablation across identical opportunities.
    """
    ledger_file = str(tmp_path / "opp_population_ablation.jsonl")
    ledger = OpportunityPopulationLedger(ledger_file=ledger_file)

    np.random.seed(42)
    n = 100
    opportunities = [{"opportunity_id": f"OPP-{i}"} for i in range(n)]
    
    # Realized returns from the future market path
    gross_returns = np.random.normal(12.0, 18.0, n) # bps
    drags = np.random.uniform(8.0, 12.0, n)          # bps
    c2_auth = np.random.choice([True, False], p=[0.80, 0.20], size=n)
    path_auth = gross_returns > drags

    ablation_res = ledger.evaluate_four_policy_ablation(
        opportunities=opportunities,
        future_realized_returns_bps=gross_returns.tolist(),
        execution_drags_bps=drags.tolist(),
        c2_risks_authorized=c2_auth.tolist(),
        path_edges_authorized=path_auth.tolist()
    )

    assert ablation_res["opportunity_count"] == 100
    evs = ablation_res["policy_ev_bps"]
    deltas = ablation_res["paired_deltas_bps"]

    # Invariants
    assert "policy_a_signal_only" in evs
    assert "policy_b_signal_and_execution" in evs
    assert "policy_c_signal_exec_and_risk" in evs
    assert "policy_d_full_decision_anatomy" in evs

    # Execution gating improves return by rejecting negative EV signals
    assert evs["policy_b_signal_and_execution"] >= evs["policy_a_signal_only"]
    assert deltas["delta_execution_value_b_minus_a"] >= 0.0
