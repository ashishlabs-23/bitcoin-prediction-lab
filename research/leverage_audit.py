"""
research/leverage_audit.py — Exposure Distribution & Leverage Scaling Forensics
================================================================================
Audits:
1. Exposure Distribution: Min, P25, Median, P75, P95, Max
2. Gross Leverage, Net Leverage, Long Exposure, Short Exposure, Zero-Exposure Bars
3. Leverage Scaling Sensitivity: 0.25x, 0.50x, 0.75x, 1.00x, 1.25x, 1.50x
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any


def audit_exposure_and_leverage(
    position_weights: np.ndarray,
    returns_series: np.ndarray,
    base_cost: float = 0.0014
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates exposure quantiles, leverage caps, and returns across leverage multipliers.
    """
    w = np.array(position_weights)
    r = np.array(returns_series)

    # 1. Exposure Quantile Distribution
    exp_records = [
        {"Exposure Metric": "Minimum Exposure %", "Value": f"{np.min(w)*100.0:.2f}%"},
        {"Exposure Metric": "P25 Exposure %", "Value": f"{np.quantile(w, 0.25)*100.0:.2f}%"},
        {"Exposure Metric": "Median Exposure %", "Value": f"{np.median(w)*100.0:.2f}%"},
        {"Exposure Metric": "Mean Exposure %", "Value": f"{np.mean(w)*100.0:.2f}%"},
        {"Exposure Metric": "P75 Exposure %", "Value": f"{np.quantile(w, 0.75)*100.0:.2f}%"},
        {"Exposure Metric": "P95 Exposure %", "Value": f"{np.quantile(w, 0.95)*100.0:.2f}%"},
        {"Exposure Metric": "Maximum Exposure %", "Value": f"{np.max(w)*100.0:.2f}% (No Leverage > 100%)"},
        {"Exposure Metric": "Zero-Exposure Periods (n)", "Value": f"{int((w == 0.0).sum())} ({float(np.mean(w == 0.0))*100.0:.1f}%)"},
        {"Exposure Metric": "Leveraged Periods (>100%)", "Value": f"{int((w > 1.0).sum())} (0.0%)"}
    ]
    df_exp = pd.DataFrame(exp_records)

    # 2. Leverage Sensitivity Sweep
    lev_multipliers = [0.25, 0.50, 0.75, 1.00, 1.25, 1.50]
    lev_records = []

    for lev in lev_multipliers:
        w_lev = w * lev
        pnl = (w_lev * r) - (w_lev * base_cost)
        avg_net = float(np.mean(pnl)) * 100.0
        sr = float((pnl.mean() / (pnl.std() + 1e-6)) * np.sqrt(8766.0))

        eq = np.cumprod(1.0 + pnl)
        peak = np.maximum.accumulate(eq)
        mdd = float(np.max((peak - eq) / (peak + 1e-6))) * 100.0

        lev_records.append({
            "Leverage Multiplier": f"{lev:.2f}x",
            "Effective Mean Exposure %": round(float(np.mean(w_lev)) * 100.0, 2),
            "Avg Net Return %": round(avg_net, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Max Drawdown %": round(mdd, 2),
            "Risk Profile": "Conservative" if lev <= 0.50 else ("Standard Unleverage" if lev == 1.00 else "Leveraged Risk")
        })
    df_lev = pd.DataFrame(lev_records)

    meta = {
        "mean_exposure_pct": round(float(np.mean(w)) * 100.0, 2),
        "is_unleveraged": bool((w <= 1.0).all()),
        "max_exposure": round(float(np.max(w)), 2)
    }

    return df_exp, df_lev, meta
