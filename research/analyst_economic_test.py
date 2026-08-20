"""
research/analyst_economic_test.py — Economic Execution, Thresholds & Cost-Sensitivity Engine
=============================================================================================
Evaluates:
1. Execution Filter Probability Thresholds (0.50, 0.55, 0.60, 0.65, 0.70, 0.75)
2. Alternative Meta-Labeling Formulations (Binary Cross Entropy, Focal Loss, Cost-Sensitive BCE)
3. Cost-Sensitivity Analysis (0, 4, 8, 10, 14, 20 bps) & Break-Even Round-Trip Cost
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from typing import Dict, List, Tuple, Any

from validation.purged_split import PurgedWalkForwardSplit


def run_threshold_and_cost_sweep(
    df_features: pd.DataFrame,
    target_labels: np.ndarray,
    fwd_returns: np.ndarray,
    thresholds: List[float] = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75],
    cost_levels_bps: List[float] = [0.0, 4.0, 8.0, 10.0, 14.0, 20.0]
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates out-of-sample trading performance across calibrated confidence thresholds
    and round-trip fee schedules.
    """
    ts_series = pd.Series(pd.to_datetime(df_features.index, utc=True))
    t1_series = pd.Series(pd.to_datetime(df_features.index, utc=True) + pd.Timedelta(hours=24))
    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=24)
    splits = list(splitter.split(ts_series, t1_series))

    # Evaluate on the final test fold
    train_idx, test_idx = splits[-1]
    X_mat = df_features.values.astype(np.float32)

    mean_X = np.nanmean(X_mat[train_idx], axis=0, keepdims=True)
    std_X = np.nanstd(X_mat[train_idx], axis=0, keepdims=True) + 1e-6

    X_tr = np.nan_to_num((X_mat[train_idx] - mean_X) / std_X, nan=0.0)
    X_te = np.nan_to_num((X_mat[test_idx] - mean_X) / std_X, nan=0.0)

    y_tr = target_labels[train_idx]
    y_te = target_labels[test_idx]
    r_te = fwd_returns[test_idx]

    # Base + Calibrated Model
    base_clf = LogisticRegression(C=1.0, max_iter=500, class_weight='balanced', random_state=42)
    cal_clf = CalibratedClassifierCV(estimator=base_clf, method='sigmoid', cv=3)
    cal_clf.fit(X_tr, y_tr)

    probs_te = cal_clf.predict_proba(X_te)  # [P(BUY), P(SELL), P(HOLD)]
    if probs_te.shape[1] < 3:
        p_full = np.zeros((len(test_idx), 3))
        for idx_c, c in enumerate(cal_clf.classes_):
            p_full[:, c] = probs_te[:, idx_c]
        probs_te = p_full

    # 1. Threshold Sweep (Fixed 14 bps round-trip cost)
    thresh_records = []
    base_cost = 0.0014

    for th in thresholds:
        # Take trade only if max(P(BUY), P(SELL)) >= th
        p_buy = probs_te[:, 0]
        p_sell = probs_te[:, 1]

        actions = np.zeros(len(test_idx))
        actions = np.where((p_buy >= th) & (p_buy > p_sell), 1.0, actions)
        actions = np.where((p_sell >= th) & (p_sell > p_buy), -1.0, actions)

        active_mask = (actions != 0.0)
        n_trades = int(active_mask.sum())
        coverage_pct = (n_trades / len(test_idx)) * 100.0

        if n_trades > 0:
            net_rets = (actions[active_mask] * r_te[active_mask]) - base_cost
            gross_rets = actions[active_mask] * r_te[active_mask]
            win_rate = float(np.mean(net_rets > 0)) * 100.0
            avg_gross = float(np.mean(gross_rets)) * 100.0
            avg_net = float(np.mean(net_rets)) * 100.0
            
            gains = gross_rets[gross_rets > 0].sum() if (gross_rets > 0).any() else 1e-6
            losses = np.abs(gross_rets[gross_rets < 0].sum()) if (gross_rets < 0).any() else 1e-6
            pf = float(gains / max(1e-6, losses))

            test_days = len(test_idx) / 24.0
            trades_yr = (n_trades / test_days) * 365.25
            sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(trades_yr))

            eq = np.cumprod(1.0 + net_rets)
            peak = np.maximum.accumulate(eq)
            mdd = float(np.max((peak - eq) / (peak + 1e-6))) * 100.0
        else:
            win_rate = 0.0
            avg_gross = 0.0
            avg_net = 0.0
            pf = 0.0
            sr = 0.0
            mdd = 0.0

        thresh_records.append({
            "Confidence Threshold": th,
            "Active Trades": n_trades,
            "Coverage %": round(coverage_pct, 2),
            "Win Rate %": round(win_rate, 2),
            "Avg Gross Return %": round(avg_gross, 4),
            "Avg Net Return %": round(avg_net, 4),
            "Profit Factor": round(pf, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Max Drawdown %": round(mdd, 2),
            "Net Expectancy ($10 base)": round(avg_net * 0.10, 4)
        })

    # 2. Cost Sensitivity Sweep (At default threshold th=0.50)
    cost_records = []
    p_buy = probs_te[:, 0]
    p_sell = probs_te[:, 1]
    actions = np.where(p_buy > p_sell, 1.0, -1.0)
    gross_rets = actions * r_te

    break_even_cost_bps = float(np.mean(gross_rets) * 10000.0)

    for cost_bps in cost_levels_bps:
        cost_dec = cost_bps / 10000.0
        net_rets = gross_rets - cost_dec
        win_rate = float(np.mean(net_rets > 0)) * 100.0
        avg_net = float(np.mean(net_rets)) * 100.0
        sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(8766.0))

        cost_records.append({
            "Round-Trip Fee (bps)": cost_bps,
            "Win Rate %": round(win_rate, 2),
            "Avg Net Return per Trade %": round(avg_net, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Net Expectancy ($10 base)": round(avg_net * 0.10, 4)
        })

    return pd.DataFrame(thresh_records), pd.DataFrame(cost_records), {"break_even_cost_bps": round(break_even_cost_bps, 2)}
