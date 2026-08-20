"""
research/conditional_direction.py — Conditional Direction & Long/Short Asymmetry Engine
======================================================================================
Tests whether directional sign prediction becomes viable when conditioned on:
1. Predicted MFE > Transaction-Cost Hurdle (14 bps)
2. Predicted MFE High AND Predicted MAE Low (Asymmetric Envelope)
3. Evaluates Long vs Short Excursion Asymmetry across market regimes
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score
from typing import Dict, List, Tuple, Any

from research.mfe_target_audit import compute_directional_excursions


def evaluate_conditional_direction_and_asymmetry(
    df: pd.DataFrame,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    train_end_idx: int,
    val_end_idx: int
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates directional accuracy inside conditional excursion subsets and measures long/short structural asymmetry.
    """
    close_aligned = close.loc[df.index]
    fwd_ret_24h = np.log(close_aligned.shift(-24) / close_aligned).fillna(0.0)
    exc = compute_directional_excursions(close, high, low, horizon_bars=24)
    mfe_long = exc["mfe_long"]
    mae_long = exc["mae_long"]
    mfe_short = exc["mfe_short"]
    mae_short = exc["mae_short"]

    feat_cols = [c for c in df.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    X_mat = df[feat_cols].values.astype(np.float32)

    mean_tr = np.nanmean(X_mat[:train_end_idx], axis=0, keepdims=True)
    std_tr = np.nanstd(X_mat[:train_end_idx], axis=0, keepdims=True) + 1e-6

    X_tr = np.nan_to_num((X_mat[:train_end_idx] - mean_tr) / std_tr, nan=0.0)
    X_conf = np.nan_to_num((X_mat[val_end_idx:] - mean_tr) / std_tr, nan=0.0)

    # 1. Fit Excursion Predictors
    reg_mfe = Ridge(alpha=1.0)
    reg_mfe.fit(X_tr, mfe_long[:train_end_idx])
    pred_mfe_conf = reg_mfe.predict(X_conf)

    reg_mae = Ridge(alpha=1.0)
    reg_mae.fit(X_tr, mae_long[:train_end_idx])
    pred_mae_conf = reg_mae.predict(X_conf)

    # 2. Fit Base Directional Model
    y_dir_tr = np.where(fwd_ret_24h.iloc[:train_end_idx] > 0, 1, 0)
    clf_dir = LogisticRegression(C=1.0, max_iter=500, class_weight='balanced', random_state=42)
    clf_dir.fit(X_tr, y_dir_tr)
    probs_up_conf = clf_dir.predict_proba(X_conf)[:, 1]

    r_conf = fwd_ret_24h.iloc[val_end_idx:].values
    y_dir_conf = np.where(r_conf > 0, 1, 0)
    base_cost = 0.0014

    # Evaluate Subsets
    subsets = {
        "1. Unconditional Global Direction (Baseline)": np.ones(len(r_conf), dtype=bool),
        "2. Conditioned on Pred MFE > 14 bps Hurdle": (pred_mfe_conf > 0.0014),
        "3. Conditioned on Pred MFE > 25 bps Hurdle": (pred_mfe_conf > 0.0025),
        "4. Conditioned on Pred MFE > 50 bps Hurdle": (pred_mfe_conf > 0.0050),
        "5. Asymmetric Envelope: Pred MFE High (> 75th) & Pred MAE Low (< 25th)": (pred_mfe_conf > np.quantile(pred_mfe_conf, 0.75)) & (pred_mae_conf < np.quantile(pred_mae_conf, 0.25))
    }

    cond_records = []

    for s_name, mask in subsets.items():
        n_sub = int(mask.sum())
        cov_pct = (n_sub / len(r_conf)) * 100.0

        if n_sub > 10 and len(np.unique(y_dir_conf[mask])) >= 2:
            try:
                auc_sub = float(roc_auc_score(y_dir_conf[mask], probs_up_conf[mask]))
            except Exception:
                auc_sub = 0.50
            preds_binary = (probs_up_conf[mask] >= 0.50).astype(int)
            acc_sub = float(accuracy_score(y_dir_conf[mask], preds_binary)) * 100.0
            p_up = float(np.mean(y_dir_conf[mask] == 1)) * 100.0
            p_down = 100.0 - p_up

            signals = np.where(probs_up_conf[mask] >= 0.50, 1.0, -1.0)
            net_rets = signals * r_conf[mask] - base_cost
            avg_net = float(np.mean(net_rets)) * 100.0
            sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(max(1, (n_sub / max(1, len(r_conf)/24.0)) * 365.25)))
        else:
            auc_sub, acc_sub, p_up, p_down, avg_net, sr = 0.50, 0.0, 0.0, 0.0, 0.0, 0.0

        cond_records.append({
            "Conditional Execution Strategy": s_name,
            "Sample Count (n)": n_sub,
            "Coverage %": round(cov_pct, 2),
            "P(Up | Condition) %": round(p_up, 2),
            "P(Down | Condition) %": round(p_down, 2),
            "Directional Accuracy %": round(acc_sub, 2),
            "Directional ROC AUC": round(auc_sub, 4),
            "Avg Net Return % (14 bps)": round(avg_net, 4),
            "Cost-Adjusted Sharpe": round(sr, 4)
        })

    df_cond = pd.DataFrame(cond_records)

    # Long vs Short Asymmetry Analysis
    asym_records = [
        {"Position Side": "Long Excursion (Upside)", "Mean Favorable MFE %": round(float(np.mean(mfe_long[val_end_idx:])) * 100.0, 3), "Mean Adverse MAE %": round(float(np.mean(mae_long[val_end_idx:])) * 100.0, 3), "Favorable/Adverse Ratio": round(float(np.mean(mfe_long[val_end_idx:]) / max(1e-6, np.mean(mae_long[val_end_idx:]))), 3)},
        {"Position Side": "Short Excursion (Downside)", "Mean Favorable MFE %": round(float(np.mean(mfe_short[val_end_idx:])) * 100.0, 3), "Mean Adverse MAE %": round(float(np.mean(mae_short[val_end_idx:])) * 100.0, 3), "Favorable/Adverse Ratio": round(float(np.mean(mfe_short[val_end_idx:]) / max(1e-6, np.mean(mae_short[val_end_idx:]))), 3)}
    ]
    df_asym = pd.DataFrame(asym_records)

    meta = {
        "asymmetric_envelope_auc": float(df_cond.iloc[4]["Directional ROC AUC"]),
        "unconditional_auc": float(df_cond.iloc[0]["Directional ROC AUC"]),
        "auc_improvement": round(float(df_cond.iloc[4]["Directional ROC AUC"] - df_cond.iloc[0]["Directional ROC AUC"]), 4)
    }

    return df_cond, df_asym, meta
