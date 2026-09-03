"""
engine/decision_envelope.py — Hardened Hash-Chained Decision & Resolution Ledger (D_t -> R_t)
=============================================================================================
Implements the canonical, immutable dual-object lifecycle for every market evaluation:
  1. Hash-Chained Append Ledger: H_i = SHA256(H_{i-1} || D_i) preventing retroactive tampering.
  2. Epistemic Null Semantics: null/None when unobservable/no event rather than deceptive 0.0.
  3. Precedence Hierarchy for Reason Codes.
  4. Decision Replay Inspector reconstructing full D_t -> R_t audit traces.
  5. Cryptographic chain verification & adversarial tamper detection.
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd


# Canonical Hierarchical Reason Code Precedence
REASON_CODE_PRECEDENCE = [
    "DATA_INVALID",
    "MODEL_STATE_BLOCK",
    "NO_EVENT",
    "PATH_EVIDENCE_INSUFFICIENT",
    "EV_BELOW_COST",
    "C2_RISK_EXCEEDED",
    "CAPACITY_BLOCK",
    "LATENCY_BLOCK",
    "TRADE"
]


class DecisionEnvelopeLedger:
    """
    Cryptographically chained, immutable audit ledger for Canonical Decision Envelopes (D_t)
    and Resolutions (R_t).
    """

    def __init__(self, ledger_file: Optional[str] = None):
        self.ledger_file = ledger_file or os.path.join("experiments", "results", "canonical_decisions.jsonl")
        os.makedirs(os.path.dirname(self.ledger_file), exist_ok=True)
        self._last_hash = self._get_latest_chain_hash()

    def _get_latest_chain_hash(self) -> str:
        """Reads the tail hash of the existing ledger, or returns the genesis hash."""
        if not os.path.exists(self.ledger_file):
            return "0" * 32
        tail_hash = "0" * 32
        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        tail_hash = entry.get("chain_hash", tail_hash)
        except Exception:
            pass
        return tail_hash

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a decision envelope by decision_id."""
        if not os.path.exists(self.ledger_file):
            return None
        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        if entry.get("record_type") == "DECISION" and entry.get("decision_id") == decision_id:
                            return entry
        except Exception:
            pass
        return None

    def get_all_decisions(self) -> List[Dict[str, Any]]:
        """Retrieves all decision envelopes in temporal order."""
        if not os.path.exists(self.ledger_file):
            return []
        decisions = []
        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        if entry.get("record_type") == "DECISION":
                            decisions.append(entry)
        except Exception:
            pass
        return decisions

    def compute_record_chain_hash(self, parent_hash: str, payload_str: str) -> str:
        """Computes H_i = SHA256(H_{i-1} || Payload)."""
        chain_material = f"{parent_hash}::{payload_str}"
        return hashlib.sha256(chain_material.encode("utf-8")).hexdigest()[:32]

    def create_decision_envelope(
        self,
        t_event: str,
        t_exchange: str,
        t_available: str,
        t_decision: str,
        market_state: Dict[str, Any],
        event: Dict[str, Any],
        path_distribution: Dict[str, Any],
        execution: Dict[str, Any],
        risk_authorization: Dict[str, Any],
        action: str,
        primary_reason_code: str,
        mechanism_diagnostics: Optional[Dict[str, Any]] = None,
        evidence_quality: str = "INSUFFICIENT",
        strategy_id: str = "MEIE-ARENA-v1.0",
        research_trial_id: Optional[str] = None,
        contract_terms: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates an immutable, hash-chained D_t decision envelope at t_0.
        """
        parent_hash = self._last_hash

        contract = contract_terms or {
            "entry_price": None,
            "tp_price": None,
            "sl_price": None,
            "max_hold_seconds": 1800,
            "direction": "LONG"
        }

        # Base payload for content verification
        content_payload = {
            "t_decision": t_decision,
            "state": market_state,
            "event": event,
            "path": path_distribution,
            "execution": execution,
            "contract": contract,
            "risk": risk_authorization,
            "action": action.upper(),
            "reason": primary_reason_code.upper()
        }
        json_content_str = json.dumps(content_payload, sort_keys=True, default=str)
        provenance_hash = hashlib.sha256(json_content_str.encode("utf-8")).hexdigest()[:16]
        decision_id = f"DEC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{provenance_hash[:6]}"

        # Cryptographic chain hash
        chain_hash = self.compute_record_chain_hash(parent_hash, json_content_str)
        self._last_hash = chain_hash

        decision_record = {
            "record_type": "DECISION",
            "decision_id": decision_id,
            "parent_hash": parent_hash,
            "chain_hash": chain_hash,
            "provenance_hash": provenance_hash,
            "strategy_id": strategy_id,
            "research_trial_id": research_trial_id,
            "timestamps": {
                "t_event": t_event,
                "t_exchange": t_exchange,
                "t_available": t_available,
                "t_decision": t_decision,
                "info_latency_ms": round(
                    (pd.to_datetime(t_available) - pd.to_datetime(t_exchange)).total_seconds() * 1000.0, 2
                ) if t_available and t_exchange else 0.0,
                "decision_latency_ms": round(
                    (pd.to_datetime(t_decision) - pd.to_datetime(t_available)).total_seconds() * 1000.0, 2
                ) if t_decision and t_available else 0.0
            },
            "market_state": market_state,
            "event": event,
            "path_distribution": path_distribution,
            "evidence_quality": evidence_quality,
            "execution": execution,
            "contract_terms": contract,
            "risk_authorization": risk_authorization,
            "action": action.upper(),
            "primary_reason_code": primary_reason_code.upper(),
            "mechanism_diagnostics": mechanism_diagnostics,
            "status": "OPEN"
        }

        # Append to immutable JSONL ledger
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(decision_record) + "\n")

        return decision_record

    def create_resolution_record(
        self,
        decision_id: str,
        t_exit: str,
        actual_path: str,
        realized_mfe_bps: float,
        realized_mae_bps: float,
        realized_gross_pnl_bps: float,
        realized_net_pnl_bps: float,
        counterfactual_gross_pnl_bps: float,
        counterfactual_net_pnl_bps: float,
        estimated_execution_drag_bps: float = 9.5,
        realized_execution_drag_bps: float = 9.5,
        skip_validation: str = "CORRECT_ABSTAIN",
        resolution_class: str = "TIMEOUT"
    ) -> Dict[str, Any]:
        """
        Creates an immutable resolution record R_t at t_exit chained into the ledger.
        """
        parent_hash = self._last_hash
        exec_forecast_error = round(estimated_execution_drag_bps - realized_execution_drag_bps, 2)

        resolution = {
            "decision_id": decision_id,
            "t_exit": t_exit,
            "actual_path": actual_path,
            "resolution_class": resolution_class,
            "realized_mfe_bps": round(realized_mfe_bps, 2),
            "realized_mae_bps": round(realized_mae_bps, 2),
            "realized_gross_pnl_bps": round(realized_gross_pnl_bps, 2),
            "realized_net_pnl_bps": round(realized_net_pnl_bps, 2),
            "estimated_execution_drag_bps": round(estimated_execution_drag_bps, 2),
            "realized_execution_drag_bps": round(realized_execution_drag_bps, 2),
            "execution_forecast_error_bps": exec_forecast_error,
            "counterfactual_gross_pnl_bps": round(counterfactual_gross_pnl_bps, 2),
            "counterfactual_net_pnl_bps": round(counterfactual_net_pnl_bps, 2),
            "skip_validation": skip_validation,
            "resolution_timestamp": datetime.now(timezone.utc).isoformat()
        }

        json_res_str = json.dumps(resolution, sort_keys=True, default=str)
        chain_hash = self.compute_record_chain_hash(parent_hash, json_res_str)
        self._last_hash = chain_hash

        resolution_entry = {
            "record_type": "RESOLUTION",
            "decision_id": decision_id,
            "parent_hash": parent_hash,
            "chain_hash": chain_hash,
            "resolution": resolution
        }

        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(resolution_entry) + "\n")

        return resolution

    def resolve_pending_decisions(
        self,
        current_price: float,
        high_price: Optional[float] = None,
        low_price: Optional[float] = None,
        current_time_iso: Optional[str] = None,
        realized_drag_bps: float = 9.5,
        max_horizon_seconds: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Scans ledger for un-resolved D_t decisions, checks individual D_t.max_hold_seconds,
        evaluates barrier first-passage touch, and appends immutable R_t records.
        """
        if not os.path.exists(self.ledger_file):
            return []

        now_dt = pd.to_datetime(current_time_iso or datetime.now(timezone.utc).isoformat(), utc=True)
        decisions: Dict[str, Dict[str, Any]] = {}
        resolved_ids = set()

        high_p = high_price if high_price is not None else current_price
        low_p = low_price if low_price is not None else current_price

        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("record_type") == "DECISION":
                        decisions[entry["decision_id"]] = entry
                    elif entry.get("record_type") == "RESOLUTION":
                        resolved_ids.add(entry["decision_id"])
                except Exception:
                    pass

        newly_resolved = []
        for d_id, d_entry in decisions.items():
            if d_id in resolved_ids:
                continue

            t_dec_str = d_entry.get("timestamps", {}).get("t_decision")
            if not t_dec_str:
                continue
            t_dec_dt = pd.to_datetime(t_dec_str, utc=True)
            elapsed_sec = (now_dt - t_dec_dt).total_seconds()

            contract = d_entry.get("contract_terms", {})
            max_hold = contract.get("max_hold_seconds", 1800)
            entry_p = contract.get("entry_price") or current_price
            tp_p = contract.get("tp_price")
            sl_p = contract.get("sl_price")
            is_long = contract.get("direction", "LONG").upper() == "LONG"
            action = d_entry.get("action", "ABSTAIN")
            est_drag = float(d_entry.get("execution", {}).get("execution_drag_bps", 9.5))

            # Barrier touch checking
            hit_tp = False
            hit_sl = False

            if tp_p and sl_p:
                if is_long:
                    hit_tp = high_p >= tp_p
                    hit_sl = low_p <= sl_p
                else:
                    hit_tp = low_p <= tp_p
                    hit_sl = high_p >= sl_p

            # Resolution evaluation
            should_resolve = False
            res_class = "TIMEOUT"
            actual_path = "TIMEOUT"

            if hit_sl and hit_tp:
                # Conservative priority: SL-first on simultaneous intra-bar breach
                should_resolve = True
                res_class = "RESOLVED_SL"
                actual_path = "SL_HIT"
            elif hit_sl:
                should_resolve = True
                res_class = "RESOLVED_SL"
                actual_path = "SL_HIT"
            elif hit_tp:
                should_resolve = True
                res_class = "RESOLVED_TP"
                actual_path = "TP_HIT"
            elif elapsed_sec >= max_hold:
                should_resolve = True
                res_class = "TIMEOUT"
                actual_path = "TIMEOUT"

            if should_resolve:
                # Calculate realized returns
                gross_ret_bps = 0.0
                if action == "TRADE" and entry_p > 0:
                    exit_price = tp_p if actual_path == "TP_HIT" else (sl_p if actual_path == "SL_HIT" else current_price)
                    price_ratio = (exit_price / entry_p) if is_long else (entry_p / exit_price)
                    gross_ret_bps = float(np.log(max(1e-6, price_ratio)) * 10000.0)

                net_ret_bps = gross_ret_bps - realized_drag_bps if action == "TRADE" else 0.0
                cf_net = gross_ret_bps - realized_drag_bps

                res = self.create_resolution_record(
                    decision_id=d_id,
                    t_exit=now_dt.isoformat(),
                    actual_path=actual_path,
                    resolution_class=res_class,
                    realized_mfe_bps=max(0.0, gross_ret_bps),
                    realized_mae_bps=min(0.0, gross_ret_bps),
                    realized_gross_pnl_bps=gross_ret_bps,
                    realized_net_pnl_bps=net_ret_bps,
                    counterfactual_gross_pnl_bps=gross_ret_bps,
                    counterfactual_net_pnl_bps=cf_net,
                    estimated_execution_drag_bps=est_drag,
                    realized_execution_drag_bps=realized_drag_bps,
                    skip_validation="CORRECT_ABSTAIN" if action == "ABSTAIN" else ("PROFITABLE_TRADE" if net_ret_bps > 0 else "LOSS_TRADE")
                )
                newly_resolved.append(res)

        return newly_resolved

    def verify_ledger_integrity(self) -> Dict[str, Any]:
        """
        Cryptographically validates the complete hash chain of the ledger.
        Fails if any historical line has been modified, deleted, or inserted.
        """
        if not os.path.exists(self.ledger_file):
            return {"valid": True, "n_records": 0, "violations": []}

        violations = []
        expected_parent = "0" * 32
        n_records = 0

        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                n_records += 1
                try:
                    entry = json.loads(line)
                    rec_type = entry.get("record_type")
                    rec_parent = entry.get("parent_hash")
                    rec_chain = entry.get("chain_hash")

                    # 1. Parent continuity check
                    if rec_parent != expected_parent:
                        violations.append(f"Line {idx}: Broken parent hash link (found {rec_parent[:8]}, expected {expected_parent[:8]})")

                    # 2. Content integrity hash re-computation
                    if rec_type == "DECISION":
                        content_payload = {
                            "t_decision": entry["timestamps"]["t_decision"],
                            "state": entry["market_state"],
                            "event": entry["event"],
                            "path": entry["path_distribution"],
                            "execution": entry["execution"],
                            "contract": entry.get("contract_terms", {}),
                            "risk": entry["risk_authorization"],
                            "action": entry["action"],
                            "reason": entry["primary_reason_code"]
                        }
                        json_content_str = json.dumps(content_payload, sort_keys=True, default=str)
                    elif rec_type == "RESOLUTION":
                        json_content_str = json.dumps(entry["resolution"], sort_keys=True, default=str)
                    else:
                        json_content_str = ""

                    recomputed_chain = self.compute_record_chain_hash(rec_parent, json_content_str)
                    if recomputed_chain != rec_chain:
                        violations.append(f"Line {idx}: Tampered record content hash mismatch ({recomputed_chain[:8]} != {rec_chain[:8]})")

                    expected_parent = rec_chain
                except Exception as e:
                    violations.append(f"Line {idx}: Malformed JSON entry ({str(e)})")

        return {
            "valid": len(violations) == 0,
            "n_records": n_records,
            "tail_hash": expected_parent,
            "violations": violations
        }

    def get_decision_replay(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """
        Reconstructs the full D_t -> R_t decision replay inspection for a given decision_id.
        """
        decision_doc = None
        resolution_doc = None

        if not os.path.exists(self.ledger_file):
            return None

        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("decision_id") == decision_id:
                    if entry.get("record_type") == "DECISION":
                        decision_doc = entry
                    elif entry.get("record_type") == "RESOLUTION":
                        resolution_doc = entry.get("resolution")

        if decision_doc is None:
            return None

        return {
            "decision_envelope_d_t": decision_doc,
            "resolution_r_t": resolution_doc,
            "has_resolved": resolution_doc is not None
        }

    def format_decision_anatomy_payload(self, decision_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the decision envelope into the exact 4-layer Decision Anatomy UI structure,
        using explicit null semantics when evidence is unobservable.
        """
        st = decision_record.get("market_state", {})
        ev = decision_record.get("event", {})
        pa = decision_record.get("path_distribution", {})
        ex = decision_record.get("execution", {})
        rk = decision_record.get("risk_authorization", {})

        has_event = ev.get("type", "NONE") != "NONE"

        return {
            "header": {
                "decision_id": decision_record.get("decision_id"),
                "provenance_hash": decision_record.get("provenance_hash"),
                "chain_hash": decision_record.get("chain_hash"),
                "strategy_id": decision_record.get("strategy_id"),
                "timestamp": decision_record.get("timestamps", {}).get("t_decision")
            },
            "opportunity_status": "IDENTIFIED" if has_event else "NONE",
            "evidence_status": "EVALUATED" if (has_event and pa.get("p_tp_first") is not None) else "NOT_APPLICABLE",
            "economics_status": "EVALUATED" if (has_event and ex.get("net_ev_bps") is not None) else "NOT_APPLICABLE",
            "risk_status": "EVALUATED" if has_event else "NOT_APPLICABLE",
            "layer1_market_event": {
                "event_type": ev.get("type", "NONE"),
                "event_strength": ev.get("strength") if has_event else None,
                "elapsed_seconds": ev.get("elapsed_seconds") if has_event else None,
                "state_dynamics": {
                    "volatility": st.get("volatility_regime", "NORMAL"),
                    "liquidity": st.get("liquidity_regime", "NORMAL"),
                    "flow": st.get("flow_regime", "BALANCED"),
                    "positioning": st.get("positioning_regime", "NEUTRAL"),
                    "novelty": st.get("novelty", "LOW")
                }
            },
            "layer2_conditional_path": {
                "empirical_tp_first_pct": pa.get("p_tp_first") if has_event else None,
                "empirical_sl_first_pct": pa.get("p_sl_first") if has_event else None,
                "empirical_timeout_pct": pa.get("p_timeout") if has_event else None,
                "sample_n": pa.get("sample_n", 0) if has_event else 0,
                "temporal_interval_95": pa.get("ci_95") if has_event else None,
                "evidence_quality": decision_record.get("evidence_quality", "NOT_APPLICABLE" if not has_event else "INSUFFICIENT"),
                "expected_mfe_bps": pa.get("expected_mfe_bps") if has_event else None,
                "expected_mae_bps": pa.get("expected_mae_bps") if has_event else None
            },
            "layer3_execution_economics": {
                "mode": ex.get("mode", "TAKER") if has_event else "NOT_APPLICABLE",
                "gross_expected_ev_bps": ex.get("gross_ev_bps") if has_event else None,
                "friction_breakdown_bps": {
                    "fee": ex.get("fee_bps", 5.0) if has_event else None,
                    "spread": ex.get("spread_bps", 2.0) if has_event else None,
                    "slippage": ex.get("slippage_bps", 2.0) if has_event else None,
                    "impact": ex.get("impact_bps", 0.5) if has_event else None,
                    "adverse_selection": ex.get("adverse_selection_bps", 0.0) if has_event else None
                },
                "total_execution_drag_bps": ex.get("execution_drag_bps", 9.5) if has_event else None,
                "net_executable_ev_bps": ex.get("net_ev_bps") if has_event else None
            },
            "layer4_risk_authorization": {
                "c2_model_health": rk.get("c2_model_health", "CALIBRATED"),
                "trade_risk_check": ("AUTHORIZED" if rk.get("authorized", False) else "BLOCKED") if has_event else "NOT_APPLICABLE",
                "risk_block_reason": (rk.get("risk_block_reason", "NONE" if rk.get("authorized", False) else "C2_RISK_EXCEEDED")) if has_event else "NO_OPPORTUNITY",
                "daily_risk_budget_allocated_pct": rk.get("daily_budget_allocated_pct", 0.0),
                "daily_risk_budget_limit_pct": rk.get("daily_budget_limit_pct", 0.50),
                "latency_health": rk.get("latency_health", "PASS"),
                "capacity_threshold": rk.get("capacity_threshold", "PASS"),
                "authorized": bool(rk.get("authorized", False)) if has_event else False
            },
            "final_action": decision_record.get("action", "ABSTAIN"),
            "primary_reason_code": decision_record.get("primary_reason_code", "NO_EVENT"),
            "mechanism_diagnostics": decision_record.get("mechanism_diagnostics", {
                "support_count": 0,
                "block_count": 0,
                "diagnostics": {}
            })
        }


# Global Singleton Decision Ledger
canonical_decision_ledger = DecisionEnvelopeLedger()

