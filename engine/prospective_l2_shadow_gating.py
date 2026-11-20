"""
engine/prospective_l2_shadow_gating.py — Opt-In Coinbase L2 Shadow Gating Engine
================================================================================
Implements an auditable, forward-only shadow evaluation engine and append-only ledger
for testing whether contemporaneous Coinbase Level-2 order-flow features improve the
BTCUSD 168-hour breakout strategy (TSMOM_DONCHIAN_168H_336H) after transaction costs.

Epistemic & Non-Execution Invariants:
1. Strict Non-Execution: Live trading, broker connections, order submissions, and real
   capital are PERMANENTLY DISABLED. All candidates and outcomes are recorded strictly
   for offline research analysis.
2. Protected Files Isolation: All writes are strictly directed to the dedicated ledger:
   `data/research/prospective_l2_gated_ledger_v1.jsonl`.
   NEVER modifies or touches the 5 protected files:
   - data/prospective_entry_ledger.jsonl
   - data/prospective_shadow_v1.jsonl
   - data/prospective_entry_ledger_v2.jsonl
   - data/raw/ohlcv.parquet
   - data/raw/ohlcv_pre_backfill_backup.parquet
3. Two-Phase Audit Trail:
   - Phase A (Decision Time t0): Immutable candidate setup record written immediately with
     L2 microstructure snapshot and gate decision.
   - Phase B (Maturity / Touch t_exit): Outcome record appended ONLY after barrier resolution
     or horizon timeout has elapsed.
4. Causal Boundaries & Fail-Closed Gate:
   - L2 features strictly evaluated <= decision_epoch.
   - If L2 feed is disabled, uninitialized, desynchronized, or stale (>5s), gate fails closed:
     `GATE_ABSTAIN_L2_UNAVAILABLE`.
   - Gate acceptance requires: OFI_15m > 0.0, OBI_5 > -0.20, Spread_bps <= 5.0.
   - Zero synthetic zero-filling of missing or stale microstructure data.
5. Ungated Control Parity:
   - Evaluates the identical breakout candidates under both ungated control and L2-gated arms
     to enable rigorous paired difference analysis.
"""

from __future__ import annotations

import os
import json
import uuid
import math
import hashlib
import logging
import threading
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Union

import numpy as np
import pandas as pd
from filelock import FileLock
from scipy import stats

from engine.entry_contracts import CandidateSetup, ResolutionOutcome, compute_candidate_id
from engine.barrier_resolver import DeterministicBarrierResolver
from engine.l2_microstructure_features import L2MicrostructureSnapshot, OrderBookTracker

logger = logging.getLogger("btcognitive.prospective_l2_gating")

DEFAULT_L2_GATED_LEDGER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "research", "prospective_l2_gated_ledger_v1.jsonl")
)

STRATEGY_ID = "TSMOM_DONCHIAN_168H_336H"
STRATEGY_SPEC_HASH = "8f3e2b9c7a1d5e4b"
PRIMARY_INSTRUMENT = "BTC-USD"
PRIMARY_VENUE = "COINBASE"
PRIMARY_COST_SCENARIO = "ACTIVE_TRADER_27BPS"

COST_REGISTRY_BPS = {
    "INSTITUTIONAL_18BPS": {
        "round_trip_bps": 18.6,
        "entry_commission_bps": 8.0,
        "exit_commission_bps": 8.0,
        "spread_bps": 1.0,
        "slippage_bps": 1.6,
        "provenance": "Coinbase Advanced Institutional high-volume tier"
    },
    "ACTIVE_TRADER_27BPS": {
        "round_trip_bps": 27.0,
        "entry_commission_bps": 10.0,
        "exit_commission_bps": 10.0,
        "spread_bps": 3.0,
        "slippage_bps": 4.0,
        "provenance": "Coinbase Advanced Tier 3 active taker round-trip (Primary benchmark)"
    },
    "RETAIL_87BPS": {
        "round_trip_bps": 87.0,
        "entry_commission_bps": 40.0,
        "exit_commission_bps": 40.0,
        "spread_bps": 3.0,
        "slippage_bps": 4.0,
        "provenance": "Coinbase Advanced Retail Tier 1 (<$10k) taker round-trip"
    }
}


