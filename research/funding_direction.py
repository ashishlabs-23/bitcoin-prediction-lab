"""
research/funding_direction.py — Directional Asymmetry & Mean-Reversion Decomposition Engine
===========================================================================================
Separates and independently evaluates:
1. Extreme Positive Funding Spikes (Crowded Longs / Short Opportunity)
2. Extreme Negative Funding Spikes (Crowded Shorts / Long Opportunity)
Determines whether the market response is symmetric mean-reversion, momentum, or asymmetric.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any


def evaluate_funding_directional_asymmetry(
    df: pd.DataFrame,
    close: pd.Series,
    funding_z: pd.Series,
    horizon_bars: int = 24,
    threshold_sigma: float = 2.0
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates forward 24h returns following positive vs negative funding shocks.
    """
    close_aligned = close.loc[df.index]
    fwd_ret = np.log(close_aligned.shift(-horizon_bars) / close_aligned).fillna(0.0)
    base_cost = 0.0014  # 14 bps

    pos_mask = (funding_z > threshold_sigma)
    neg_mask = (funding_z < -threshold_sigma)

    pos_rets = fwd_ret[pos_mask].values
    neg_rets = fwd_ret[neg_mask].values

    # Mean-reversion assumption:
    # Pos funding (crowded long) -> SHORT (trade sign = -1) -> Trade return = -1 * fwd_ret
    # Neg funding (crowded short) -> LONG (trade sign = +1) -> Trade return = +1 * fwd_ret
    short_trade_rets = -1.0 * pos_rets - base_cost
    long_trade_rets = 1.0 * neg_rets - base_cost

    records = []

    # 1. Positive Funding (Short Side)
    n_pos = len(pos_rets)
    if n_pos > 0:
        win_rate_pos = float(np.mean(short_trade_rets > 0)) * 100.0
        gross_pos = float(np.mean(-1.0 * pos_rets)) * 100.0
        net_pos = float(np.mean(short_trade_rets)) * 100.0
        sr_pos = float((short_trade_rets.mean() / (short_trade_rets.std() + 1e-6)) * np.sqrt(max(1, n_pos * 12)))
        pf_pos = float(np.sum(short_trade_rets[short_trade_rets > 0]) / max(1e-6, np.abs(np.sum(short_trade_rets[short_trade_rets < 0]))))
    else:
        win_rate_pos, gross_pos, net_pos, sr_pos, pf_pos = 0.0, 0.0, 0.0, 0.0, 0.0

    records.append({
        "Funding Shock Regime": f"Positive Funding (> +{threshold_sigma} sigma) -> SHORT",
        "Sample Count (n)": n_pos,
        "Mean Asset Return %": round(float(np.mean(pos_rets)) * 100.0, 4) if n_pos > 0 else 0.0,
        "Mean Trade Gross Return %": round(gross_pos, 4),
        "Mean Trade Net Return %": round(net_pos, 4),
        "Hit Rate %": round(win_rate_pos, 2),
        "Profit Factor": round(pf_pos, 4),
        "Cost-Adjusted Sharpe": round(sr_pos, 4),
        "Net Expectancy ($10 base)": round(net_pos * 0.10, 4),
        "Mechanics": "Mean Reversion" if net_pos > 0 else "Negative after friction"
    })

    # 2. Negative Funding (Long Side)
    n_neg = len(neg_rets)
    if n_neg > 0:
        win_rate_neg = float(np.mean(long_trade_rets > 0)) * 100.0
        gross_neg = float(np.mean(1.0 * neg_rets)) * 100.0
        net_neg = float(np.mean(long_trade_rets)) * 100.0
        sr_neg = float((long_trade_rets.mean() / (long_trade_rets.std() + 1e-6)) * np.sqrt(max(1, n_neg * 12)))
        pf_neg = float(np.sum(long_trade_rets[long_trade_rets > 0]) / max(1e-6, np.abs(np.sum(long_trade_rets[long_trade_rets < 0]))))
    else:
        win_rate_neg, gross_neg, net_neg, sr_neg, pf_neg = 0.0, 0.0, 0.0, 0.0, 0.0

    records.append({
        "Funding Shock Regime": f"Negative Funding (< -{threshold_sigma} sigma) -> LONG",
        "Sample Count (n)": n_neg,
        "Mean Asset Return %": round(float(np.mean(neg_rets)) * 100.0, 4) if n_neg > 0 else 0.0,
        "Mean Trade Gross Return %": round(gross_neg, 4),
        "Mean Trade Net Return %": round(net_neg, 4),
        "Hit Rate %": round(win_rate_neg, 2),
        "Profit Factor": round(pf_neg, 4),
        "Cost-Adjusted Sharpe": round(sr_neg, 4),
        "Net Expectancy ($10 base)": round(net_neg * 0.10, 4),
        "Mechanics": "Mean Reversion" if net_neg > 0 else "Negative after friction"
    })

    df_dir = pd.DataFrame(records)
    summary = {
        "is_asymmetric": bool(abs(net_pos - net_neg) > 0.05),
        "dominant_side": "Long Side (Negative Funding)" if net_neg > net_pos else "Short Side (Positive Funding)"
    }

    return df_dir, summary
