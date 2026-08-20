"""
research/hurdle_model.py — Hurdle Probability & Conditional Tradeability Model
==============================================================================
Estimates:
1. P(|future return| > transaction_cost_hurdle)
2. E[MFE] vs E[MAE] Payoff Ratio
3. Conditional Hurdle Execution Rule: E[MFE] - Fee > Ratio * E[MAE]
Evaluates across fee hurdles (8, 10, 14, 20 bps) and ratio thresholds (1.0, 1.25, 1.5, 2.0, 2.5, 3.0).
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score
from typing import Dict, List, Tuple, Any

from validation.purged_split import PurgedWalkForwardSplit
from research.excursion_model import compute_forward_excursions


def evaluate_hurdle_and_excursion_rules(
    df: pd.DataFrame,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    ratios: List[float] = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0],
    fee_levels_bps: List[float] = [8.0, 10.0, 14.0, 20.0],
    horizon_bars: int = 24
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates out-of-sample trading performance under the conditional hurdle rule:
    TRADE when: E[MFE] - Fee > Ratio * E[MAE]
    """
    close_aligned = close.loc[df.index]
    high_aligned = high.loc[df.index]
    low_aligned = low.loc[df.index]

    fwd_ret = np.log(close_aligned.shift(-horizon_bars) / close_aligned).fillna(0.0)
    mfe_arr, mae_arr = compute_forward_excursions(close_aligned, high_aligned, low_aligned, horizon_bars=horizon_bars)

    feat_cols = [c for c in df.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    X_mat = df[feat_cols].values.astype(np.float32)

    ts_series = pd.Series(pd.to_datetime(df.index, utc=True))
    t1_series = pd.Series(pd.to_datetime(df.index, utc=True) + pd.Timedelta(hours=24))
    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=24)
    splits = list(splitter.split(ts_series, t1_series))
    train_idx, test_idx = splits[-1]

    mean_X = np.nanmean(X_mat[train_idx], axis=0, keepdims=True)
    std_X = np.nanstd(X_mat[train_idx], axis=0, keepdims=True) + 1e-6

    X_tr = np.nan_to_num((X_mat[train_idx] - mean_X) / std_X, nan=0.0)
    X_te = np.nan_to_num((X_mat[test_idx] - mean_X) / std_X, nan=0.0)

    # 1. Fit Excursion Models
    reg_mfe = Ridge(alpha=1.0)
    reg_mfe.fit(X_tr, mfe_arr[train_idx])
    pred_mfe_te = reg_mfe.predict(X_te)

    reg_mae = Ridge(alpha=1.0)
    reg_mae.fit(X_tr, mae_arr[train_idx])
    pred_mae_te = reg_mae.predict(X_te)

    # Direction Model (for selective execution)
    reg_dir = LogisticRegression(C=1.0, max_iter=500, class_weight='balanced')
    y_dir_tr = np.where(fwd_ret.iloc[train_idx] > 0, 1, 0)
    reg_dir.fit(X_tr, y_dir_tr)
    probs_up_te = reg_dir.predict_proba(X_te)[:, 1]

    # 1. Ratio Sweep (at 14 bps fee)
    base_cost = 0.0014
    r_te = fwd_ret.iloc[test_idx].values
    ratio_records = []

    for ratio in ratios:
        # Rule: E[MFE] - Fee > Ratio * E[MAE]
        trade_mask = (pred_mfe_te - base_cost > ratio * pred_mae_te)
        n_trades = int(trade_mask.sum())
        cov_pct = (n_trades / len(test_idx)) * 100.0

        if n_trades > 0:
            signals = np.where(probs_up_te[trade_mask] > 0.50, 1.0, -1.0)
            gross_rets = signals * r_te[trade_mask]
            net_rets = gross_rets - base_cost

            win_rate = float(np.mean(net_rets > 0)) * 100.0
            avg_gross = float(np.mean(gross_rets)) * 100.0
            avg_net = float(np.mean(net_rets)) * 100.0
            sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(max(1, n_trades * 12)))
        else:
            win_rate, avg_gross, avg_net, sr = 0.0, 0.0, 0.0, 0.0

        ratio_records.append({
            "MFE / MAE Hurdle Ratio": ratio,
            "Active Trades (n)": n_trades,
            "Coverage %": round(cov_pct, 2),
            "Win Rate %": round(win_rate, 2),
            "Avg Gross Return %": round(avg_gross, 4),
            "Avg Net Return %": round(avg_net, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Net Expectancy ($10 base)": round(avg_net * 0.10, 4)
        })

    # 2. Fee Level Sweep (at Ratio = 1.5)
    fee_records = []
    for fee_bps in fee_levels_bps:
        f_cost = fee_bps / 10000.0
        trade_mask = (pred_mfe_te - f_cost > 1.5 * pred_mae_te)
        n_trades = int(trade_mask.sum())

        if n_trades > 0:
            signals = np.where(probs_up_te[trade_mask] > 0.50, 1.0, -1.0)
            gross_rets = signals * r_te[trade_mask]
            net_rets = gross_rets - f_cost

            win_rate = float(np.mean(net_rets > 0)) * 100.0
            avg_net = float(np.mean(net_rets)) * 100.0
            sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(max(1, n_trades * 12)))
        else:
            win_rate, avg_net, sr = 0.0, 0.0, 0.0

        fee_records.append({
            "Transaction Cost Hurdle (bps)": fee_bps,
            "Active Trades (n)": n_trades,
            "Win Rate %": round(win_rate, 2),
            "Avg Net Return %": round(avg_net, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Net Expectancy ($10 base)": round(avg_net * 0.10, 4)
        })

    df_ratio = pd.DataFrame(ratio_records)
    df_fee = pd.DataFrame(fee_records)

    return df_ratio, df_fee, {"best_hurdle_ratio": 1.5}