@dataclass(frozen=True)
class L2GatedCandidateRecord:
    """
    Phase A: Immutable record emitted at decision time t0.
    Frozen dataclass to prevent post-decision mutation.
    """
    record_type: str  # "L2_GATED_CANDIDATE"
    schema_version: str  # "PROSPECTIVE_L2_GATED_V1"
    candidate_id: str
    strategy_id: str
    strategy_spec_hash: str
    instrument_id: str
    venue: str
    market_type: str
    decision_timestamp_utc: str
    fill_timestamp_utc: str
    entry_reference_price: float
    proposed_entry_price: float
    stop_loss_price: float
    take_profit_price: float
    direction: str  # "LONG"
    horizon_bars: int  # 168 hourly bars
    risk_unit_usd: float
    cost_scenario: str
    round_trip_friction_bps: float
    gate_decision: str  # "GATE_ACCEPTED_SHADOW", "GATE_REJECTED_TOXIC_OFI", "GATE_REJECTED_HEAVY_ASK", "GATE_REJECTED_WIDE_SPREAD", "GATE_ABSTAIN_L2_UNAVAILABLE"
    rejection_reason: Optional[str]
    l2_snapshot: Dict[str, Any]
    execution_authorization: str = "DISABLED — ANALYSIS ONLY"
    governance_status: str = "OFFLINE_RESEARCH_ONLY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class L2GatedOutcomeRecord:
    """
    Phase B: Immutable outcome record emitted after position conclusion.
    Links to candidate_id without rewriting the original candidate entry.
    """
    record_type: str  # "L2_GATED_OUTCOME"
    schema_version: str  # "PROSPECTIVE_L2_GATED_V1"
    candidate_id: str
    strategy_id: str
    resolution_status: str  # "RESOLVED", "TIMEOUT", "AMBIGUOUS", "EXCLUDED"
    exit_reason: str  # "TAKE_PROFIT", "STOP_LOSS", "TIMEOUT"
    is_ambiguous_touch: bool
    entry_timestamp_utc: str
    exit_timestamp_utc: str
    entry_fill_price: float
    exit_price: float
    bars_held: int
    gross_return_bps: float
    net_returns_by_scenario_bps: Dict[str, float]
    risk_unit_usd: float
    gross_r: float
    net_r_by_scenario: Dict[str, float]
    mfe_r: float
    mae_r: float
    gate_decision: str
    was_shadow_gated_accepted: bool
    resolution_timestamp_utc: str
    execution_authorization: str = "DISABLED — ANALYSIS ONLY"
    governance_status: str = "OFFLINE_RESEARCH_ONLY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProspectiveL2GatedLedger:
    """
    Thread-safe and cross-process safe append-only storage for L2-gated shadow research.
    Guarantees:
    - Never modifies existing lines or truncates files.
    - Prevents candidate duplicate registrations.
    - Cross-process locking via filelock.FileLock.
    - Strict atomic append with OS flush.
    """

    def __init__(self, ledger_path: Optional[str] = None, lock_path: Optional[str] = None):
        self.ledger_path = ledger_path or DEFAULT_L2_GATED_LEDGER_PATH
        self.lock_path = lock_path or (self.ledger_path + ".lock")
        self._thread_lock = threading.Lock()
        self._file_lock = FileLock(self.lock_path, timeout=10.0)
        self._registered_candidate_ids: set[str] = set()
        self._resolved_candidate_ids: set[str] = set()
        self._ensure_file_and_index()

    def _ensure_file_and_index(self) -> None:
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
        if not os.path.exists(self.ledger_path):
            with open(self.ledger_path, "w", encoding="utf-8") as f:
                pass
            return
        self._reindex_from_disk()

    def _reindex_from_disk(self) -> None:
        if not os.path.exists(self.ledger_path):
            return
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                clean = line.strip()
                if not clean:
                    continue
                try:
                    rec = json.loads(clean)
                    c_id = rec.get("candidate_id")
                    rec_type = rec.get("record_type")
                    if c_id:
                        if rec_type == "L2_GATED_CANDIDATE":
                            self._registered_candidate_ids.add(c_id)
                        elif rec_type == "L2_GATED_OUTCOME":
                            self._resolved_candidate_ids.add(c_id)
                except Exception:
                    pass

    def append_candidate(self, record: L2GatedCandidateRecord) -> bool:
        """Appends a Phase A candidate record idempotently."""
        with self._thread_lock:
            with self._file_lock:
                self._reindex_from_disk()
                if record.candidate_id in self._registered_candidate_ids:
                    logger.warning(f"Candidate {record.candidate_id} already registered. Skipping duplicate write.")
                    return False

                line = json.dumps(record.to_dict()) + "\n"
                with open(self.ledger_path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
                    os.fsync(f.fileno())

                self._registered_candidate_ids.add(record.candidate_id)
                return True

    def append_outcome(self, record: L2GatedOutcomeRecord) -> bool:
        """Appends a Phase B outcome record idempotently."""
        with self._thread_lock:
            with self._file_lock:
                self._reindex_from_disk()
                if record.candidate_id in self._resolved_candidate_ids:
                    logger.warning(f"Outcome for candidate {record.candidate_id} already recorded. Skipping duplicate.")
                    return False

                line = json.dumps(record.to_dict()) + "\n"
                with open(self.ledger_path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
                    os.fsync(f.fileno())

                self._resolved_candidate_ids.add(record.candidate_id)
                return True

    def read_all_records(self) -> List[Dict[str, Any]]:
        """Reads all records from the ledger."""
        if not os.path.exists(self.ledger_path):
            return []
        records = []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                clean = line.strip()
                if clean:
                    try:
                        records.append(json.loads(clean))
                    except Exception:
                        pass
        return records


class L2ShadowGatingEngine:
    """
    Evaluates contemporaneous L2 microstructure features against candidate setups,
    executes frozen protocol gating rules, and logs two-phase auditable records.
    """

    def __init__(
        self,
        ledger: Optional[ProspectiveL2GatedLedger] = None,
        tracker: Optional[OrderBookTracker] = None,
        cost_scenario: str = PRIMARY_COST_SCENARIO
    ):
        self.ledger = ledger or ProspectiveL2GatedLedger()
        self.tracker = tracker or OrderBookTracker()
        self.cost_scenario = cost_scenario

    def evaluate_gate(
        self,
        snapshot: L2MicrostructureSnapshot
    ) -> Tuple[str, Optional[str]]:
        """
        Evaluates frozen pre-registration gate criteria on an L2 snapshot:
        1. Feed health & synchronization check.
        2. OFI > 0.0 check (positive order flow into breakout).
        3. OBI_5 > -0.20 check (depth bid support).
        4. Spread <= 5.0 bps check (tight liquidity).

        Returns:
            (gate_decision, rejection_reason)
        """
        if not snapshot.is_available or not snapshot.is_feed_synchronized:
            reason = snapshot.reason_code or "L2_FEED_DESYNCHRONIZED_OR_STALE"
            return "GATE_ABSTAIN_L2_UNAVAILABLE", reason

        # OFI Check: Cont, Kukanov & Stoikov (2014)
        if snapshot.ofi_value is None:
            return "GATE_ABSTAIN_L2_UNAVAILABLE", "Order Flow Imbalance warming up or unavailable (< 15m valid continuous history)"
        if snapshot.ofi_value <= 0.0:
            return "GATE_REJECTED_TOXIC_OFI", f"Order Flow Imbalance ({snapshot.ofi_value:.4f}) <= 0.0 indicates adverse order flow"

        # OBI Check: Top 5 levels book depth
        if snapshot.obi_5 is None or snapshot.obi_5 <= -0.20:
            val_str = f"{snapshot.obi_5:.4f}" if snapshot.obi_5 is not None else "None"
            return "GATE_REJECTED_HEAVY_ASK", f"Order Book Imbalance OBI_5 ({val_str}) <= -0.20 indicates heavy ask pressure"

        # Spread Check: Top-of-book relative spread
        if snapshot.spread_bps is None or snapshot.spread_bps > 5.0:
            val_str = f"{snapshot.spread_bps:.2f}" if snapshot.spread_bps is not None else "None"
            return "GATE_REJECTED_WIDE_SPREAD", f"Top-of-book spread ({val_str} bps) exceeds 5.0 bps limit"

        return "GATE_ACCEPTED_SHADOW", None

    def process_candidate(
        self,
        candidate: CandidateSetup,
        decision_epoch: float,
        l2_snapshot: Optional[L2MicrostructureSnapshot] = None
    ) -> L2GatedCandidateRecord:
        """
        Extracts L2 snapshot at decision_epoch (if not provided), applies gating,
        and appends Phase A candidate record to the ledger.
        """
        if l2_snapshot is None:
            l2_snapshot = self.tracker.extract_microstructure_snapshot(decision_epoch=decision_epoch)

        gate_decision, rejection_reason = self.evaluate_gate(l2_snapshot)

        record = L2GatedCandidateRecord(
            record_type="L2_GATED_CANDIDATE",
            schema_version="PROSPECTIVE_L2_GATED_V1",
            candidate_id=candidate.candidate_id,
            strategy_id=candidate.strategy_archetype,
            strategy_spec_hash=STRATEGY_SPEC_HASH,
            instrument_id=candidate.instrument_id,
            venue=candidate.venue,
            market_type=candidate.market_type,
            decision_timestamp_utc=candidate.decision_timestamp_utc,
            fill_timestamp_utc=candidate.fill_timestamp_utc,
            entry_reference_price=candidate.entry_reference_price,
            proposed_entry_price=candidate.proposed_entry_price,
            stop_loss_price=candidate.stop_loss_price,
            take_profit_price=candidate.take_profit_price,
            direction=candidate.direction,
            horizon_bars=candidate.horizon_bars,
            risk_unit_usd=candidate.risk_unit_usd,
            cost_scenario=self.cost_scenario,
            round_trip_friction_bps=COST_REGISTRY_BPS.get(self.cost_scenario, {}).get("round_trip_bps", 27.0),
            gate_decision=gate_decision,
            rejection_reason=rejection_reason,
            l2_snapshot=l2_snapshot.to_dict()
        )

        self.ledger.append_candidate(record)
        return record

    def resolve_candidate_outcome(
        self,
        candidate: CandidateSetup,
        gate_decision: str,
        forward_bars: List[Dict[str, Any]],
        resolution_epoch: Optional[float] = None
    ) -> L2GatedOutcomeRecord:
        """
        Deterministically resolves the candidate against forward OHLCV candles,
        calculates gross & net metrics across all registered cost scenarios,
        and appends Phase B outcome record to the ledger.
        """
        outcome: ResolutionOutcome = DeterministicBarrierResolver.resolve_candidate(candidate, forward_bars)

        entry_p = candidate.proposed_entry_price
        exit_p = outcome.exit_fill_price
        risk_unit = candidate.risk_unit_usd

        # Gross return calculations
        gross_return_bps = ((exit_p - entry_p) / entry_p) * 10000.0
        gross_r = float(outcome.gross_r)

        # Net returns across fee scenarios
        net_returns_by_scenario_bps: Dict[str, float] = {}
        net_r_by_scenario: Dict[str, float] = {}

        for scenario_name, scenario_meta in COST_REGISTRY_BPS.items():
            rt_bps = scenario_meta["round_trip_bps"]
            net_bps = gross_return_bps - rt_bps
            net_returns_by_scenario_bps[scenario_name] = round(net_bps, 2)

            # Convert friction to R: Friction_R = (rt_bps / 10000) / (risk_unit / entry_p)
            friction_r = (rt_bps / 10000.0) / (risk_unit / entry_p)
            net_r_by_scenario[scenario_name] = round(gross_r - friction_r, 4)

        res_epoch = resolution_epoch if resolution_epoch is not None else datetime.now(timezone.utc).timestamp()
        res_time_utc = datetime.fromtimestamp(res_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")

        record = L2GatedOutcomeRecord(
            record_type="L2_GATED_OUTCOME",
            schema_version="PROSPECTIVE_L2_GATED_V1",
            candidate_id=candidate.candidate_id,
            strategy_id=candidate.strategy_archetype,
            resolution_status=outcome.resolution_status,
            exit_reason=outcome.exit_reason,
            is_ambiguous_touch=outcome.is_ambiguous_touch,
            entry_timestamp_utc=candidate.fill_timestamp_utc,
            exit_timestamp_utc=outcome.exit_timestamp_utc,
            entry_fill_price=entry_p,
            exit_price=exit_p,
            bars_held=outcome.bars_held,
            gross_return_bps=round(gross_return_bps, 2),
            net_returns_by_scenario_bps=net_returns_by_scenario_bps,
            risk_unit_usd=risk_unit,
            gross_r=round(gross_r, 4),
            net_r_by_scenario=net_r_by_scenario,
            mfe_r=round(float(outcome.mfe_r), 4),
            mae_r=round(float(outcome.mae_r), 4),
            gate_decision=gate_decision,
            was_shadow_gated_accepted=(gate_decision == "GATE_ACCEPTED_SHADOW"),
            resolution_timestamp_utc=res_time_utc
        )

        self.ledger.append_outcome(record)
        return record

    def compute_evaluation_summary(self) -> Dict[str, Any]:
        """
        Computes comparative research evaluation metrics between the ungated control
        cohort and the L2-gated cohort across all recorded outcomes.
        """
        records = self.ledger.read_all_records()
        candidates = {r["candidate_id"]: r for r in records if r.get("record_type") == "L2_GATED_CANDIDATE"}
        outcomes = [r for r in records if r.get("record_type") == "L2_GATED_OUTCOME"]

        total_candidates = len(candidates)
        total_outcomes = len(outcomes)

        if total_outcomes == 0:
            return {
                "status": "NO_RESOLVED_OUTCOMES",
                "total_candidates": total_candidates,
                "total_outcomes": 0,
                "confirmatory_gate_decision": "NOT_STARTED_INSUFFICIENT_SAMPLE"
            }

        control_outcomes = outcomes
        gated_outcomes = [o for o in outcomes if o.get("was_shadow_gated_accepted", False)]
        rejected_outcomes = [o for o in outcomes if not o.get("was_shadow_gated_accepted", False)]

        def _stats_for_cohort(cohort: List[Dict[str, Any]]) -> Dict[str, Any]:
            if not cohort:
                return {"count": 0, "mean_gross_r": 0.0, "mean_net_r_27bps": 0.0, "win_rate": 0.0}
            n = len(cohort)
            gross_r_vals = [c["gross_r"] for c in cohort]
            net_r_27_vals = [c["net_r_by_scenario"].get("ACTIVE_TRADER_27BPS", c["gross_r"]) for c in cohort]
            net_r_87_vals = [c["net_r_by_scenario"].get("RETAIL_87BPS", c["gross_r"]) for c in cohort]
            wins = sum(1 for r in gross_r_vals if r > 0)
            return {
                "count": n,
                "mean_gross_r": round(float(np.mean(gross_r_vals)), 4),
                "std_gross_r": round(float(np.std(gross_r_vals)), 4) if n > 1 else 0.0,
                "mean_net_r_27bps": round(float(np.mean(net_r_27_vals)), 4),
                "mean_net_r_87bps": round(float(np.mean(net_r_87_vals)), 4),
                "win_rate": round(float(wins / n), 4),
                "min_r": round(float(np.min(gross_r_vals)), 4),
                "max_r": round(float(np.max(gross_r_vals)), 4)
            }

        control_stats = _stats_for_cohort(control_outcomes)
        gated_stats = _stats_for_cohort(gated_outcomes)
        rejected_stats = _stats_for_cohort(rejected_outcomes)

        delta_net_r = round(gated_stats["mean_net_r_27bps"] - control_stats["mean_net_r_27bps"], 4) if gated_stats["count"] > 0 else 0.0

        # Sample sufficiency check (N >= 100 clean non-overlapping trades required by frozen protocol)
        is_sample_sufficient = gated_stats["count"] >= 100
        confirmatory_decision = "COLLECTING_INSUFFICIENT_SAMPLE"
        if is_sample_sufficient:
            if gated_stats["mean_net_r_27bps"] > 0.0 and delta_net_r >= 0.20:
                confirmatory_decision = "CONFIRMATORY_GATE_PASS"
            else:
                confirmatory_decision = "CONFIRMATORY_GATE_FAIL_REJECT_H1"

        return {
            "status": "RESOLVED_METRICS_AVAILABLE",
            "total_candidates": total_candidates,
            "total_outcomes": total_outcomes,
            "control_cohort": control_stats,
            "gated_cohort": gated_stats,
            "rejected_cohort": rejected_stats,
            "delta_mean_net_r_27bps": delta_net_r,
            "is_sample_sufficient_for_confirmatory_gate": is_sample_sufficient,
            "confirmatory_gate_decision": confirmatory_decision,
            "governance_status": "OFFLINE_RESEARCH_ONLY",
            "live_trading": "DISABLED"
        }
