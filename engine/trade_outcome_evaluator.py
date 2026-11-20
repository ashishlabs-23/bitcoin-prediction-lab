"""
engine/trade_outcome_evaluator.py — Cost, Outcome and Uncertainty Evaluation Contract
====================================================================================
Evaluates candidate trade payoffs in standardized risk units (1R = entry-to-stop distance),
enforces mutually exclusive probability partitions (p_TP + p_SL + p_TO = 1.0),
calculates signed net expected value EV_net, and validates statistical uncertainty.

Current Governance Blocker:
- A trained, calibrated triple-barrier meta-model (estimating p_TP, p_SL, p_TO) does NOT
  currently exist in the repository.
- Directional GBDT probabilities P(UP)/P(DOWN) are return-sign forecasts and MUST NEVER
  be substituted for trade-outcome probabilities.
- Therefore, in this phase, outcome evaluation fails closed with reason META_MODEL_UNAVAILABLE.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
import numpy as np


@dataclass(frozen=True)
class OutcomeEvaluationResult:
    """Immutable evaluation result emitted by TradeOutcomeEvaluator."""
    is_eligible: bool
    status_code: str  # "ELIGIBLE", "META_MODEL_UNAVAILABLE", "NEGATIVE_NET_EXPECTANCY", etc.
    p_tp: Optional[float]
    p_sl: Optional[float]
    p_to: Optional[float]
    probability_sum: Optional[float]
    k_tp_r: float
    k_sl_r: float
    friction_bps: float
    friction_r: float
    expected_timeout_r: float
    expected_gross_r: Optional[float]
    expected_net_r: Optional[float]
    ci_95_lower_r: Optional[float]
    ci_95_upper_r: Optional[float]
    assumed_cost_scenario: str
    rejection_reason: Optional[str]
    audit_notes: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TradeOutcomeEvaluator:
    """
    Evaluates net expectancy and uncertainty under strict econometric contracts.
    """

    ASSUMED_COST_SCENARIOS = {
        "COINBASE_RETAIL_87BPS": {
            "round_trip_bps": 87.0,
            "taker_commission_per_side_bps": 40.0,
            "half_spread_per_side_bps": 1.5,
            "slippage_per_side_bps": 2.0,
            "description": "Assumed retail benchmark scenario (Coinbase Advanced Tier 1 taker)"
        },
        "COINBASE_ACTIVE_27BPS": {
            "round_trip_bps": 27.0,
            "taker_commission_per_side_bps": 10.0,
            "half_spread_per_side_bps": 1.5,
            "slippage_per_side_bps": 2.0,
            "description": "Assumed active/VIP benchmark scenario (Coinbase high-tier taker)"
        }
    }

    @classmethod
    def calculate_net_expectancy(
        cls,
        entry_price: float,
        stop_price: float,
        target_price: float,
        p_tp: Optional[float],
        p_sl: Optional[float],
        p_to: Optional[float],
        expected_timeout_r: float = 0.0,
        assumed_cost_scenario: str = "COINBASE_RETAIL_87BPS",
        custom_friction_bps: Optional[float] = None,
        uncertainty_half_width_r: Optional[float] = None
    ) -> OutcomeEvaluationResult:
        """
        Calculates EV_net using the closed-form 3-outcome triple-barrier equation.
        """
        # 1. Validate Geometry and Risk Units
        if entry_price <= 0 or stop_price <= 0 or target_price <= 0:
            return OutcomeEvaluationResult(
                is_eligible=False,
                status_code="INVALID_GEOMETRY",
                p_tp=None, p_sl=None, p_to=None, probability_sum=None,
                k_tp_r=0.0, k_sl_r=0.0, friction_bps=0.0, friction_r=0.0,
                expected_timeout_r=0.0, expected_gross_r=None, expected_net_r=None,
                ci_95_lower_r=None, ci_95_upper_r=None,
                assumed_cost_scenario=assumed_cost_scenario,
                rejection_reason="Prices must be strictly positive.",
                audit_notes={}
            )

        stop_distance = abs(entry_price - stop_price)
        target_distance = abs(target_price - entry_price)

        if stop_distance <= 0:
            return OutcomeEvaluationResult(
                is_eligible=False,
                status_code="INVALID_GEOMETRY",
                p_tp=None, p_sl=None, p_to=None, probability_sum=None,
                k_tp_r=0.0, k_sl_r=0.0, friction_bps=0.0, friction_r=0.0,
                expected_timeout_r=0.0, expected_gross_r=None, expected_net_r=None,
                ci_95_lower_r=None, ci_95_upper_r=None,
                assumed_cost_scenario=assumed_cost_scenario,
                rejection_reason="Stop distance must be strictly greater than zero.",
                audit_notes={}
            )

        # Standardized Risk Units: 1R = stop_distance
        k_sl_r = 1.0
        k_tp_r = target_distance / stop_distance

        # 2. Convert Friction to R-multiples
        if custom_friction_bps is not None:
            friction_bps = float(custom_friction_bps)
        else:
            scenario_info = cls.ASSUMED_COST_SCENARIOS.get(
                assumed_cost_scenario.upper(), cls.ASSUMED_COST_SCENARIOS["COINBASE_RETAIL_87BPS"]
            )
            friction_bps = scenario_info["round_trip_bps"]

        stop_pct = stop_distance / entry_price
        friction_pct = friction_bps / 10000.0
        friction_r = friction_pct / stop_pct

        # 3. Check Meta-Model Availability (CRITICAL CURRENT BLOCKER)
        if p_tp is None or p_sl is None or p_to is None:
            return OutcomeEvaluationResult(
                is_eligible=False,
                status_code="META_MODEL_UNAVAILABLE",
                p_tp=None, p_sl=None, p_to=None, probability_sum=None,
                k_tp_r=round(k_tp_r, 4),
                k_sl_r=round(k_sl_r, 4),
                friction_bps=round(friction_bps, 2),
                friction_r=round(friction_r, 4),
                expected_timeout_r=round(expected_timeout_r, 4),
                expected_gross_r=None,
                expected_net_r=None,
                ci_95_lower_r=None,
                ci_95_upper_r=None,
                assumed_cost_scenario=assumed_cost_scenario,
                rejection_reason="CRITICAL BLOCKER: No validated, calibrated triple-barrier meta-model exists. "
                                 "Directional GBDT probabilities cannot be substituted for p_TP.",
                audit_notes={"blocker": "META_MODEL_UNAVAILABLE"}
            )

        # 4. Validate Probability Partition Sum
        prob_sum = float(p_tp + p_sl + p_to)
        if not math.isclose(prob_sum, 1.0, abs_tol=1e-3):
            return OutcomeEvaluationResult(
                is_eligible=False,
                status_code="INVALID_PROBABILITIES",
                p_tp=p_tp, p_sl=p_sl, p_to=p_to, probability_sum=round(prob_sum, 4),
                k_tp_r=round(k_tp_r, 4), k_sl_r=round(k_sl_r, 4),
                friction_bps=round(friction_bps, 2), friction_r=round(friction_r, 4),
                expected_timeout_r=round(expected_timeout_r, 4),
                expected_gross_r=None, expected_net_r=None,
                ci_95_lower_r=None, ci_95_upper_r=None,
                assumed_cost_scenario=assumed_cost_scenario,
                rejection_reason=f"Probabilities do not sum to 1.0 (got {prob_sum:.4f}).",
                audit_notes={"probability_sum": prob_sum}
            )

        # 5. Closed-Form Expected Net R:
        # EV_net = p_TP*(k_tp - C_R) - p_SL*(k_sl + C_R) + p_TO*(E[R_TO] - C_R)
        ev_tp = p_tp * (k_tp_r - friction_r)
        ev_sl = p_sl * (k_sl_r + friction_r)
        ev_to = p_to * (expected_timeout_r - friction_r)

        ev_net = ev_tp - ev_sl + ev_to
        ev_gross = (p_tp * k_tp_r) - (p_sl * k_sl_r) + (p_to * expected_timeout_r)

        # 6. Uncertainty Lower Bound Check
        if uncertainty_half_width_r is None:
            ci_lower = None
            ci_upper = None
            uncertainty_passed = False
            uncertainty_reason = "UNCERTAINTY_NOT_ESTABLISHED: Empirical confidence interval is missing."
        else:
            ci_lower = ev_net - abs(uncertainty_half_width_r)
            ci_upper = ev_net + abs(uncertainty_half_width_r)
            uncertainty_passed = ci_lower > 0.0
            uncertainty_reason = (
                None if uncertainty_passed
                else f"STATISTICAL_UNCERTAINTY: 95% CI lower bound ({ci_lower:.4f}R) is not strictly positive."
            )

        # 7. Final Eligibility Evaluation
        if ev_net <= 0.0:
            return OutcomeEvaluationResult(
                is_eligible=False,
                status_code="NEGATIVE_NET_EXPECTANCY",
                p_tp=round(p_tp, 4), p_sl=round(p_sl, 4), p_to=round(p_to, 4),
                probability_sum=round(prob_sum, 4),
                k_tp_r=round(k_tp_r, 4), k_sl_r=round(k_sl_r, 4),
                friction_bps=round(friction_bps, 2), friction_r=round(friction_r, 4),
                expected_timeout_r=round(expected_timeout_r, 4),
                expected_gross_r=round(ev_gross, 4), expected_net_r=round(ev_net, 4),
                ci_95_lower_r=round(ci_lower, 4) if ci_lower is not None else None,
                ci_95_upper_r=round(ci_upper, 4) if ci_upper is not None else None,
                assumed_cost_scenario=assumed_cost_scenario,
                rejection_reason=f"Expected net return ({ev_net:.4f}R) is <= 0.0 after friction ({friction_r:.4f}R).",
                audit_notes={"ev_net": round(ev_net, 4), "friction_r": round(friction_r, 4)}
            )

        if not uncertainty_passed:
            return OutcomeEvaluationResult(
                is_eligible=False,
                status_code="STATISTICAL_UNCERTAINTY" if "STATISTICAL" in str(uncertainty_reason) else "UNCERTAINTY_NOT_ESTABLISHED",
                p_tp=round(p_tp, 4), p_sl=round(p_sl, 4), p_to=round(p_to, 4),
                probability_sum=round(prob_sum, 4),
                k_tp_r=round(k_tp_r, 4), k_sl_r=round(k_sl_r, 4),
                friction_bps=round(friction_bps, 2), friction_r=round(friction_r, 4),
                expected_timeout_r=round(expected_timeout_r, 4),
                expected_gross_r=round(ev_gross, 4), expected_net_r=round(ev_net, 4),
                ci_95_lower_r=round(ci_lower, 4) if ci_lower is not None else None,
                ci_95_upper_r=round(ci_upper, 4) if ci_upper is not None else None,
                assumed_cost_scenario=assumed_cost_scenario,
                rejection_reason=uncertainty_reason,
                audit_notes={"ci_lower": round(ci_lower, 4) if ci_lower is not None else None}
            )

        return OutcomeEvaluationResult(
            is_eligible=True,
            status_code="ELIGIBLE",
            p_tp=round(p_tp, 4), p_sl=round(p_sl, 4), p_to=round(p_to, 4),
            probability_sum=round(prob_sum, 4),
            k_tp_r=round(k_tp_r, 4), k_sl_r=round(k_sl_r, 4),
            friction_bps=round(friction_bps, 2), friction_r=round(friction_r, 4),
            expected_timeout_r=round(expected_timeout_r, 4),
            expected_gross_r=round(ev_gross, 4), expected_net_r=round(ev_net, 4),
            ci_95_lower_r=round(ci_lower, 4), ci_95_upper_r=round(ci_upper, 4),
            assumed_cost_scenario=assumed_cost_scenario,
            rejection_reason=None,
            audit_notes={"status": "POSITIVE_EDGE_VERIFIED"}
        )
