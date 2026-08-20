"""
research/economic_bootstrap.py — 10,000 Block Bootstrap Economic Validation Engine
==================================================================================
Executes 10,000 block bootstrap resamples on the point-in-time reference sizing returns:
- Mean Net Return 95% Confidence Interval
- Sharpe Ratio 95% Confidence Interval
- Sortino Ratio 95% Confidence Interval
- Maximum Drawdown 95% Confidence Interval
- Profit Factor 95% Confidence Interval
Accounts for temporal serial correlation using block resampling (block size = 24h).
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any


def run_economic_block_bootstrap(
    net_pnl: np.ndarray,
    n_resamples: int = 10000,
    block_size: int = 24
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Executes block bootstrap resampling on strategy returns and calculates robust confidence intervals.
    """
    n = len(net_pnl)
    n_blocks = max(1, n // block_size)
    np.random.seed(42)

    boot_means = []
    boot_sharpes = []
    boot_sortinos = []
    boot_mdds = []
    boot_pfs = []

    for _ in range(n_resamples):
        rand_blocks = np.random.choice(n_blocks, size=n_blocks, replace=True)
        boot_idx = np.concatenate([np.arange(b * block_size, min(n, (b + 1) * block_size)) for b in rand_blocks])
        sample_pnl = net_pnl[boot_idx]

        m_ret = float(np.mean(sample_pnl))
        s_ret = float(np.std(sample_pnl)) + 1e-8
        sr = (m_ret / s_ret) * np.sqrt(8766.0)

        downside_std = float(np.std(sample_pnl[sample_pnl < 0])) + 1e-8 if (sample_pnl < 0).any() else 1e-6
        sortino = (m_ret / downside_std) * np.sqrt(8766.0)

        eq = np.cumprod(1.0 + sample_pnl)
        peak = np.maximum.accumulate(eq)
        mdd = float(np.max((peak - eq) / (peak + 1e-6))) * 100.0

        gains = sample_pnl[sample_pnl > 0].sum() if (sample_pnl > 0).any() else 1e-6
        losses = np.abs(sample_pnl[sample_pnl < 0].sum()) if (sample_pnl < 0).any() else 1e-6
        pf = float(gains / max(1e-6, losses))

        boot_means.append(m_ret * 100.0)
        boot_sharpes.append(sr)
        boot_sortinos.append(sortino)
        boot_mdds.append(mdd)
        boot_pfs.append(pf)

    def ci(arr):
        return [round(float(np.percentile(arr, 2.5)), 4), round(float(np.percentile(arr, 97.5)), 4)]

    ci_mean = ci(boot_means)
    ci_sr = ci(boot_sharpes)
    ci_sortino = ci(boot_sortinos)
    ci_mdd = ci(boot_mdds)
    ci_pf = ci(boot_pfs)

    records = [
        {"Performance Metric": "Mean Net Return %", "Point Estimate": round(float(np.mean(net_pnl))*100.0, 4), "Bootstrap Mean": round(float(np.mean(boot_means)), 4), "95% Confidence Interval": f"[{ci_mean[0]:.4f}%, {ci_mean[1]:.4f}%]", "Zero Included in 95% CI?": "YES" if ci_mean[0] <= 0 <= ci_mean[1] else "NO"},
        {"Performance Metric": "Cost-Adjusted Sharpe", "Point Estimate": round(float(np.mean(net_pnl)/(np.std(net_pnl)+1e-8))*np.sqrt(8766.0), 4), "Bootstrap Mean": round(float(np.mean(boot_sharpes)), 4), "95% Confidence Interval": f"[{ci_sr[0]:.4f}, {ci_sr[1]:.4f}]", "Zero Included in 95% CI?": "YES" if ci_sr[0] <= 0 <= ci_sr[1] else "NO"},
        {"Performance Metric": "Sortino Ratio", "Point Estimate": round(float(np.mean(boot_sortinos)), 4), "Bootstrap Mean": round(float(np.mean(boot_sortinos)), 4), "95% Confidence Interval": f"[{ci_sortino[0]:.4f}, {ci_sortino[1]:.4f}]", "Zero Included in 95% CI?": "YES" if ci_sortino[0] <= 0 <= ci_sortino[1] else "NO"},
        {"Performance Metric": "Maximum Drawdown %", "Point Estimate": round(float(np.mean(boot_mdds)), 2), "Bootstrap Mean": round(float(np.mean(boot_mdds)), 2), "95% Confidence Interval": f"[{ci_mdd[0]:.2f}%, {ci_mdd[1]:.2f}%]", "Zero Included in 95% CI?": "N/A"},
        {"Performance Metric": "Profit Factor", "Point Estimate": round(float(np.mean(boot_pfs)), 4), "Bootstrap Mean": round(float(np.mean(boot_pfs)), 4), "95% Confidence Interval": f"[{ci_pf[0]:.4f}, {ci_pf[1]:.4f}]", "Zero Included in 95% CI?": "N/A"}
    ]
    df_boot = pd.DataFrame(records)

    meta = {
        "bootstrap_mean_net_ci": ci_mean,
        "bootstrap_sharpe_ci": ci_sr,
        "is_sharpe_strictly_positive": bool(ci_sr[0] > 0.0)
    }

    return df_boot, meta
