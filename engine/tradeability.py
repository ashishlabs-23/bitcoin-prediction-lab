"""
engine/tradeability.py — Tradeability Research Score Engine (Non-Execution Informational Layer)
==============================================================================================
Computes informational tradeability scores:
    Score = E[MFE] - 1.5 * E[MAE] - Friction
Categorizes:
    - HIGH: Substantial favorable excursion potential exceeding adverse risk + friction
    - MEDIUM: Marginal opportunity; elevated risk/reward sensitivity
    - LOW: Adverse excursion and costs exceed expected favorable move (ABSTAIN)
IMPORTANT:
This score is strictly informational and DOES NOT execute live trades.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class TradeabilityResult:
    score_value: float
    category: str  # HIGH, MEDIUM, LOW
    label: str  # TRADEABILITY RESEARCH SCORE (NON-EXECUTION)
    reasoning: str
    is_actionable: bool = False  # Always False for safety


class TradeabilityService:
    """
    Evaluates market tradeability for risk intelligence without live execution.
    """

    def __init__(self, transaction_friction_pct: float = 0.0016):
        self.friction = transaction_friction_pct

    def compute_tradeability(
        self,
        exp_mfe: float,
        exp_mae: float,
        uncertainty_level: str = "HIGH"
    ) -> TradeabilityResult:
        """
        Calculates utility-weighted tradeability score.
        """
        raw_utility = exp_mfe - (1.5 * exp_mae) - self.friction

        if uncertainty_level == "LOW_CONFIDENCE" or raw_utility < -0.0050:
            category = "LOW"
            reason = "Adverse excursion risk and transaction costs heavily exceed expected favorable move."
        elif raw_utility < 0.0020:
            category = "MEDIUM"
            reason = "Marginal tradeability. Excursion symmetry does not provide a robust edge after costs."
        else:
            category = "HIGH"
            reason = "Favorable excursion exceeds downside bounds and friction; positive theoretical edge."

        return TradeabilityResult(
            score_value=round(raw_utility * 100.0, 4),
            category=category,
            label="TRADEABILITY RESEARCH SCORE (NON-EXECUTION)",
            reasoning=reason,
            is_actionable=False
        )
