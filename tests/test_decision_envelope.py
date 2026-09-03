"""
tests/test_decision_envelope.py — Hardened Decision Ledger & Hash-Chain Adversarial Tests
==========================================================================================
Validates:
  1. Complete immutable D_t -> R_t lifecycle.
  2. Cryptographic Merkle/Hash-Chain validation across entries.
  3. Adversarial tampering detection (retroactive mutations break the chain).
  4. Epistemic null semantics (unobservable quantities return None, not 0.0).
  5. Decision Replay Inspector reconstruction.
"""

import os
import sys
import json
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.decision_envelope import DecisionEnvelopeLedger


def test_decision_envelope_lifecycle_and_hash_chain(tmp_path):
    """Tests complete immutable D_t -> R_t lifecycle with cryptographic hash chaining."""
    test_ledger_file = str(tmp_path / "test_chained_decisions.jsonl")
    ledger = DecisionEnvelopeLedger(ledger_file=test_ledger_file)

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Create Decision Envelope (D_t)
    d_record = ledger.create_decision_envelope(
        t_event=now_iso,
        t_exchange=now_iso,
        t_available=now_iso,
        t_decision=now_iso,
        market_state={
            "volatility_regime": "HIGH",
            "liquidity_regime": "THIN",
            "flow_regime": "BUYING",
            "positioning_regime": "CROWDED",
            "novelty": "ELEVATED"
        },
        event={
            "type": "IGNITION",
            "strength": 1.84,
            "elapsed_seconds": 8.2
        },
        path_distribution={
            "p_tp_first": 0.632,
            "p_sl_first": 0.214,
            "p_timeout": 0.154,
            "sample_n": 214,
            "ci_95": [0.581, 0.684],
            "expected_mfe_bps": 31.0,
            "expected_mae_bps": -15.0
        },
        execution={
            "mode": "TAKER",
            "gross_ev_bps": 21.0,
            "fee_bps": 8.0,
            "spread_bps": 3.0,
            "slippage_bps": 6.0,
            "impact_bps": 3.0,
            "adverse_selection_bps": 5.0,
            "execution_drag_bps": 25.0,
            "net_ev_bps": -4.0
        },
        risk_authorization={
            "c2_state": "CALIBRATED",
            "daily_budget_allocated_pct": 0.18,
            "daily_budget_limit_pct": 0.50,
            "latency_health": "PASS",
            "capacity_threshold": "PASS",
            "authorized": False
        },
        action="ABSTAIN",
        primary_reason_code="EV_BELOW_COST",
        mechanism_diagnostics={
            "support_count": 3,
            "block_count": 1,
            "diagnostics": {"IGNITION": "SUPPORT", "ABSORPTION": "NEUTRAL", "VACUUM": "SUPPORT", "TOXICITY": "BLOCK"}
        },
        evidence_quality="HIGH (N=214 across 6 independent block partitions)"
    )

    assert "decision_id" in d_record
    assert "chain_hash" in d_record
    assert "provenance_hash" in d_record
    assert d_record["action"] == "ABSTAIN"
    assert d_record["primary_reason_code"] == "EV_BELOW_COST"

    # 2. Format Decision Anatomy UI payload
    ui_payload = ledger.format_decision_anatomy_payload(d_record)
    assert ui_payload["layer1_market_event"]["event_type"] == "IGNITION"
    assert ui_payload["layer2_conditional_path"]["empirical_tp_first_pct"] == 0.632
    assert ui_payload["layer3_execution_economics"]["gross_expected_ev_bps"] == 21.0
    assert ui_payload["layer3_execution_economics"]["net_executable_ev_bps"] == -4.0

    # 3. Create Resolution Record (R_t)
    res_record = ledger.create_resolution_record(
        decision_id=d_record["decision_id"],
        t_exit=datetime.now(timezone.utc).isoformat(),
        actual_path="TIMEOUT",
        realized_mfe_bps=14.2,
        realized_mae_bps=-8.1,
        realized_gross_pnl_bps=5.1,
        realized_net_pnl_bps=-19.9,
        counterfactual_gross_pnl_bps=5.1,
        counterfactual_net_pnl_bps=-19.9,
        skip_validation="CORRECT_ABSTAIN"
    )

    assert res_record["decision_id"] == d_record["decision_id"]

    # 4. Verify Cryptographic Integrity
    audit_res = ledger.verify_ledger_integrity()
    assert audit_res["valid"] is True
    assert audit_res["n_records"] == 2
    assert len(audit_res["violations"]) == 0

    # 5. Replay Inspector Test
    replay = ledger.get_decision_replay(d_record["decision_id"])
    assert replay is not None
    assert replay["has_resolved"] is True
    assert replay["decision_envelope_d_t"]["decision_id"] == d_record["decision_id"]
    assert replay["resolution_r_t"]["actual_path"] == "TIMEOUT"


