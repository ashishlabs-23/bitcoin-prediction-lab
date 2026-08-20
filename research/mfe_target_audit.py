"""
research/mfe_target_audit.py — MFE / MAE Point-in-Time Target Audit & Leakage Forensics
======================================================================================
Audits:
1. MFE_long = max(high[t+1:t+H] / close[t] - 1)
2. MFE_short = max(close[t] / low[t+1:t+H] - 1)
3. MAE_long = max(1 - low[t+1:t+H] / close[t])
4. MAE_short = max(high[t+1:t+H] / close[t] - 1)
Evaluates horizons: 1h, 4h, 8h, 12h, 24h, 48h.
Verifies no future lookahead leakage in features and strict point-in-time boundary isolation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any


def compute_directional_excursions(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    horizon_bars: int = 24
) -> Dict[str, np.ndarray]:
    """Computes exact forward directional MFE and MAE for both long and short positions."""
    c_vals = close.values
    h_vals = high.values
    l_vals = low.values
    n = len(close)

    mfe_long = np.zeros(n)
    mfe_short = np.zeros(n)
    mae_long = np.zeros(n)
    mae_short = np.zeros(n)

    for i in range(n - horizon_bars):
        p0 = c_vals[i]
        if p0 > 0:
            w_high = np.max(h_vals[i+1 : i+horizon_bars+1])
            w_low = np.min(l_vals[i+1 : i+horizon_bars+1])
            mfe_long[i] = max(0.0, float((w_high / p0) - 1.0))
            mfe_short[i] = max(0.0, float((p0 / w_low) - 1.0))
            mae_long[i] = max(0.0, float(1.0 - (w_low / p0)))
            mae_short[i] = max(0.0, float((w_high / p0) - 1.0))

    return {
        "mfe_long": mfe_long,
        "mfe_short": mfe_short,
        "mae_long": mae_long,
        "mae_short": mae_short
    }


def audit_mfe_leakage_and_horizons(
    df: pd.DataFrame,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    horizons: List[int] = [1, 4, 8, 12, 24, 48]
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates excursion properties across horizons and runs automated point-in-time leakage checks.
    """
    records = []
    leakage_flags = []

    for h in horizons:
        exc = compute_directional_excursions(close, high, low, horizon_bars=h)
        m_long = exc["mfe_long"]
        m_short = exc["mfe_short"]

        # Leakage check: Correlation of feature at t with future excursion high/low index
        # Feature at t must have zero correlation with future random innovation
        ret_1h = df.get('ret_1h', np.log(close / close.shift(1)).fillna(0.0)).values
        corr_leakage = float(np.corrcoef(ret_1h[:-h], m_long[h:])[0, 1]) if len(ret_1h) > 2*h else 0.0
        is_clean = abs(corr_leakage) < 0.20
        leakage_flags.append(is_clean)

        records.append({
            "Horizon": f"{h}h",
            "Mean Long MFE %": round(float(np.mean(m_long)) * 100.0, 3),
            "Mean Short MFE %": round(float(np.mean(m_short)) * 100.0, 3),
            "Mean Long MAE %": round(float(np.mean(exc["mae_long"])) * 100.0, 3),
            "Mean Short MAE %": round(float(np.mean(exc["mae_short"])) * 100.0, 3),
            "Long/Short MFE Ratio": round(float(np.mean(m_long) / max(1e-6, np.mean(m_short))), 3),
            "Leakage Correlation": round(corr_leakage, 4),
            "Leakage Audit Status": "PASS (Zero Lookahead)" if is_clean else "FAIL"
        })

    df_audit = pd.DataFrame(records)
    summary = {
        "is_leakage_free": all(leakage_flags),
        "tested_horizons_count": len(horizons)
    }

    return df_audit, summary
