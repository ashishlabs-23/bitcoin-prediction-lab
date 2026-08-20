"""
engine/direction_overlay.py — Secondary Directional Evidence & Overlay Engine
=============================================================================
Explicitly isolates directional positioning as a secondary, conditional layer.
1. Evaluates excursion asymmetry (MFE / MAE ratio)
2. Checks directional model probability & uncertainty
3. Returns:
   - NO_DIRECTIONAL_EDGE (Default when signal is noise-dominated)
   - BULLISH / BEARISH (Only under extreme validated asymmetry)
   - NEUTRAL
   - LOW_CONFIDENCE
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class DirectionOverlayResult:
    state: str  # NO_DIRECTIONAL_EDGE, BULLISH, BEARISH, NEUTRAL, LOW_CONFIDENCE
    raw_direction_prob: float
    asymmetry_ratio: float
    confidence: str
    explanation: str


class DirectionOverlayService:
    """
    Evaluates secondary directional evidence without forcing binary BUY/SELL trades.
    """

    def __init__(
        self,
        min_asymmetry_bullish: float = 1.40,
        max_asymmetry_bearish: float = 0.70,
        prob_threshold_high: float = 0.65,
        prob_threshold_low: float = 0.35
    ):
        self.min_asymmetry_bullish = min_asymmetry_bullish
        self.max_asymmetry_bearish = max_asymmetry_bearish
        self.prob_threshold_high = prob_threshold_high
        self.prob_threshold_low = prob_threshold_low

    def evaluate_direction(
        self,
        exp_mfe: float,
        exp_mae: float,
        directional_prob: float = 0.50,
        uncertainty_level: str = "HIGH"
    ) -> DirectionOverlayResult:
        """
        Evaluates whether directional positioning is justified or should abstain as NO_DIRECTIONAL_EDGE.
        """
        asym = exp_mfe / (exp_mae + 1e-6)

        if uncertainty_level == "LOW_CONFIDENCE":
            return DirectionOverlayResult(
                state="LOW_CONFIDENCE",
                raw_direction_prob=round(directional_prob, 4),
                asymmetry_ratio=round(asym, 3),
                confidence="LOW",
                explanation="High forecast uncertainty precludes reliable directional edge."
            )

        if asym >= self.min_asymmetry_bullish and directional_prob >= self.prob_threshold_high:
            state = "BULLISH"
            conf = "MODERATE"
            expl = f"Favorable excursion exceeds downside (asymmetry {asym:.2f}x) with supportive directional probability."
        elif asym <= self.max_asymmetry_bearish and directional_prob <= self.prob_threshold_low:
            state = "BEARISH"
            conf = "MODERATE"
            expl = f"Adverse excursion dominates favorable upside (asymmetry {asym:.2f}x) with bearish probability bias."
        else:
            state = "NO_DIRECTIONAL_EDGE"
            conf = "HIGH"
            expl = "Directional sign prediction is statistically indistinguishable from noise. Range forecast remains fully operational."

        return DirectionOverlayResult(
            state=state,
            raw_direction_prob=round(directional_prob, 4),
            asymmetry_ratio=round(asym, 3),
            confidence=conf,
            explanation=expl
        )
