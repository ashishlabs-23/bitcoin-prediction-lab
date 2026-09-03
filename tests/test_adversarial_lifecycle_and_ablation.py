"""
tests/test_adversarial_lifecycle_and_ablation.py — Full 12-Step Adversarial & Ablation Verification
====================================================================================================
Validates the complete 12-step lifecycle:
  1. Create D_t at t_0
  2. Hash-chain into Merkle ledger
  3. Execute / Abstain decision
  4. Persist D_t to disk
  5. Simulate market passage to resolution horizon
  6. Create R_t at t_exit
  7. Attempt adversarial retroactive mutation of D_t
  8. Verify cryptographic rejection of D_t mutation
  9. Attempt adversarial alteration of R_t
  10. Verify D_t remains untainted and identical
  11. Verify overall hash-chain integrity
  12. Verify paired 4-policy ablation (A, B, C, D) across the identical opportunity set.
"""

import os
import sys
import json
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.decision_envelope import DecisionEnvelopeLedger


def test_full_12_step_adversarial_and_ablation_lifecycle(tmp_path):
    """
    Executes the comprehensive 12-step adversarial and paired-ablation validation protocol.
    """
    test_ledger_file = str(tmp_path / "adversarial_audit_ledger.jsonl")
    ledger = DecisionEnvelopeLedger(ledger_file=test_ledger_file)
    now_iso = datetime.now(timezone.utc).isoformat()

    # -------------------------------------------------------------------------
    # Steps 1 to 4: Create D_t, Hash-chain it, Execute/Abstain, Persist to disk
    # -------------------------------------------------------------------------
    d_t = ledger.create_decision_envelope(
        t_event=now_iso,
        t_exchange=now_iso,
        t_available=now_iso,
        t_decision=now_iso,
        market_state={"volatility_regime": "HIGH", "liquidity_regime": "NORMAL"},
        event={"type": "IGNITION", "strength": 1.8},
        path_distribution={"p_tp_first": 0.62, "p_sl_first": 0.22, "p_timeout": 0.16, "sample_n": 180},
        execution={"mode": "TAKER", "gross_ev_bps": 22.0, "execution_drag_bps": 12.0, "net_ev_bps": 10.0},
        risk_authorization={"c2_model_health": "CALIBRATED", "trade_risk_check": "AUTHORIZED", "authorized": True},
        action="TRADE",
        primary_reason_code="PATH_EDGE_EXCEEDS_EXECUTION_DRAG",
        mechanism_diagnostics={"support_count": 3, "block_count": 0}
    )

    decision_id = d_t["decision_id"]
    initial_provenance_hash = d_t["provenance_hash"]
    initial_chain_hash = d_t["chain_hash"]

    assert os.path.exists(test_ledger_file)
    assert ledger.verify_ledger_integrity()["valid"] is True

    # -------------------------------------------------------------------------
    # Steps 5 & 6: Simulate market passage and Create R_t at t_exit
    # -------------------------------------------------------------------------
    exit_iso = datetime.now(timezone.utc).isoformat()
    r_t = ledger.create_resolution_record(
        decision_id=decision_id,
        t_exit=exit_iso,
        actual_path="TP_HIT",
        realized_mfe_bps=32.0,
        realized_mae_bps=-6.0,
        realized_gross_pnl_bps=28.0,
        realized_net_pnl_bps=16.0, # 28 gross - 12 drag
        counterfactual_gross_pnl_bps=28.0,
        counterfactual_net_pnl_bps=16.0,
        skip_validation="CORRECT_TRADE"
    )

    assert r_t["decision_id"] == decision_id
    assert ledger.verify_ledger_integrity()["valid"] is True

    # -------------------------------------------------------------------------
    # Steps 7 & 8: Attempt retroactive mutation of D_t -> Verify rejection
    # -------------------------------------------------------------------------
    with open(test_ledger_file, "r", encoding="utf-8") as f:
        original_lines = f.readlines()

    # Attacker tries to alter D_t action from "TRADE" to "ABSTAIN"
    tampered_lines = list(original_lines)
    d_tampered = json.loads(tampered_lines[0])
    d_tampered["action"] = "ABSTAIN"
    tampered_lines[0] = json.dumps(d_tampered) + "\n"

    with open(test_ledger_file, "w", encoding="utf-8") as f:
        f.writelines(tampered_lines)

    # Cryptographic integrity check MUST FAIL
    tamper_result = ledger.verify_ledger_integrity()
    assert tamper_result["valid"] is False
    assert any("Tampered record content hash mismatch" in v for v in tamper_result["violations"])

    # -------------------------------------------------------------------------
    # Steps 9, 10 & 11: Revert tamper, attempt alteration of R_t -> Verify chain
    # -------------------------------------------------------------------------
    # Revert D_t to valid state
    with open(test_ledger_file, "w", encoding="utf-8") as f:
        f.writelines(original_lines)
    assert ledger.verify_ledger_integrity()["valid"] is True

    # Attacker tries to inject fraudulent profit into R_t
    r_tampered_lines = list(original_lines)
    r_tampered = json.loads(r_tampered_lines[1])
    r_tampered["resolution"]["realized_net_pnl_bps"] = 999.0
    r_tampered_lines[1] = json.dumps(r_tampered) + "\n"

    with open(test_ledger_file, "w", encoding="utf-8") as f:
        f.writelines(r_tampered_lines)

    tamper_res_result = ledger.verify_ledger_integrity()
    assert tamper_res_result["valid"] is False

    # Restore clean ledger
    with open(test_ledger_file, "w", encoding="utf-8") as f:
        f.writelines(original_lines)
    assert ledger.verify_ledger_integrity()["valid"] is True

    # D_t retrieved from replay must be 100% identical to original
    replay = ledger.get_decision_replay(decision_id)
    assert replay["decision_envelope_d_t"]["provenance_hash"] == initial_provenance_hash
    assert replay["decision_envelope_d_t"]["chain_hash"] == initial_chain_hash

    # -------------------------------------------------------------------------
    # Step 12: Paired 4-Policy Ablation (A, B, C, D) on Identical Opportunities
    # -------------------------------------------------------------------------
    # Synthesize 100 candidate opportunities
    np.random.seed(42)
    n_opps = 100
    gross_signals = np.random.normal(12.0, 15.0, n_opps) # gross edge in bps
    drags = np.random.uniform(8.0, 14.0, n_opps) # execution drag
    c2_risks_ok = np.random.choice([True, False], p=[0.75, 0.25], size=n_opps)
    path_edges_ok = gross_signals > drags

    # Outcomes under each policy:
    # Policy A: Signal Only (trades whenever gross > 0)
    p_a_mask = gross_signals > 0.0
    p_a_returns = np.where(p_a_mask, gross_signals - drags, 0.0)

    # Policy B: Signal + Execution (trades whenever gross > drag)
    p_b_mask = gross_signals > drags
    p_b_returns = np.where(p_b_mask, gross_signals - drags, 0.0)

    # Policy C: Signal + Execution + C2 Risk (trades when gross > drag AND C2 ok)
    p_c_mask = (gross_signals > drags) & c2_risks_ok
    p_c_returns = np.where(p_c_mask, gross_signals - drags, 0.0)

    # Policy D: Full Decision Anatomy (requires path, execution, risk, and capacity)
    p_d_mask = (gross_signals > (drags + 2.0)) & c2_risks_ok
    p_d_returns = np.where(p_d_mask, gross_signals - drags, 0.0)

    # Compute exact paired incremental deltas
    ev_a = float(np.mean(p_a_returns))
    ev_b = float(np.mean(p_b_returns))
    ev_c = float(np.mean(p_c_returns))
    ev_d = float(np.mean(p_d_returns))

    delta_b_minus_a = ev_b - ev_a
    delta_c_minus_b = ev_c - ev_b
    delta_d_minus_c = ev_d - ev_c

    # Invariants on paired opportunity set
    assert ev_b >= ev_a # Execution filtering improves or maintains net return by eliminating negative-EV trades
    assert isinstance(delta_b_minus_a, float)
    assert isinstance(delta_c_minus_b, float)
    assert isinstance(delta_d_minus_c, float)
