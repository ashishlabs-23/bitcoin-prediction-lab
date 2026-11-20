"""
research/risk_envelope.py — Risk Envelope & Probabilistic Decision Table Engine
================================================================================
Generates:
1. Expected Upside Excursion, Expected Downside Excursion
2. Tail Upside (P90), Tail Downside (P90), Range Width
3. Probabilistic Decision Table categorizing:
   - Range Quality: HIGH / MODERATE / LOW
   - Risk Quality: BALANCED / SKEWED ADVERSE / SKEWED FAVORABLE
   - Tradeability: FAVORABLE / MARGINAL / ABSTAIN
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any


def generate_risk_envelope_and_decision_table(
    df_mfe_forecasts: pd.DataFrame,
    base_btc_price: float = 100000.0
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Constructs the BTCognitive Risk Envelope and Probabilistic Decision Table for UI integration.
    """
    has_mae = "p50_mae" in df_mfe_forecasts.columns and "p90_mae" in df_mfe_forecasts.columns
    mfe_p50 = float(np.mean(df_mfe_forecasts["p50_mfe"])) * 100.0
    mfe_p90 = float(np.mean(df_mfe_forecasts["p90_mfe"])) * 100.0
    mae_p50 = float(np.mean(df_mfe_forecasts["p50_mae"])) * 100.0 if has_mae else None
    mae_p90 = float(np.mean(df_mfe_forecasts["p90_mae"])) * 100.0 if has_mae else None
    range_w = (mfe_p90 + mae_p90) if has_mae else None
    unc_score = float(np.mean(df_mfe_forecasts["uncertainty_score"])) if "uncertainty_score" in df_mfe_forecasts.columns else 1.0

    envelope_records = [
        {"Risk Metric": "Expected Median Upside (MFE P50)", "Magnitude %": f"+{mfe_p50:.2f}%", "BTCUSD Projected Level": f"${base_btc_price * (1 + mfe_p50/100):,.0f}"},
        {"Risk Metric": "Expected Median Downside (MAE P50)", "Magnitude %": f"-{mae_p50:.2f}%" if mae_p50 is not None else "DATA_UNAVAILABLE", "BTCUSD Projected Level": f"${base_btc_price * (1 - mae_p50/100):,.0f}" if mae_p50 is not None else "—"},
        {"Risk Metric": "Tail Favorable Upside (MFE P90)", "Magnitude %": f"+{mfe_p90:.2f}%", "BTCUSD Projected Level": f"${base_btc_price * (1 + mfe_p90/100):,.0f}"},
        {"Risk Metric": "Tail Adverse Downside (MAE P90)", "Magnitude %": f"-{mae_p90:.2f}%" if mae_p90 is not None else "DATA_UNAVAILABLE", "BTCUSD Projected Level": f"${base_btc_price * (1 - mae_p90/100):,.0f}" if mae_p90 is not None else "—"},
        {"Risk Metric": "80% Risk Range Width", "Magnitude %": f"{range_w:.2f}%" if range_w is not None else "DATA_UNAVAILABLE", "BTCUSD Projected Level": f"${base_btc_price * (range_w/100):,.0f} Spread" if range_w is not None else "—"},
        {"Risk Metric": "Forecast Uncertainty Ratio", "Magnitude %": f"{unc_score:.2f}x", "BTCUSD Projected Level": "Dispersion / Move Ratio"}
    ]
    df_envelope = pd.DataFrame(envelope_records)

    # Probabilistic Decision Table
    decision_records = [
        {
            "Forecast Attribute": "1. Range Confidence",
            "State / Value": "UNAVAILABLE (C2 Conformal Undercoverage 84.89% - Research Only)",
            "Interpretation": "Holdout coverage (84.89%) failed the 90% nominal calibration hurdle. Conformal bounds are research-only."
        },
        {
            "Forecast Attribute": "2. Expected Range",
            "State / Value": f"[${base_btc_price*(1 - mae_p90/100):,.0f}, ${base_btc_price*(1 + mfe_p90/100):,.0f}]" if mae_p90 is not None else "DATA_UNAVAILABLE",
            "Interpretation": "Empirical envelope unavailable without verified bidirectional excursion observations."
        },
        {
            "Forecast Attribute": "3. Risk Symmetry",
            "State / Value": "UNVERIFIED SYMMETRY",
            "Interpretation": "Synthetic multipliers removed; asymmetric excursion requires empirical MAE."
        },
        {
            "Forecast Attribute": "4. Tradeability Recommendation",
            "State / Value": "ABSTAIN / RESEARCH_ONLY",
            "Interpretation": "Live trading permanently disabled; market risk intelligence posture only."
        }
    ]
    df_decision = pd.DataFrame(decision_records)

    meta = {
        "mfe_p50_pct": round(mfe_p50, 2),
        "mae_p50_pct": round(mae_p50, 2) if mae_p50 is not None else None,
        "range_width_pct": round(range_w, 2) if range_w is not None else None,
        "decision_verdict": "ABSTAIN (Research only; trading permanently disabled)"
    }

    return df_envelope, df_decision, meta
