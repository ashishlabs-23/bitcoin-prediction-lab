"""
research/tradeability_model.py — Excursion Tradeability Scoring & Selective Prediction Engine
=============================================================================================
Calculates Tradeability Score:
    Score = (E[MFE] - Cost) / (E[MAE] + Cost)
Classifies into:
    - TRADEABLE (Score > 1.5)
    - MARGINAL  (1.0 <= Score <= 1.5)
    - ABSTAIN   (Score < 1.0)
Evaluates selective excursion coverage: 50%, 25%, 20%, 10%, 5%.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from typing import Dict, List, Tuple, Any

from research.mfe_target_audit import compute_directional_excursions


def evaluate_tradeability_and_selectivity(
    df: pd.DataFrame,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    train_end_idx: int,
    val_end_idx: int,
    coverage_levels: List[float] = [0.50, 0.25, 0.20, 0.10, 0.05]
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates Tradeability classification and selective excursion forecasting on the Confirmation split.
    """
    close_aligned = close.loc[df.index]
    fwd_ret_24h = np.log(close_aligned.shift(-24) / close_aligned).fillna(0.0)
    exc = compute_directional_excursions(close, high, low, horizon_bars=24)
    mfe_long = exc["mfe_long"]
    mae_long = exc["mae_long"]

    feat_cols = [c for c in df.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    X_mat = df[feat_cols].values.astype(np.float32)

    mean_tr = np.nanmean(X_mat[:train_end_idx], axis=0, keepdims=True)
    std_tr = np.nanstd(X_mat[:train_end_idx], axis=0, keepdims=True) + 1e-6

    X_tr = np.nan_to_num((X_mat[:train_end_idx] - mean_tr) / std_tr, nan=0.0)
    X_val = np.nan_to_num((X_mat[train_end_idx:val_end_idx] - mean_tr) / std_tr, nan=0.0)
    X_conf = np.nan_to_num((X_mat[val_end_idx:] - mean_tr) / std_tr, nan=0.0)

    reg_mfe = Ridge(alpha=1.0)
    reg_mfe.fit(X_tr, mfe_long[:train_end_idx])
    pred_mfe_conf = np.maximum(0.0, reg_mfe.predict(X_conf))

    reg_mae = Ridge(alpha=1.0)
    reg_mae.fit(X_tr, mae_long[:train_end_idx])
    pred_mae_conf = np.maximum(0.0, reg_mae.predict(X_conf))

    base_cost = 0.0014
    tradeability_scores = (pred_mfe_conf - base_cost) / (pred_mae_conf + base_cost + 1e-6)

    # 1. Tradeability Category Evaluation
    cat_tradeable = (tradeability_scores > 1.5)
    cat_marginal = (tradeability_scores >= 1.0) & (tradeability_scores <= 1.5)
    cat_abstain = (tradeability_scores < 1.0)

    r_conf = fwd_ret_24h.iloc[val_end_idx:].values
    y_mfe_conf = mfe_long[val_end_idx:]
    y_mae_conf = mae_long[val_end_idx:]

    cat_dict = {
        "TRADEABLE (Score > 1.5)": cat_tradeable,
        "MARGINAL (1.0 <= Score <= 1.5)": cat_marginal,
        "ABSTAIN (Score < 1.0)": cat_abstain
    }

    cat_records = []
    for cat_name, mask in cat_dict.items():
        n_c = int(mask.sum())
        cov_pct = (n_c / len(r_conf)) * 100.0
        if n_c > 0:
            actual_mfe = float(np.mean(y_mfe_conf[mask])) * 100.0
            actual_mae = float(np.mean(y_mae_conf[mask])) * 100.0
            ratio = float(actual_mfe / max(1e-6, actual_mae))
            win_rate = float(np.mean(r_conf[mask] > base_cost)) * 100.0
        else:
            actual_mfe, actual_mae, ratio, win_rate = 0.0, 0.0, 0.0, 0.0

        cat_records.append({
            "Tradeability Classification": cat_name,
            "Sample Count (n)": n_c,
            "Market Coverage %": round(cov_pct, 2),
            "Actual Mean MFE %": round(actual_mfe, 3),
            "Actual Mean MAE %": round(actual_mae, 3),
            "Empirical Excursion Ratio": round(ratio, 3),
            "Trade Win Rate %": round(win_rate, 2)
        })
    df_cats = pd.DataFrame(cat_records)

    # 2. Selective Excursion Slicing
    sel_records = []
    # Calibrate thresholds on VALIDATION partition
    p_mfe_val = np.maximum(0.0, reg_mfe.predict(X_val))
    p_mae_val = np.maximum(0.0, reg_mae.predict(X_val))
    scores_val = (p_mfe_val - base_cost) / (p_mae_val + base_cost + 1e-6)

    for cov in coverage_levels:
        th_val = float(np.quantile(scores_val, 1.0 - cov))
        active_mask = (tradeability_scores >= th_val)
        n_act = int(active_mask.sum())
        emp_cov = (n_act / len(r_conf)) * 100.0

        if n_act > 0:
            act_mfe = float(np.mean(y_mfe_conf[active_mask])) * 100.0
            act_mae = float(np.mean(y_mae_conf[active_mask])) * 100.0
            net_rets = r_conf[active_mask] - base_cost
            avg_net = float(np.mean(net_rets)) * 100.0
            sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(max(1, (n_act / max(1, len(r_conf)/24.0)) * 365.25)))
        else:
            act_mfe, act_mae, avg_net, sr = 0.0, 0.0, 0.0, 0.0

        sel_records.append({
            "Target Selective Coverage": f"{int(cov*100)}%",
            "Active Trades (n)": n_act,
            "Empirical Coverage %": round(emp_cov, 2),
            "Actual Mean MFE %": round(act_mfe, 3),
            "Actual Mean MAE %": round(act_mae, 3),
            "Avg Net Return % (14 bps)": round(avg_net, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Net Expectancy ($10 base)": round(avg_net * 0.10, 4)
        })
    df_selective = pd.DataFrame(sel_records)

    meta = {
        "tradeable_coverage": float(df_cats.iloc[0]["Market Coverage %"]),
        "tradeable_excursion_ratio": float(df_cats.iloc[0]["Empirical Excursion Ratio"])
    }

    return df_cats, df_selective, meta
