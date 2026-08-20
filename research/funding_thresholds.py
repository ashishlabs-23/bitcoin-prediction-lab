"""
research/funding_thresholds.py — Funding Rate Threshold Ladder Forensics
========================================================================
Sweeps and evaluates threshold sensitivities:
1.0 sigma, 1.5 sigma, 2.0 sigma, 2.5 sigma, 3.0 sigma
Records trade frequency, win rate, gross return, net expectancy, and Sharpe ratio.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any


def evaluate_funding_threshold_ladder(
    df: pd.DataFrame,
    close: pd.Series,
    funding_z: pd.Series,
    thresholds: List[float] = [1.0, 1.5, 2.0, 2.5, 3.0],
    horizon_bars: int = 24
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates trading expectancy across standard deviation thresholds on funding rate Z-scores.
    """
    close_aligned = close.loc[df.index]
    fwd_ret = np.log(close_aligned.shift(-horizon_bars) / close_aligned).fillna(0.0)
    base_cost = 0.0014  # 14 bps

    records = []

    for th in thresholds:
        active_mask = (np.abs(funding_z) > th)
        n_bars = int(active_mask.sum())

        if n_bars > 0:
            rets_active = fwd_ret[active_mask].values
            fz_active = funding_z[active_mask].values
            # Mean-reversion sign: opposite of funding Z
            signs = -np.sign(fz_active)
            gross_rets = signs * rets_active
            net_rets = gross_rets - base_cost

            win_rate = float(np.mean(net_rets > 0)) * 100.0
            avg_gross = float(np.mean(gross_rets)) * 100.0
            avg_net = float(np.mean(net_rets)) * 100.0
            gains = np.sum(gross_rets[gross_rets > 0]) if (gross_rets > 0).any() else 1e-6
            losses = np.abs(np.sum(gross_rets[gross_rets < 0])) if (gross_rets < 0).any() else 1e-6
            pf = float(gains / max(1e-6, losses))

            sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(max(1, n_bars * 12)))
        else:
            win_rate, avg_gross, avg_net, pf, sr = 0.0, 0.0, 0.0, 0.0, 0.0

        records.append({
            "Threshold Z-Score (sigma)": th,
            "Active Sample Count (n)": n_bars,
            "Market Coverage %": round((n_bars / len(df)) * 100.0, 2),
            "Win Rate %": round(win_rate, 2),
            "Avg Gross Return %": round(avg_gross, 4),
            "Avg Net Return %": round(avg_net, 4),
            "Profit Factor": round(pf, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Net Expectancy ($10 base)": round(avg_net * 0.10, 4)
        })

    df_th = pd.DataFrame(records)
    best_th = df_th.loc[df_th["Cost-Adjusted Sharpe"].idxmax()]["Threshold Z-Score (sigma)"] if len(df_th) > 0 else 2.0

    return df_th, {"best_training_threshold": float(best_th)}
