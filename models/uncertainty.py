"""
models/uncertainty.py -- 4-Factor Uncertainty Decomposition Engine

Decomposes signal confidence into four distinct, interpretable uncertainty layers:
  1. Data Reliability (U_data): Freshness, completeness, and non-null status of live feature inputs.
  2. Regime Certainty (U_regime): 1 - Normalized Entropy across the continuous regime probability vector.
  3. Model Agreement (U_model): Consensus agreement (low variance) across RF, XGBoost, and LogReg.
  4. Volatility Stress (U_vol): Percentile rank of 24h realized volatility (1.0 = calm, 0.0 = extreme spike).

Exposes compute_decomposed_uncertainty() and format_uncertainty_narrative().
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple


def compute_data_reliability(df_row: pd.Series) -> float:
    """
    Computes Data Reliability score in [0.0, 1.0].
    1.0 = all expected features present and non-null.
    Reduces proportionally for missing features or NaN values.
    """
    expected_cols = [
        'close', 'rsi_14', 'macd', 'sma_ratio_50',
        'realized_vol_24h', 'atr_14', 'funding_rate', 'oi_pct_change_24h'
    ]
    present_cols = [c for c in expected_cols if c in df_row.index]
    if not present_cols:
        return 0.5

    non_null_count = sum(1 for c in present_cols if pd.notna(df_row[c]) and math.isfinite(float(df_row[c])))
    return float(non_null_count / len(expected_cols))


def compute_regime_certainty(regime_probs: Dict[str, float]) -> float:
    """
    Computes Regime Certainty score in [0.0, 1.0] using 1 - Normalized Shannon Entropy.
    1.0 = 100% single regime certainty.
    0.0 = max entropy (flat 20% across all 5 regimes).
    """
    probs = np.array(list(regime_probs.values()), dtype=float)
    probs = np.clip(probs, 1e-9, 1.0)
    probs = probs / np.sum(probs)  # normalize

    n_regimes = len(probs)
    if n_regimes <= 1:
        return 1.0

    entropy = -np.sum(probs * np.log2(probs))
    max_entropy = np.log2(n_regimes)

    normalized_entropy = float(entropy / max_entropy)
    return float(np.clip(1.0 - normalized_entropy, 0.0, 1.0))


def compute_model_agreement(model_probs: Dict[str, float]) -> float:
    """
    Computes Model Agreement score in [0.0, 1.0].
    1.0 = zero variance among model predictions (full consensus).
    0.0 = extreme disagreement (e.g. 0.90 vs 0.10).
    """
    p_vals = list(model_probs.values())
    if len(p_vals) <= 1:
        return 1.0

    std_dev = float(np.std(p_vals))
    # Max possible std_dev for probabilities in [0, 1] is 0.5 (e.g., [0.0, 1.0])
    agreement = 1.0 - (2.0 * std_dev)
    return float(np.clip(agreement, 0.0, 1.0))


def compute_volatility_stress(realized_vol_24h: float, historical_vol_series: Optional[pd.Series] = None) -> float:
    """
    Computes Volatility Stress score in [0.0, 1.0].
    1.0 = calm market (low volatility percentile).
    0.0 = extreme volatility spike (99th percentile+).
    """
    if math.isnan(realized_vol_24h) or not math.isfinite(realized_vol_24h):
        return 0.5

    if historical_vol_series is not None and len(historical_vol_series) > 10:
        vol_clean = historical_vol_series.dropna()
        percentile = float((vol_clean <= realized_vol_24h).mean())
    else:
        # Static heuristic fallback for BTC 24h realized vol (typical range 0.005 to 0.05)
        percentile = float(np.clip((realized_vol_24h - 0.005) / 0.045, 0.0, 1.0))

    return float(np.clip(1.0 - percentile, 0.0, 1.0))


def compute_decomposed_uncertainty(
    df_row: pd.Series,
    regime_probs: Dict[str, float],
    model_probs: Dict[str, float],
    historical_vol_series: Optional[pd.Series] = None,
) -> Dict[str, float]:
    """
    Computes all 4 uncertainty scores and their harmonic mean quality score.

    Returns dict with keys:
      - data_reliability
      - regime_certainty
      - model_agreement
      - volatility_stress
      - composite_quality_score (harmonic mean)
    """
    u_data   = compute_data_reliability(df_row)
    u_regime = compute_regime_certainty(regime_probs)
    u_model  = compute_model_agreement(model_probs)

    rvol = float(df_row.get('realized_vol_24h', 0.01))
    u_vol    = compute_volatility_stress(rvol, historical_vol_series)

    scores = [u_data, u_regime, u_model, u_vol]
    scores_clamped = [max(1e-4, s) for s in scores]

    # Harmonic mean emphasizes the lowest score (weakest link principle)
    harmonic_mean = float(len(scores_clamped) / sum(1.0 / s for s in scores_clamped))

    return {
        'data_reliability':      round(u_data, 4),
        'regime_certainty':      round(u_regime, 4),
        'model_agreement':       round(u_model, 4),
        'volatility_stress':     round(u_vol, 4),
        'composite_quality_score': round(harmonic_mean, 4),
    }


def format_uncertainty_narrative(uncertainty_dict: Dict[str, float]) -> str:
    """Returns a clean human-readable narrative summarizing the 4-factor breakdown."""
    ud = uncertainty_dict['data_reliability']
    ur = uncertainty_dict['regime_certainty']
    um = uncertainty_dict['model_agreement']
    uv = uncertainty_dict['volatility_stress']
    qc = uncertainty_dict['composite_quality_score']

    weakest = min(
        ('Data Reliability', ud),
        ('Regime Certainty', ur),
        ('Model Agreement', um),
        ('Volatility Stress', uv),
        key=lambda x: x[1]
    )

    if qc >= 0.75:
        verdict = "High Confidence"
    elif qc >= 0.50:
        verdict = "Moderate Confidence"
    else:
        verdict = "Low Confidence (High Uncertainty)"

    return (
        f"Verdict: {verdict} (Overall Score: {int(qc*100)}/100). "
        f"Data: {int(ud*100)}%, Regime Certainty: {int(ur*100)}%, "
        f"Model Consensus: {int(um*100)}%, Market Vol Calmness: {int(uv*100)}%. "
        f"Primary risk factor: {weakest[0]} ({int(weakest[1]*100)}%)."
    )


if __name__ == "__main__":
    print("Testing models/uncertainty.py...")

    dummy_row = pd.Series({
        'close': 116000.0, 'rsi_14': 58.2, 'macd': 120.0,
        'sma_ratio_50': 0.03, 'realized_vol_24h': 0.015,
        'atr_14': 1400.0, 'funding_rate': 0.0001, 'oi_pct_change_24h': 0.01
    })

    reg_probs = {'TRENDING_BULL': 0.70, 'BREAKOUT': 0.15, 'RANGING': 0.10, 'HIGH_VOLATILITY': 0.03, 'TRENDING_BEAR': 0.02}
    mod_probs = {'RandomForest': 0.72, 'XGBoost': 0.68, 'LogisticRegression': 0.70}

    unc = compute_decomposed_uncertainty(dummy_row, reg_probs, mod_probs)
    print("Uncertainty breakdown:", unc)
    narrative = format_uncertainty_narrative(unc)
    print("Narrative:", narrative)

    assert 0.0 <= unc['data_reliability'] <= 1.0
    assert 0.0 <= unc['regime_certainty'] <= 1.0
    assert 0.0 <= unc['model_agreement'] <= 1.0
    assert 0.0 <= unc['volatility_stress'] <= 1.0
    assert 0.0 <= unc['composite_quality_score'] <= 1.0

    print("PASS: models/uncertainty.py smoke test passed.")
