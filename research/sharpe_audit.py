"""
research/sharpe_audit.py — Sharpe Annualization & Return Dispersion Forensics
=============================================================================
Investigates Sharpe ratio annualization methods and return distributions:
- Return frequency & observation count
- Active trade count & calendar duration
- Mean return, return standard deviation, lag-1 serial autocorrelation
- Unannualized Sharpe, Daily-equivalent Sharpe, Hourly-equivalent Sharpe, Trade-based Sharpe, Time-based Sharpe
- Triggers forensic warnings if observed Sharpe > 5.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any


def audit_sharpe_calculations(
    net_pnl_series: pd.Series,
    timestamps: pd.DatetimeIndex,
    active_mask: np.ndarray = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Computes rigorous unannualized and annualized Sharpe metrics across time and trade frequencies.
    """
    pnl = net_pnl_series.values
    n_obs = len(pnl)
    t_start = timestamps[0]
    t_end = timestamps[-1]
    cal_days = (t_end - t_start).total_seconds() / 86400.0

    if active_mask is None:
        active_mask = (pnl != 0.0)
    n_trades = int(active_mask.sum())

    mean_ret = float(np.mean(pnl))
    std_ret = float(np.std(pnl)) + 1e-8
    rho_1 = float(np.corrcoef(pnl[:-1], pnl[1:])[0, 1]) if len(pnl) > 2 else 0.0

    # Sharpe Numerator & Denominator
    sr_unannualized = mean_ret / std_ret

    # Hourly Time-Based Annualization: sqrt(8766 hours/year)
    ann_factor_hourly = np.sqrt(8766.0)
    sr_time_annualized = sr_unannualized * ann_factor_hourly

    # Daily-Equivalent: sqrt(365.25 days/year)
    ann_factor_daily = np.sqrt(365.25)
    sr_daily_equivalent = sr_unannualized * np.sqrt(24.0) * ann_factor_daily

    # Trade-Based Annualization: sqrt(actual trades / calendar year)
    trades_per_year = (n_trades / max(1.0, cal_days)) * 365.25
    sr_trade_annualized = sr_unannualized * np.sqrt(trades_per_year)

    sharpe_records = [
        {"Sharpe Variant": "1. Unannualized (Per 1h Bar)", "Annualization Factor": "1.00x", "Sharpe Value": round(sr_unannualized, 4), "Forensic Status": "Pure Statistical Metric"},
        {"Sharpe Variant": "2. Time-Based Annualized (sqrt(8766))", "Annualization Factor": f"{ann_factor_hourly:.2f}x", "Sharpe Value": round(sr_time_annualized, 4), "Forensic Status": "WARNING: High Frequency Scaling" if abs(sr_time_annualized) > 5.0 else "Normal Bounds"},
        {"Sharpe Variant": "3. Trade-Based Annualized (sqrt(Trades/Yr))", "Annualization Factor": f"{np.sqrt(trades_per_year):.2f}x", "Sharpe Value": round(sr_trade_annualized, 4), "Forensic Status": "Correct Trade-Weighted Scaling"},
        {"Sharpe Variant": "4. Lag-1 Autocorrelation Adjusted", "Annualization Factor": f"{np.sqrt(max(1e-6, 1.0 - rho_1)/(1.0 + rho_1)):.2f}x", "Sharpe Value": round(sr_time_annualized * np.sqrt((1.0 - rho_1)/(1.0 + rho_1 + 1e-6)), 4), "Forensic Status": "Serial Correlation Corrected"}
    ]
    df_sharpe = pd.DataFrame(sharpe_records)

    meta = {
        "n_observations": n_obs,
        "n_active_trades": n_trades,
        "calendar_days": round(cal_days, 2),
        "mean_return_pct": round(mean_ret * 100.0, 4),
        "std_return_pct": round(std_ret * 100.0, 4),
        "serial_correlation_rho1": round(rho_1, 4),
        "unannualized_sharpe": round(sr_unannualized, 4),
        "trade_annualized_sharpe": round(sr_trade_annualized, 4)
    }

    return df_sharpe, meta
