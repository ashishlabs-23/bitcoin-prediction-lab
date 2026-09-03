"""
engine/opportunity_definition.py — Level 0.5 Opportunity & Target Formulation Engine
====================================================================================
Establishes the foundational opportunity definition before path, execution, and selection:
  1. Target Contract Specification: TargetContract = (entry, TP, SL, direction, tau_max, hash).
  2. Opportunity Census & Funnel Ledger: Raw -> Event -> Qualified -> Executable -> Executed -> Profitable.
  3. Event Clustering & Overlap Control: Groups dependent bursts into independent blocks (N_raw vs N_blocks).
  4. Mechanism Co-Occurrence Graph: Disentangles simultaneous triggers (e.g. IGNITION + VACUUM + TOXICITY).
  5. Portfolio Exposure & Aggregate Impact: Tracks directional exposure & nonlinear Impact(sum(q)).
  6. Formal Causal Role Taxonomy: PRE_TREATMENT, TREATMENT, OUTCOME, MEDIATOR.
"""

import os
import sys
import json
import hashlib
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd


class CausalRole(str, Enum):
    PRE_TREATMENT = "PRE_TREATMENT"   # State, Event, Historical Features (Available <= t0)
    TREATMENT = "TREATMENT"           # Decision Action, Execution Mode, Position Size
    OUTCOME = "OUTCOME"               # Future Path, MFE, MAE, Gross/Net PnL
    MEDIATOR = "MEDIATOR"             # Fill Latency, Queue Position, Adverse Selection


@dataclass
class TargetContract:
    """
    Explicit, pre-registered trade target contract defining the exact outcome space at t_0.
    """
    entry_price: float
    tp_price: float
    sl_price: float
    direction: str              # "LONG" | "SHORT"
    max_hold_seconds: int       # tau_max
    pt_mult: float = 2.0        # TP in units of ATR / volatility
    sl_mult: float = 1.0        # SL in units of ATR / volatility
    contract_hash: str = ""

    def __post_init__(self):
        if not self.contract_hash:
            payload = {
                "entry": round(self.entry_price, 2),
                "tp": round(self.tp_price, 2),
                "sl": round(self.sl_price, 2),
                "dir": self.direction.upper(),
                "tau": self.max_hold_seconds,
                "pt": self.pt_mult,
                "sl_m": self.sl_mult
            }
            json_str = json.dumps(payload, sort_keys=True)
            self.contract_hash = hashlib.sha256(json_str.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EventClusterer:
    """
    Clusters overlapping event triggers within tau_max to distinguish raw triggers
    from statistically independent event blocks (N_raw vs N_blocks).
    """

    def __init__(self, cluster_window_seconds: int = 1800):
        self.cluster_window_seconds = cluster_window_seconds
        self.active_clusters: Dict[str, Dict[str, Any]] = {} # cluster_id -> metadata

    def process_trigger(
        self,
        event_type: str,
        timestamp_iso: str,
        price: float
    ) -> Dict[str, Any]:
        """
        Assigns an incoming event trigger to an existing cluster or spawns a new independent block.
        """
        ts_dt = pd.to_datetime(timestamp_iso, utc=True)
        assigned_cluster = None
        is_primary = False

        # Check existing active clusters for this event_type
        for c_id, c_meta in list(self.active_clusters.items()):
            if c_meta["event_type"] == event_type:
                start_dt = pd.to_datetime(c_meta["start_time"], utc=True)
                if (ts_dt - start_dt).total_seconds() <= self.cluster_window_seconds:
                    assigned_cluster = c_id
                    c_meta["trigger_count"] += 1
                    c_meta["last_trigger_time"] = timestamp_iso
                    break
                else:
                    # Expired cluster
                    del self.active_clusters[c_id]

        if assigned_cluster is None:
            # New independent block
            c_id = f"CLUST-{event_type}-{ts_dt.strftime('%Y%m%d%H%M%S')}"
            self.active_clusters[c_id] = {
                "cluster_id": c_id,
                "event_type": event_type,
                "start_time": timestamp_iso,
                "last_trigger_time": timestamp_iso,
                "trigger_count": 1,
                "primary_price": price
            }
            assigned_cluster = c_id
            is_primary = True

        return {
            "cluster_id": assigned_cluster,
            "is_primary_block_event": is_primary,
            "cluster_trigger_index": self.active_clusters[assigned_cluster]["trigger_count"],
            "cluster_window_seconds": self.cluster_window_seconds
        }


class MechanismCoOccurrenceLedger:
    """
    Tracks and disentangles simultaneous mechanism activations (e.g. IGNITION + VACUUM + TOXICITY).
    """

    def analyze_composition(self, active_mechanisms: List[str]) -> Dict[str, Any]:
        """
        Analyzes the composition of active mechanisms at a single bar.
        """
        if not active_mechanisms:
            return {
                "composition_type": "ISOLATED_NONE",
                "primary_mechanism": "NONE",
                "co_mechanisms": [],
                "co_occurrence_count": 0,
                "composition_hash": "none"
            }

        sorted_mechs = sorted(active_mechanisms)
        comp_str = "+".join(sorted_mechs)
        comp_hash = hashlib.sha256(comp_str.encode("utf-8")).hexdigest()[:12]

        primary = sorted_mechs[0]
        co_mechs = sorted_mechs[1:]

        return {
            "composition_type": "SINGLE" if len(active_mechanisms) == 1 else "CONCURRENT_MULTI",
            "primary_mechanism": primary,
            "co_mechanisms": co_mechs,
            "co_occurrence_count": len(active_mechanisms),
            "composition_label": comp_str,
            "composition_hash": comp_hash
        }


def generate_opportunity_id(
    t_0: str,
    asset: str,
    event_type: str,
    contract_hash: str,
    state_hash: str
) -> str:
    """
    Deterministic opportunity identity:
    OPP-{t_0[:10]}-{asset}-{event_type}-{SHA256(t_0 || asset || event || contract || state)[:8]}
    """
    payload = f"{t_0}_{asset}_{event_type}_{contract_hash}_{state_hash}"
    opp_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]
    date_prefix = pd.to_datetime(t_0, utc=True).strftime('%Y%m%d') if t_0 else "NODATE"
    return f"OPP-{date_prefix}-{asset.upper()}-{event_type.upper()}-{opp_hash}"


