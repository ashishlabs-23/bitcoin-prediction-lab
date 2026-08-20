"""
research/selective_prediction.py — Selective Prediction & Abstention Engine
============================================================================
Evaluates selective trading policies allowing the model to ABSTAIN when confidence is low
or conformal uncertainty is high. Evaluates coverage levels: 50%, 25%, 10%, 5%.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from typing import Dict, List, Tuple, Any

from validation.purged_split import PurgedWalkForwardSplit


def evaluate_selective_abstention_policy(
    df: pd.DataFrame,
    close: pd.Series,
    target_labels: np.ndarray,
    fwd_returns: np.ndarray,
    target_coverages: List[float] = [1.0, 0.50, 0.25, 0.10, 0.05]
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates selective prediction out-of-sample at fixed coverage constraints.
    """
    ts_series = pd.Series(pd.to_datetime(df.index, utc=True))
    t1_series = pd.Series(pd.to_datetime(df.index, utc=True) + pd.Timedelta(hours=24))
    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=24)
    splits = list(splitter.split(ts_series, t1_series))

    train_idx, test_idx = splits[-1]
    feat_cols = [c for c in df.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    X_mat = df[feat_cols].values.astype(np.float32)

    mean_X = np.nanmean(X_mat[train_idx], axis=0, keepdims=True)
    std_X = np.nanstd(X_mat[train_idx], axis=0, keepdims=True) + 1e-6

    X_tr = np.nan_to_num((X_mat[train_idx] - mean_X) / std_X, nan=0.0)
    X_te = np.nan_to_num((X_mat[test_idx] - mean_X) / std_X, nan=0.0)

    y_tr = target_labels[train_idx]
    y_te = target_labels[test_idx]
    r_te = fwd_returns[test_idx]

    clf = CalibratedClassifierCV(estimator=LogisticRegression(C=1.0, max_iter=500, class_weight='balanced', random_state=42), method='sigmoid', cv=3)
    clf.fit(X_tr, y_tr)

    probs_te = clf.predict_proba(X_te)
    if probs_te.shape[1] < 3:
        p_full = np.zeros((len(test_idx), 3))
        for idx_c, c in enumerate(clf.classes_):
            p_full[:, c] = probs_te[:, idx_c]
        probs_te = p_full

    # Directional confidence margin: |P(BUY) - P(SELL)|
    confidence = np.abs(probs_te[:, 0] - probs_te[:, 1])

    records = []
    base_cost = 0.0014  # 14 bps round-trip

    for cov in target_coverages:
        # Determine quantile threshold on training/validation or confidence distribution
        th = float(np.quantile(confidence, 1.0 - cov))
        active_mask = (confidence >= th)
        n_active = int(active_mask.sum())
        actual_cov = (n_active / len(test_idx)) * 100.0

        if n_active > 0:
            actions = np.where(probs_te[active_mask, 0] > probs_te[active_mask, 1], 1.0, -1.0)
            gross_rets = actions * r_te[active_mask]
            net_rets = gross_rets - base_cost

            win_rate = float(np.mean(net_rets > 0)) * 100.0
            avg_gross = float(np.mean(gross_rets)) * 100.0
            avg_net = float(np.mean(net_rets)) * 100.0

            gains = gross_rets[gross_rets > 0].sum() if (gross_rets > 0).any() else 1e-6
            losses = np.abs(gross_rets[gross_rets < 0].sum()) if (gross_rets < 0).any() else 1e-6
            pf = float(gains / max(1e-6, losses))

            test_days = len(test_idx) / 24.0
            trades_yr = (n_active / test_days) * 365.25
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

        records.append({
            "Target Coverage": f"{int(cov*100)}%",
            "Active Trades": n_active,
            "Empirical Coverage %": round(actual_cov, 2),
            "Win Rate %": round(win_rate, 2),
            "Avg Gross Return %": round(avg_gross, 4),
            "Avg Net Return %": round(avg_net, 4),
            "Profit Factor": round(pf, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Max Drawdown %": round(mdd, 2),
            "Net Expectancy ($10 base)": round(avg_net * 0.10, 4)
        })

    return pd.DataFrame(records), {"evaluated_coverages": len(target_coverages)}
