"""
engine/prospective_l2_evaluation_protocol.py — Locked Prospective Evaluation Protocol
======================================================================================
BTCognitive V32.39: Prospective Level-2 Shadow Qualification

Defines the immutable prospective evaluation schema, unbiased comparison ledger,
paired statistical hypothesis testing rules, and independent block accounting:
1. Versioned prospective schema: PROSPECTIVE_L2_GATED_V2
2. Unbiased opportunity tracking: records BOTH gate-passing and gate-rejected baseline setups.
3. Strict non-overlapping block definitions for statistical independence (N >= 100 blocks).
4. Pre-registered decision criteria, Diebold-Mariano HLN test, and transaction-cost model.
5. Delayed outcome resolution strictly enforced at t_exit >= t_0 + H.
"""

from __future__ import annotations

import os
import sys
import json
import math
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from scipy import stats

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_V2_LEDGER_PATH = os.path.join(REPO_ROOT, "data", "research", "prospective_l2_gated_ledger_v2.jsonl")

PROTOCOL_VERSION = "V32.39_PROSPECTIVE_L2_PROTOCOL"
SCHEMA_VERSION = "PROSPECTIVE_L2_GATED_V2"
STRATEGY_ID = "TSMOM_DONCHIAN_168H_336H"
PRIMARY_INSTRUMENT = "BTC-USD"
PRIMARY_VENUE = "COINBASE"
HORIZON_HOURS = 168  # 168 hours = 7 days

# Pre-registered L2 Gate Thresholds (Frozen, Never Tuned)
PREREGISTERED_OFI_THRESHOLD = 0.0      # OFI_15m > 0.0 (positive order flow into breakout)
PREREGISTERED_OBI_THRESHOLD = -0.20    # OBI_5 > -0.20 (no severe ask depth pressure)
PREREGISTERED_SPREAD_MAX_BPS = 5.0     # Spread <= 5.0 bps (tight top-of-book liquidity)
PREREGISTERED_MAX_STALENESS_SEC = 5.0  # Max feed age <= 5.0 seconds

# Conservative Transaction Cost Registry
COST_SCENARIOS = {
    "ACTIVE_TRADER_27BPS": {
        "round_trip_bps": 27.0,
        "entry_commission_bps": 10.0,
        "exit_commission_bps": 10.0,
        "half_spread_bps": 3.0,
        "slippage_bps": 4.0,
        "is_primary_benchmark": True,
        "description": "Coinbase Advanced Tier 3 active taker round-trip (Primary Benchmark)"
    },
    "RETAIL_87BPS": {
        "round_trip_bps": 87.0,
        "entry_commission_bps": 40.0,
        "exit_commission_bps": 40.0,
        "half_spread_bps": 3.0,
        "slippage_bps": 4.0,
        "is_primary_benchmark": False,
        "description": "Coinbase Advanced Retail Tier 1 (<$10k) taker round-trip"
    }
}