class OpportunityCensusLedger:
    """
    Formal audit ledger tracking the 6-stage Opportunity Lifecycle Funnel:
      Stage 1: Raw Observations (Candles / Ticks evaluated)
      Stage 2: Mechanism Events Detected
      Stage 3: Qualified Opportunities (State & Path Evidence Valid)
      Stage 4: Executable Opportunities (Net EV > 0 after all friction)
      Stage 5: Executed Trades (Risk & Capacity Authorized)
      Stage 6: Resolved Trades (Matured & Chained into Ledger)

    Followed by the Resolved Outcome Partition:
      - Profitable Trades (Net PnL > 0)
      - Non-Profitable Trades (Net PnL <= 0)
    """

    def __init__(self, ledger_file: Optional[str] = None):
        self.ledger_file = ledger_file or os.path.join("experiments", "results", "opportunity_census.json")
        self.funnel_counts = {
            "stage1_raw_observations": 0,
            "stage2_mechanism_events": 0,
            "stage3_qualified_opportunities": 0,
            "stage4_executable_opportunities": 0,
            "stage5_executed_trades": 0,
            "stage6_resolved_trades": 0
        }
        self.outcome_partition = {
            "profitable_trades": 0,
            "non_profitable_trades": 0
        }
        self.abstention_records: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.ledger_file):
            try:
                with open(self.ledger_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.funnel_counts.update(data.get("funnel_counts", {}))
                    self.outcome_partition.update(data.get("outcome_partition", {}))
                    self.abstention_records = data.get("abstention_records", [])
            except Exception:
                pass

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.ledger_file), exist_ok=True)
        try:
            payload = {
                "funnel_counts": self.funnel_counts,
                "outcome_partition": self.outcome_partition,
                "abstention_records": self.abstention_records[-200:] # Keep last 200 for audit
            }
            with open(self.ledger_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    def log_observation(
        self,
        has_event: bool,
        is_qualified: bool,
        is_executable: bool,
        is_executed: bool,
        is_resolved: bool = False,
        is_profitable: Optional[bool] = None,
        abstained_counterfactual_net_bps: Optional[float] = None
    ) -> None:
        """Increments the respective lifecycle stage and logs outcome partition."""
        self.funnel_counts["stage1_raw_observations"] += 1
        if has_event:
            self.funnel_counts["stage2_mechanism_events"] += 1
        if is_qualified:
            self.funnel_counts["stage3_qualified_opportunities"] += 1
        if is_executable:
            self.funnel_counts["stage4_executable_opportunities"] += 1
        if is_executed:
            self.funnel_counts["stage5_executed_trades"] += 1
        if is_resolved:
            self.funnel_counts["stage6_resolved_trades"] += 1
            if is_profitable is True:
                self.outcome_partition["profitable_trades"] += 1
            elif is_profitable is False:
                self.outcome_partition["non_profitable_trades"] += 1

        # Track Abstention Value if trade was abstained/blocked
        if not is_executed and abstained_counterfactual_net_bps is not None:
            # AV_i = PnL_policy (0) - PnL_counterfactual = -PnL_counterfactual
            # If counterfactual lost 15 bps, AV_i = +15 bps (abstention saved money)
            av_i = -abstained_counterfactual_net_bps
            self.abstention_records.append({
                "counterfactual_net_bps": abstained_counterfactual_net_bps,
                "abstention_value_bps": av_i,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        self._save()

    def compute_abstention_value_summary(self) -> Dict[str, Any]:
        """
        Computes aggregate Abstention Value: AV_aggregate = sum(AV_i).
        Measures whether the abstention filter removed more losing trades than winning trades.
        """
        if not self.abstention_records:
            return {
                "total_abstained_count": 0,
                "aggregate_abstention_value_bps": 0.0,
                "avoided_loss_count": 0,
                "missed_profit_count": 0,
                "filter_efficiency_ratio": 0.0
            }

        av_vals = [r["abstention_value_bps"] for r in self.abstention_records]
        agg_av = float(np.sum(av_vals))
        avoided_losses = sum(1 for v in av_vals if v > 0)
        missed_profits = sum(1 for v in av_vals if v < 0)
        ratio = (avoided_losses / max(1, missed_profits)) if missed_profits > 0 else float(avoided_losses)

        return {
            "total_abstained_count": len(self.abstention_records),
            "aggregate_abstention_value_bps": round(agg_av, 2),
            "avoided_loss_count": avoided_losses,
            "missed_profit_count": missed_profits,
            "filter_efficiency_ratio": round(ratio, 2)
        }

    def get_funnel_metrics(self) -> Dict[str, Any]:
        """
        Computes formal Opportunity Conversion Rates and separate Resolved Outcome Partitions.
        """
        raw = self.funnel_counts["stage1_raw_observations"]
        events = self.funnel_counts["stage2_mechanism_events"]
        qualified = self.funnel_counts["stage3_qualified_opportunities"]
        executable = self.funnel_counts["stage4_executable_opportunities"]
        executed = self.funnel_counts["stage5_executed_trades"]
        resolved = self.funnel_counts["stage6_resolved_trades"]

        profitable = self.outcome_partition["profitable_trades"]
        non_profitable = self.outcome_partition["non_profitable_trades"]

        r_event = (events / raw) if raw > 0 else 0.0
        r_qualification = (qualified / events) if events > 0 else 0.0
        r_convert_executable = (executable / qualified) if qualified > 0 else 0.0
        r_execution = (executed / executable) if executable > 0 else 0.0
        r_resolution = (resolved / executed) if executed > 0 else 0.0
        win_rate = (profitable / resolved) if resolved > 0 else 0.0

        return {
            "lifecycle_funnel_counts": dict(self.funnel_counts),
            "funnel_counts": dict(self.funnel_counts),
            "resolved_outcomes": {
                "profitable_trades": profitable,
                "non_profitable_trades": non_profitable,
                "win_rate": round(win_rate, 4)
            },
            "rates": {
                "r_event_detection": round(r_event, 4),
                "r_qualification": round(r_qualification, 4),
                "r_opportunity_conversion_ocr": round(r_convert_executable, 4),
                "r_execution_capture": round(r_execution, 4),
                "r_resolution": round(r_resolution, 4),
                "r_win_rate": round(win_rate, 4)
            },
            "abstention_value": self.compute_abstention_value_summary()
        }


class PortfolioExposureLedger:
    """
    Tracks simultaneous multi-strategy exposure and nonlinear aggregate impact:
      Impact_total = Impact(sum(q_i)) != sum(Impact(q_i))
    """

    def __init__(self, adv_usd: float = 50_000_000.0):
        self.adv_usd = adv_usd
        self.active_positions: Dict[str, Dict[str, Any]] = {}

    def register_position(self, strategy_id: str, direction: str, notional_usd: float) -> None:
        self.active_positions[strategy_id] = {
            "direction": direction.upper(),
            "notional_usd": notional_usd
        }

    def close_position(self, strategy_id: str) -> None:
        if strategy_id in self.active_positions:
            del self.active_positions[strategy_id]

    def compute_aggregate_exposure_and_impact(self) -> Dict[str, Any]:
        """
        Computes net directional exposure and nonlinear portfolio impact.
        """
        net_long_usd = 0.0
        net_short_usd = 0.0
        gross_usd = 0.0

        for pos in self.active_positions.values():
            n = pos["notional_usd"]
            gross_usd += n
            if pos["direction"] == "LONG":
                net_long_usd += n
            else:
                net_short_usd += n

        net_directional_usd = net_long_usd - net_short_usd

        # Nonlinear square root portfolio impact model
        aggregate_impact_bps = float(
            0.10 * np.sqrt(max(100.0, gross_usd) / self.adv_usd) * 100.0
        )

        return {
            "gross_portfolio_notional_usd": round(gross_usd, 2),
            "net_directional_notional_usd": round(net_directional_usd, 2),
            "active_strategy_count": len(self.active_positions),
            "nonlinear_aggregate_impact_bps": round(aggregate_impact_bps, 2)
        }


class OpportunityPopulationLedger:
    """
    Permanent audit ledger of all candidate opportunities across time.
    Provides idempotency and worker deduplication:
    Ensures 1 Opportunity -> Exactly 1 Canonical Decision -> At Most 1 Resolution.
    Also provides paired 4-policy ablation on the identical opportunity stream.
    """

    def __init__(self, ledger_file: Optional[str] = None):
        self.ledger_file = ledger_file or os.path.join("experiments", "results", "opportunity_population.jsonl")
        self.registered_opp_ids: set = set()
        self._load_index()

    def _load_index(self) -> None:
        if os.path.exists(self.ledger_file):
            try:
                with open(self.ledger_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            self.registered_opp_ids.add(entry.get("opportunity_id"))
            except Exception:
                pass

    def register_opportunity(
        self,
        opportunity_id: str,
        t_0: str,
        asset: str,
        event_meta: Dict[str, Any],
        state_meta: Dict[str, Any],
        contract: Dict[str, Any],
        cluster_id: str,
        population_definition_hash: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Idempotently registers an opportunity. Returns (is_new, record).
        If already registered by a concurrent worker, returns (False, existing_record).
        """
        if opportunity_id in self.registered_opp_ids:
            return False, {"opportunity_id": opportunity_id, "status": "ALREADY_REGISTERED"}

        record = {
            "opportunity_id": opportunity_id,
            "t_0": t_0,
            "asset": asset,
            "event": event_meta,
            "state": state_meta,
            "contract": contract,
            "cluster_id": cluster_id,
            "population_definition_hash": population_definition_hash,
            "registered_at": datetime.now(timezone.utc).isoformat()
        }

        os.makedirs(os.path.dirname(self.ledger_file), exist_ok=True)
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        self.registered_opp_ids.add(opportunity_id)
        return True, record

    def evaluate_four_policy_ablation(
        self,
        opportunities: List[Dict[str, Any]],
        future_realized_returns_bps: List[float],
        execution_drags_bps: List[float],
        c2_risks_authorized: List[bool],
        path_edges_authorized: List[bool]
    ) -> Dict[str, Any]:
        """
        Executes true paired counterfactual ablation across 4 policies on the IDENTICAL opportunity stream:
          Policy A: Signal Only (enters whenever raw gross signal > 0)
          Policy B: Signal + Execution (enters whenever gross > drag)
          Policy C: Signal + Execution + C2 Risk (enters when gross > drag AND C2 authorized)
          Policy D: Full Decision Anatomy (enters when gross > drag + buffer AND C2 authorized AND path valid)
        """
        n = len(opportunities)
        pnl_a, pnl_b, pnl_c, pnl_d = [], [], [], []

        for i in range(n):
            realized_gross = future_realized_returns_bps[i]
            drag = execution_drags_bps[i]
            realized_net = realized_gross - drag
            c2_ok = c2_risks_authorized[i]
            path_ok = path_edges_authorized[i]

            # Policy A: Signal Only (naive entry)
            take_a = realized_gross > 0
            pnl_a.append(realized_net if take_a else 0.0)

            # Policy B: Signal + Execution Frictions
            take_b = realized_gross > drag
            pnl_b.append(realized_net if take_b else 0.0)

            # Policy C: Signal + Execution + C2 Risk Authorization
            take_c = take_b and c2_ok
            pnl_c.append(realized_net if take_c else 0.0)

            # Policy D: Full Decision Anatomy
            take_d = (realized_gross > (drag + 2.0)) and c2_ok and path_ok
            pnl_d.append(realized_net if take_d else 0.0)

        ev_a = float(np.mean(pnl_a)) if pnl_a else 0.0
        ev_b = float(np.mean(pnl_b)) if pnl_b else 0.0
        ev_c = float(np.mean(pnl_c)) if pnl_c else 0.0
        ev_d = float(np.mean(pnl_d)) if pnl_d else 0.0

        return {
            "opportunity_count": n,
            "policy_ev_bps": {
                "policy_a_signal_only": round(ev_a, 2),
                "policy_b_signal_and_execution": round(ev_b, 2),
                "policy_c_signal_exec_and_risk": round(ev_c, 2),
                "policy_d_full_decision_anatomy": round(ev_d, 2)
            },
            "paired_deltas_bps": {
                "delta_execution_value_b_minus_a": round(ev_b - ev_a, 2),
                "delta_risk_value_c_minus_b": round(ev_c - ev_b, 2),
                "delta_anatomy_value_d_minus_c": round(ev_d - ev_c, 2),
                "total_architectural_value_d_minus_a": round(ev_d - ev_a, 2)
            }
        }


def generate_opportunity_id(
    t_0: str,
    asset: str,
    event_type: str,
    contract_hash: Optional[str] = None,
    state_hash: Optional[str] = None,
    event_features: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    Generates a deterministic opportunity identifier based on t_0, asset, event type, and pre-treatment features.
    """
    raw = f"{t_0}_{asset}_{event_type}"
    if contract_hash:
        raw += f"_{contract_hash}"
    if state_hash:
        raw += f"_{state_hash}"
    if event_features:
        raw += f"_{json.dumps(event_features, sort_keys=True)}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    clean_date = t_0[:10].replace("-", "") if len(t_0) >= 10 else "DATE"
    return f"OPP-{clean_date}-{h}"


# Global Singletons
event_clusterer = EventClusterer()
mechanism_cooccurrence = MechanismCoOccurrenceLedger()
opportunity_census = OpportunityCensusLedger()
portfolio_exposure = PortfolioExposureLedger()
opportunity_population = OpportunityPopulationLedger()

