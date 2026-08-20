"""
research/funding_horizon.py — Funding Rate Holding Horizon Decomposition Engine
================================================================================
Evaluates the temporal persistence and optimal holding horizon of the funding rate signal:
Horizons: 1h, 4h, 8h, 12h, 24h, 48h
Measures forward return, MFE, MAE, win rate, and net expectancy after 14 bps friction.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any


def evaluate_funding_holding_horizons(
    df: pd.DataFrame,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    funding_z: pd.Series,
    horizons: List[int] = [1, 4, 8, 12, 24, 48],
    threshold_sigma: float = 2.0
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates trading expectancy across forward holding horizons following funding shocks.
    """
    close_aligned = close.loc[df.index]
    high_aligned = high.loc[df.index]
    low_aligned = low.loc[df.index]
    base_cost = 0.0014  # 14 bps

    active_mask = (np.abs(funding_z) > threshold_sigma)
    active_indices = df.index[active_mask]
    n_active = len(active_indices)

    records = []

    for h in horizons:
        fwd_ret = np.log(close_aligned.shift(-h) / close_aligned).fillna(0.0)
        rets_active = fwd_ret.loc[active_indices].values
        fz_active = funding_z.loc[active_indices].values

        signs = -np.sign(fz_active)
        gross_rets = signs * rets_active
        net_rets = gross_rets - base_cost

        win_rate = float(np.mean(net_rets > 0)) * 100.0 if n_active > 0 else 0.0
        avg_gross = float(np.mean(gross_rets)) * 100.0 if n_active > 0 else 0.0
        avg_net = float(np.mean(net_rets)) * 100.0 if n_active > 0 else 0.0
        sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(max(1, n_active * (8766.0 / max(1, h * 365.25))))) if n_active > 0 else 0.0

        records.append({
            "Holding Horizon (hours)": f"{h}h",
            "Active Sample Count (n)": n_active,
            "Directional Win Rate %": round(win_rate, 2),
            "Avg Gross Return %": round(avg_gross, 4),
            "Avg Net Return %": round(avg_net, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Net Expectancy ($10 base)": round(avg_net * 0.10, 4)
        })

    df_h = pd.DataFrame(records)
    best_h = df_h.loc[df_h["Cost-Adjusted Sharpe"].idxmax()]["Holding Horizon (hours)"] if len(df_h) > 0 else "24h"

    return df_h, {"optimal_horizon": best_h}