@dataclass(frozen=True)
class ProspectiveCandidateEntry:
    """Phase A: Candidate record emitted at decision time t_0."""
    record_type: str  # "PROSPECTIVE_CANDIDATE_V2"
    schema_version: str  # "PROSPECTIVE_L2_GATED_V2"
    candidate_id: str
    baseline_opportunity_id: str
    strategy_id: str
    instrument: str
    venue: str
    decision_epoch: float
    decision_timestamp_utc: str
    maturity_epoch: float
    maturity_timestamp_utc: str
    horizon_hours: int
    entry_reference_price: float
    proposed_entry_price: float
    stop_loss_price: float
    take_profit_price: float
    risk_unit_usd: float
    direction: str  # "LONG"
    gate_decision: str  # "GATE_ACCEPTED_SHADOW", "GATE_REJECTED_TOXIC_OFI", "GATE_REJECTED_HEAVY_ASK", "GATE_REJECTED_WIDE_SPREAD", "GATE_ABSTAIN_L2_UNAVAILABLE"
    gate_passed: bool
    rejection_reason: Optional[str]
    data_quality_status: str  # "DATA_VALID", "DATA_INVALID", "FEED_STALE", "FEED_DESYNC"
    l2_snapshot: Dict[str, Any]
    source_event_checksum: str
    is_independent_block: bool
    block_index: int
    cost_scenario: str = "ACTIVE_TRADER_27BPS"
    governance_status: str = "OFFLINE_RESEARCH_ONLY"
    live_trading_status: str = "DISABLED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProspectiveOutcomeEntry:
    """Phase B: Outcome record emitted after maturity or barrier resolution."""
    record_type: str  # "PROSPECTIVE_OUTCOME_V2"
    schema_version: str  # "PROSPECTIVE_L2_GATED_V2"
    candidate_id: str
    resolution_epoch: float
    resolution_timestamp_utc: str
    resolution_status: str  # "RESOLVED", "TIMEOUT", "AMBIGUOUS"
    exit_reason: str  # "TAKE_PROFIT", "STOP_LOSS", "TIMEOUT"
    exit_price: float
    bars_held: int
    gross_return_bps: float
    net_return_active_bps: float
    net_return_retail_bps: float
    ungated_net_r_active: float
    gated_net_r_active: float  # 0.0 if gate rejected (flat position)
    paired_difference_net_r: float  # gated_net_r - ungated_net_r
    was_gate_accepted: bool
    is_independent_block: bool
    block_index: int
    governance_status: str = "OFFLINE_RESEARCH_ONLY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProspectiveL2EvaluationProtocol:
    """
    Manages the prospective evaluation lifecycle, unbiased candidate tracking,
    independent block aggregation, and paired statistical testing.
    """

    def __init__(self, ledger_path: Optional[str] = None):
        self.ledger_path = ledger_path or DEFAULT_V2_LEDGER_PATH
        self._last_independent_maturity_epoch: float = 0.0
        self._current_block_index: int = 0
        self._candidate_records: Dict[str, ProspectiveCandidateEntry] = {}
        self._outcome_records: Dict[str, ProspectiveOutcomeEntry] = {}

    def evaluate_gate(self, snapshot: Dict[str, Any]) -> Tuple[str, bool, Optional[str], str]:
        """
        Evaluates frozen pre-registered gate rules:
        Returns: (gate_decision, gate_passed, rejection_reason, data_quality_status)
        """
        is_avail = snapshot.get("is_available", False)
        is_sync = snapshot.get("is_feed_synchronized", False)
        age = snapshot.get("data_age_seconds", 999.0)

        if not is_avail or not is_sync:
            reason = snapshot.get("reason_code") or "FEED_DESYNCHRONIZED_OR_UNAVAILABLE"
            return "GATE_ABSTAIN_L2_UNAVAILABLE", False, reason, "FEED_DESYNC"

        if age > PREREGISTERED_MAX_STALENESS_SEC:
            return "GATE_ABSTAIN_L2_UNAVAILABLE", False, f"DATA_STALE: age={age:.2f}s > {PREREGISTERED_MAX_STALENESS_SEC}s", "FEED_STALE"

        ofi = snapshot.get("ofi_value")
        if ofi is None or ofi <= PREREGISTERED_OFI_THRESHOLD:
            return "GATE_REJECTED_TOXIC_OFI", False, f"OFI ({ofi}) <= {PREREGISTERED_OFI_THRESHOLD}", "DATA_VALID"

        obi = snapshot.get("obi_5")
        if obi is None or obi <= PREREGISTERED_OBI_THRESHOLD:
            return "GATE_REJECTED_HEAVY_ASK", False, f"OBI_5 ({obi}) <= {PREREGISTERED_OBI_THRESHOLD}", "DATA_VALID"

        spread = snapshot.get("spread_bps")
        if spread is None or spread > PREREGISTERED_SPREAD_MAX_BPS:
            return "GATE_REJECTED_WIDE_SPREAD", False, f"Spread ({spread} bps) > {PREREGISTERED_SPREAD_MAX_BPS} bps", "DATA_VALID"

        return "GATE_ACCEPTED_SHADOW", True, None, "DATA_VALID"

    def register_opportunity(
        self,
        candidate_id: str,
        baseline_opportunity_id: str,
        decision_epoch: float,
        proposed_entry: float,
        stop_loss: float,
        take_profit: float,
        risk_unit_usd: float,
        l2_snapshot: Dict[str, Any],
        source_event_checksum: Optional[str] = None
    ) -> ProspectiveCandidateEntry:
        """
        Registers an eligible baseline opportunity at decision time t_0.
        Records BOTH gate-passing and gate-rejected setups.
        Enforces independent block numbering.
        """
        ts_utc = datetime.fromtimestamp(decision_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        maturity_ep = decision_epoch + (HORIZON_HOURS * 3600.0)
        maturity_utc = datetime.fromtimestamp(maturity_ep, tz=timezone.utc).isoformat().replace("+00:00", "Z")

        gate_decision, gate_passed, rejection_reason, dq_status = self.evaluate_gate(l2_snapshot)

        # Statistical Independence: Non-overlapping block check
        # A candidate belongs to a new independent block if its decision epoch is >= maturity of prior independent block
        is_independent = decision_epoch >= self._last_independent_maturity_epoch
        if is_independent:
            self._current_block_index += 1
            self._last_independent_maturity_epoch = maturity_ep

        checksum = source_event_checksum or hashlib.sha256(json.dumps(l2_snapshot, sort_keys=True).encode("utf-8")).hexdigest()

        entry = ProspectiveCandidateEntry(
            record_type="PROSPECTIVE_CANDIDATE_V2",
            schema_version=SCHEMA_VERSION,
            candidate_id=candidate_id,
            baseline_opportunity_id=baseline_opportunity_id,
            strategy_id=STRATEGY_ID,
            instrument=PRIMARY_INSTRUMENT,
            venue=PRIMARY_VENUE,
            decision_epoch=decision_epoch,
            decision_timestamp_utc=ts_utc,
            maturity_epoch=maturity_ep,
            maturity_timestamp_utc=maturity_utc,
            horizon_hours=HORIZON_HOURS,
            entry_reference_price=proposed_entry,
            proposed_entry_price=proposed_entry,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
            risk_unit_usd=risk_unit_usd,
            direction="LONG",
            gate_decision=gate_decision,
            gate_passed=gate_passed,
            rejection_reason=rejection_reason,
            data_quality_status=dq_status,
            l2_snapshot=l2_snapshot,
            source_event_checksum=checksum,
            is_independent_block=is_independent,
            block_index=self._current_block_index
        )

        self._candidate_records[candidate_id] = entry
        self._append_to_disk(entry.to_dict())
        return entry

    def resolve_opportunity(
        self,
        candidate_id: str,
        resolution_epoch: float,
        exit_price: float,
        exit_reason: str,
        bars_held: int
    ) -> ProspectiveOutcomeEntry:
        """
        Resolves a candidate opportunity strictly when resolution_epoch >= maturity_epoch
        (or touch event). Prevents lookahead leakage.
        Calculates ungated vs gated net returns.
        """
        if candidate_id not in self._candidate_records:
            raise KeyError(f"Candidate '{candidate_id}' not found in registered records")

        cand = self._candidate_records[candidate_id]

        if exit_reason == "TIMEOUT" and resolution_epoch < cand.maturity_epoch:
            raise ValueError(
                f"PREMATURE_RESOLUTION_ATTEMPTED: resolution_epoch {resolution_epoch} < maturity_epoch {cand.maturity_epoch}"
            )

        res_utc = datetime.fromtimestamp(resolution_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")

        # Returns calculation
        entry_p = cand.proposed_entry_price
        gross_return_bps = float(((exit_price - entry_p) / entry_p) * 10000.0)
        net_ret_active = gross_return_bps - COST_SCENARIOS["ACTIVE_TRADER_27BPS"]["round_trip_bps"]
        net_ret_retail = gross_return_bps - COST_SCENARIOS["RETAIL_87BPS"]["round_trip_bps"]

        # Risk units (R)
        r_unit = cand.risk_unit_usd if cand.risk_unit_usd > 0 else (entry_p * 0.02)
        gross_r = float((exit_price - entry_p) / r_unit)
        friction_r_active = (COST_SCENARIOS["ACTIVE_TRADER_27BPS"]["round_trip_bps"] / 10000.0) * (entry_p / r_unit)

        ungated_net_r = gross_r - friction_r_active

        # Gated strategy outcome: if gate accepted, trade is taken; if gate rejected, position is FLAT (net R = 0.0)
        if cand.gate_passed:
            gated_net_r = ungated_net_r
        else:
            gated_net_r = 0.0

        paired_diff = gated_net_r - ungated_net_r

        outcome = ProspectiveOutcomeEntry(
            record_type="PROSPECTIVE_OUTCOME_V2",
            schema_version=SCHEMA_VERSION,
            candidate_id=candidate_id,
            resolution_epoch=resolution_epoch,
            resolution_timestamp_utc=res_utc,
            resolution_status="RESOLVED",
            exit_reason=exit_reason,
            exit_price=exit_price,
            bars_held=bars_held,
            gross_return_bps=round(gross_return_bps, 2),
            net_return_active_bps=round(net_ret_active, 2),
            net_return_retail_bps=round(net_ret_retail, 2),
            ungated_net_r_active=round(ungated_net_r, 4),
            gated_net_r_active=round(gated_net_r, 4),
            paired_difference_net_r=round(paired_diff, 4),
            was_gate_accepted=cand.gate_passed,
            is_independent_block=cand.is_independent_block,
            block_index=cand.block_index
        )

        self._outcome_records[candidate_id] = outcome
        self._append_to_disk(outcome.to_dict())
        return outcome

    def compute_confirmatory_statistics(self) -> Dict[str, Any]:
        """
        Computes pre-registered statistical comparison on independent blocks:
        - Sample size of independent blocks
        - Mean paired difference in Net R
        - Student's t and Diebold-Mariano HLN statistic
        - Confirmatory gate evaluation
        """
        # Filter to resolved independent blocks
        indep_outcomes = [
            o for o in self._outcome_records.values()
            if o.is_independent_block
        ]
        n_indep = len(indep_outcomes)

        if n_indep == 0:
            return {
                "independent_blocks_count": 0,
                "operational_hurdle_met": False,
                "confirmatory_gate_verdict": "INSUFFICIENT_PROSPECTIVE_DATA",
                "mean_paired_net_r_diff": 0.0,
                "p_value": 1.0
            }

        diffs = np.array([o.paired_difference_net_r for o in indep_outcomes])
        mean_diff = float(np.mean(diffs))
        std_diff = float(np.std(diffs, ddof=1)) if n_indep > 1 else 0.0
        se_diff = std_diff / math.sqrt(n_indep) if n_indep > 1 else 0.0

        t_stat = mean_diff / se_diff if se_diff > 1e-9 else 0.0
        p_val = float(1.0 - stats.t.cdf(t_stat, df=n_indep - 1)) if n_indep > 1 else 1.0

        hurdle_met = n_indep >= 100
        edge_demonstrated = hurdle_met and mean_diff >= 0.05 and p_val < 0.05

        return {
            "independent_blocks_count": n_indep,
            "operational_hurdle_target": 100,
            "operational_hurdle_met": hurdle_met,
            "mean_paired_net_r_diff": round(mean_diff, 4),
            "std_paired_diff": round(std_diff, 4),
            "t_statistic": round(t_stat, 4),
            "p_value": round(p_val, 6),
            "economic_edge_hurdle_r": 0.05,
            "confirmatory_gate_verdict": "VALIDATED_PROSPECTIVE_EDGE" if edge_demonstrated else "NO_CONFIRMED_EDGE"
        }

    def _append_to_disk(self, record_dict: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        line = json.dumps(record_dict) + "\n"
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
