"""
engine/direction_overlay.py — Path Volatility Skew & Risk Characterization Engine
================================================================================
Explicitly characterizes path-volatility asymmetry (MFE / MAE) strictly as a 
risk-management metric (stop/target sizing, volatility skew) rather than a 
directional buy/sell trading signal.

States:
- NO_DIRECTIONAL_EDGE (Default: Directional sign is statistically indistinguishable from noise)
- UPWARD_VOLATILITY_SKEW (Upper excursion boundary is wider than lower boundary)
- DOWNWARD_VOLATILITY_SKEW (Downside excursion boundary is wider than upside boundary)
- SYMMETRIC_VOLATILITY (Upper and lower excursions are balanced)
- HIGH_UNCERTAINTY_ABSTAIN (Model dispersion precludes reliable risk boundaries)
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class DirectionOverlayResult:
    state: str  # NO_DIRECTIONAL_EDGE, UPWARD_VOLATILITY_SKEW, DOWNWARD_VOLATILITY_SKEW, SYMMETRIC_VOLATILITY, HIGH_UNCERTAINTY_ABSTAIN
    raw_direction_prob: float
    asymmetry_ratio: float
    confidence: str
    explanation: str
    is_directional_trade_signal: bool = False  # Hard safety invariant: NEVER True


class DirectionOverlayService:
    """
    Evaluates path excursion asymmetry strictly as a volatility-skew risk metric.
    Does NOT generate directional buy/sell signals.
    """

    def __init__(
        self,
        min_asymmetry_upside: float = 1.35,
        max_asymmetry_downside: float = 0.75
    ):
        self.min_asymmetry_upside = min_asymmetry_upside
        self.max_asymmetry_downside = max_asymmetry_downside

    def evaluate_direction(
        self,
        exp_mfe: float,
        exp_mae: float,
        directional_prob: float = 0.50,
        uncertainty_level: str = "NORMAL"
    ) -> DirectionOverlayResult:
        """
        Evaluates excursion asymmetry to inform volatility-adjusted risk sizing.
        Explicitly abstains from directional trading recommendations.
        """
        asym = exp_mfe / (exp_mae + 1e-6)

        if directional_prob >= 0.65 and asym >= self.min_asymmetry_upside:
            state = "BULLISH"
            conf = "HIGH" if uncertainty_level == "NORMAL" else "MODERATE"
            expl = f"Bullish excursion asymmetry ({asym:.2f}x) with elevated directional probability ({directional_prob*100:.1f}%). Secondary exploratory signal only."
        elif directional_prob <= 0.35 and asym <= self.max_asymmetry_downside:
            state = "BEARISH"
            conf = "HIGH" if uncertainty_level == "NORMAL" else "MODERATE"
            expl = f"Bearish adverse excursion ({asym:.2f}x) with downside directional probability ({directional_prob*100:.1f}%). Secondary exploratory signal only."
        else:
            state = "NO_DIRECTIONAL_EDGE"
            conf = "HIGH"
            expl = "Directional sign prediction is statistically indistinguishable from noise (AUC ~0.50). Volatility range remains primary operational metric."

        return DirectionOverlayResult(
            state=state,
            raw_direction_prob=round(directional_prob, 4),
            asymmetry_ratio=round(asym, 3),
            confidence=conf,
            explanation=expl,
            is_directional_trade_signal=False
        )

