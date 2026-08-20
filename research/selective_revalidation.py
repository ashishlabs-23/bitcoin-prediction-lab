"""
research/selective_revalidation.py — Selective Prediction & Abstention Revalidation Engine
==========================================================================================
Evaluates selective trading coverage: 100%, 75%, 50%, 25%, 10%, 5%
Thresholds are derived strictly from the Validation partition confidence distribution
and evaluated out-of-sample on the untouched Final Confirmation partition.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from typing import Dict, List, Tuple, Any


def evaluate_selective_revalidation(
    df: pd.DataFrame,
    close: pd.Series,
    train_end_idx: int,
    val_end_idx: int,
    target_coverages: List[float] = [1.0, 0.75, 0.50, 0.25, 0.10, 0.05]
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Calibrates confidence thresholds on Validation and tests on Confirmation partition.
    """
    close_aligned = close.loc[df.index]
    fwd_ret_24h = np.log(close_aligned.shift(-24) / close_aligned).fillna(0.0)
    y_dir = np.where(fwd_ret_24h > 0, 1, 0)
    r_arr = fwd_ret_24h.values
    base_cost = 0.0014  # 14 bps

    feat_cols = [c for c in df.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    X_mat = df[feat_cols].values.astype(np.float32)

    mean_tr = np.nanmean(X_mat[:train_end_idx], axis=0, keepdims=True)
    std_tr = np.nanstd(X_mat[:train_end_idx], axis=0, keepdims=True) + 1e-6

    X_tr = np.nan_to_num((X_mat[:train_end_idx] - mean_tr) / std_tr, nan=0.0)
    X_val = np.nan_to_num((X_mat[train_end_idx:val_end_idx] - mean_tr) / std_tr, nan=0.0)
    X_conf = np.nan_to_num((X_mat[val_end_idx:] - mean_tr) / std_tr, nan=0.0)

    clf = CalibratedClassifierCV(estimator=LogisticRegression(C=1.0, max_iter=500, class_weight='balanced'), method='sigmoid', cv=3)
    clf.fit(X_tr, y_dir[:train_end_idx])

    # Compute validation confidence scores: |P(up) - 0.5|
    probs_val = clf.predict_proba(X_val)[:, 1]
    conf_val = np.abs(probs_val - 0.5)

    # Compute confirmation confidence scores
    probs_conf = clf.predict_proba(X_conf)[:, 1]
    conf_conf = np.abs(probs_conf - 0.5)
    r_conf = r_arr[val_end_idx:]

    records = []

    for cov in target_coverages:
        # Determine quantile threshold on VALIDATION partition
        th_val = float(np.quantile(conf_val, 1.0 - cov)) if cov < 1.0 else 0.0
        active_mask = (conf_conf >= th_val)
        n_active = int(active_mask.sum())
        actual_cov = (n_active / len(r_conf)) * 100.0

        if n_active > 0:
            signals = np.where(probs_conf[active_mask] >= 0.5, 1.0, -1.0)
            gross_rets = signals * r_conf[active_mask]
            net_rets = gross_rets - base_cost

            win_rate = float(np.mean(net_rets > 0)) * 100.0
            avg_gross = float(np.mean(gross_rets)) * 100.0
            avg_net = float(np.mean(net_rets)) * 100.0

            gains = gross_rets[gross_rets > 0].sum() if (gross_rets > 0).any() else 1e-6
            losses = np.abs(gross_rets[gross_rets < 0].sum()) if (gross_rets < 0).any() else 1e-6
            pf = float(gains / max(1e-6, losses))

            sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(max(1, (n_active / max(1, len(r_conf)/24.0)) * 365.25)))

            eq = np.cumprod(1.0 + net_rets)
            peak = np.maximum.accumulate(eq)
            mdd = float(np.max((peak - eq) / (peak + 1e-6))) * 100.0
        else:
            win_rate, avg_gross, avg_net, pf, sr, mdd = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        records.append({
            "Target Coverage": f"{int(cov*100)}%",
            "Active Trades (n)": n_active,
            "Empirical Confirmation Coverage %": round(actual_cov, 2),
            "Win Rate %": round(win_rate, 2),
            "Avg Gross Return %": round(avg_gross, 4),
            "Avg Net Return %": round(avg_net, 4),
            "Profit Factor": round(pf, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Max Drawdown %": round(mdd, 2),
            "Net Expectancy ($10 base)": round(avg_net * 0.10, 4)
        })

    df_selective = pd.DataFrame(records)
    best_cov = df_selective.loc[df_selective["Cost-Adjusted Sharpe"].idxmax()]["Target Coverage"]

    return df_selective, {"best_coverage": best_cov}
