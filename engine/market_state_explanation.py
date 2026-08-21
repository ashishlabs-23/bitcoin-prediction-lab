"""
engine/market_state_explanation.py — Deterministic Market-State Explanation Engine
==================================================================================
Generates transparent, rule-based explanations for multi-layer market states:
- Clarifies why the 24h risk envelope is wide or narrow using deterministic causal associations
- Uses conservative, empirical language ("associated with") rather than claiming certainty
- Zero LLM dependency; fully deterministic template expansion
"""

import os
import sys
from typing import Dict, List, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def generate_market_state_narrative(
    short_term_direction: str,
    microstructure_intensity: str,
    volatility_regime: str,
    derivatives_asymmetry: str,
    long_term_risk_state: str,
    uncertainty_level: float
) -> Dict[str, str]:
    # Range dispersion explanation
    if volatility_regime in ["VOL_EXPANDING", "PEAK_VOLATILITY"] or uncertainty_level > 1.2:
        range_rationale = (
            "24h risk envelope is expanded, associated with elevated realized volatility "
            "and active order-flow dispersion across intermediate timescales."
        )
    elif volatility_regime == "VOL_COMPRESSION" and uncertainty_level <= 0.8:
        range_rationale = (
            "24h risk envelope is compressed, associated with subdued volatility term structure "
            "and balanced two-sided market liquidity."
        )
    else:
        range_rationale = (
            "24h risk envelope is within historical normal parameters, associated with "
            "steady structural variance and balanced market positioning."
        )

    # Multi-horizon synthesis narrative
    narrative_summary = (
        f"BTCUSD displays {short_term_direction} short-term market pressure "
        f"({microstructure_intensity}), within a {volatility_regime.lower().replace('_', ' ')} intermediate volatility state "
        f"and {derivatives_asymmetry.lower().replace('_', ' ')} derivatives positioning. "
        f"The 24h production envelope reflects a {long_term_risk_state.lower().replace('_', ' ')} posture."
    )

    return {
        "summary": narrative_summary,
        "range_rationale": range_rationale,
        "confidence_level": "HIGH" if uncertainty_level < 0.8 else ("MODERATE" if uncertainty_level < 1.5 else "LOW")
    }