def test_adversarial_tampering_detection(tmp_path):
    """Adversarially mutates an earlier record in the JSONL ledger and verifies chain failure."""
    test_ledger_file = str(tmp_path / "test_tampered_decisions.jsonl")
    ledger = DecisionEnvelopeLedger(ledger_file=test_ledger_file)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Create 3 chained records
    d1 = ledger.create_decision_envelope(
        t_event=now_iso, t_exchange=now_iso, t_available=now_iso, t_decision=now_iso,
        market_state={}, event={"type": "NONE"}, path_distribution={}, execution={},
        risk_authorization={}, action="ABSTAIN", primary_reason_code="NO_EVENT", mechanism_diagnostics={}
    )
    d2 = ledger.create_decision_envelope(
        t_event=now_iso, t_exchange=now_iso, t_available=now_iso, t_decision=now_iso,
        market_state={}, event={"type": "IGNITION"}, path_distribution={}, execution={},
        risk_authorization={}, action="ABSTAIN", primary_reason_code="EV_BELOW_COST", mechanism_diagnostics={}
    )
    ledger.create_resolution_record(
        decision_id=d2["decision_id"], t_exit=now_iso, actual_path="TP_HIT",
        realized_mfe_bps=25.0, realized_mae_bps=-5.0, realized_gross_pnl_bps=20.0,
        realized_net_pnl_bps=12.0, counterfactual_gross_pnl_bps=20.0, counterfactual_net_pnl_bps=12.0
    )

    # Initial chain must be valid
    assert ledger.verify_ledger_integrity()["valid"] is True

    # Adversarially modify Line 1 in the file (retroactive rewrite of D_1 action from ABSTAIN to TRADE)
    with open(test_ledger_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    tampered_entry = json.loads(lines[0])
    tampered_entry["action"] = "TRADE" # Retroactive mutation
    lines[0] = json.dumps(tampered_entry) + "\n"

    with open(test_ledger_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # Re-verify ledger: MUST fail cryptographic audit
    tampered_audit = ledger.verify_ledger_integrity()
    assert tampered_audit["valid"] is False
    assert len(tampered_audit["violations"]) > 0


def test_epistemic_null_semantics(tmp_path):
    """Verifies that NO_EVENT returns explicit null/None instead of misleading 0.0 values."""
    test_ledger_file = str(tmp_path / "test_null_semantics.jsonl")
    ledger = DecisionEnvelopeLedger(ledger_file=test_ledger_file)
    now_iso = datetime.now(timezone.utc).isoformat()

    d_no_event = ledger.create_decision_envelope(
        t_event=now_iso, t_exchange=now_iso, t_available=now_iso, t_decision=now_iso,
        market_state={"volatility_regime": "NORMAL"},
        event={"type": "NONE"}, # No event
        path_distribution={},
        execution={},
        risk_authorization={"c2_state": "CALIBRATED", "authorized": False},
        action="ABSTAIN",
        primary_reason_code="NO_EVENT",
        mechanism_diagnostics={},
        evidence_quality="INSUFFICIENT"
    )

    payload = ledger.format_decision_anatomy_payload(d_no_event)

    # Epistemic null checks
    assert payload["layer1_market_event"]["event_strength"] is None
    assert payload["layer1_market_event"]["elapsed_seconds"] is None
    assert payload["layer2_conditional_path"]["empirical_tp_first_pct"] is None
    assert payload["layer2_conditional_path"]["temporal_interval_95"] is None
    assert payload["layer2_conditional_path"]["evidence_quality"] == "INSUFFICIENT"
    assert payload["layer3_execution_economics"]["gross_expected_ev_bps"] is None
    assert payload["layer3_execution_economics"]["net_executable_ev_bps"] is None
    assert payload["final_action"] == "ABSTAIN"
    assert payload["primary_reason_code"] == "NO_EVENT"
