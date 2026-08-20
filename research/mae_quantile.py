"""
research/mae_quantile.py — Quantile MAE Forecasting & Excursion Envelope Engine
================================================================================
Predicts:
1. MAE Quantiles: P10, P25, P50, P75, P90 using Quantile Loss with non-crossing monotonicity
2. Conformal 90% and 95% MAE prediction intervals
3. Combined Excursion Envelope (Expected Upside MFE vs Expected Downside MAE)
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import QuantileRegressor
from typing import Dict, List, Tuple, Any

from research.mfe_target_audit import compute_directional_excursions
from research.mfe_quantile import pinball_loss


def evaluate_mae_quantile_and_envelope(
    df: pd.DataFrame,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    train_end_idx: int,
    val_end_idx: int,
    quantiles: List[float] = [0.10, 0.25, 0.50, 0.75, 0.90]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Fits quantile MAE models, evaluates conformal bounds, and generates the joint 24h excursion price envelope.
    """
    exc = compute_directional_excursions(close, high, low, horizon_bars=24)
    mae_long = exc["mae_long"]
    mfe_long = exc["mfe_long"]

    feat_cols = [c for c in df.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    X_mat = df[feat_cols].values.astype(np.float32)

    mean_tr = np.nanmean(X_mat[:train_end_idx], axis=0, keepdims=True)
    std_tr = np.nanstd(X_mat[:train_end_idx], axis=0, keepdims=True) + 1e-6

    X_tr = np.nan_to_num((X_mat[:train_end_idx] - mean_tr) / std_tr, nan=0.0)
    X_conf = np.nan_to_num((X_mat[val_end_idx:] - mean_tr) / std_tr, nan=0.0)

    y_tr_mae = mae_long[:train_end_idx]
    y_conf_mae = mae_long[val_end_idx:]

    quantile_preds = {}
    records_q = []

    for q in quantiles:
        qr = QuantileRegressor(quantile=q, alpha=0.01, solver='highs')
        qr.fit(X_tr, y_tr_mae)
        p_conf = qr.predict(X_conf)
        quantile_preds[q] = p_conf

    sorted_quantiles = sorted(quantiles)
    pred_mat = np.column_stack([quantile_preds[q] for q in sorted_quantiles])
    pred_mat = np.maximum.accumulate(pred_mat, axis=1)

    for idx, q in enumerate(sorted_quantiles):
        p_q = pred_mat[:, idx]
        emp_cov = float(np.mean(y_conf_mae <= p_q)) * 100.0
        cov_err = float(emp_cov - (q * 100.0))
        ploss = pinball_loss(y_conf_mae, p_q, q) * 100.0

        records_q.append({
            "Target Quantile": f"P{int(q*100)} MAE",
            "Nominal Quantile %": f"{int(q*100)}%",
            "Empirical Confirmation Coverage %": round(emp_cov, 2),
            "Coverage Error %": round(cov_err, 2),
            "Pinball Loss (x100)": round(ploss, 4),
            "Mean Predicted MAE %": round(float(np.mean(p_q)) * 100.0, 3)
        })

    df_mae_quantiles = pd.DataFrame(records_q)

    # Conformal MAE Intervals
    X_val = np.nan_to_num((X_mat[train_end_idx:val_end_idx] - mean_tr) / std_tr, nan=0.0)
    y_val_mae = mae_long[train_end_idx:val_end_idx]

    p50_mae_model = QuantileRegressor(quantile=0.50, alpha=0.01, solver='highs')
    p50_mae_model.fit(X_tr, y_tr_mae)
    p_val_p50 = p50_mae_model.predict(X_val)
    p_conf_p50 = p50_mae_model.predict(X_conf)

    val_res = np.abs(y_val_mae - p_val_p50)
    n_val = len(y_val_mae)

    conformal_records = []
    for alpha_conf in [0.10, 0.05]:
        nominal_cov = (1.0 - alpha_conf) * 100.0
        k = int(np.ceil((n_val + 1) * (1.0 - alpha_conf)))
        k = min(n_val - 1, max(0, k - 1))
        q_val_rad = float(np.sort(val_res)[k])

        low_b = np.maximum(0.0, p_conf_p50 - q_val_rad)
        high_b = p_conf_p50 + q_val_rad

        in_int = (y_conf_mae >= low_b) & (y_conf_mae <= high_b)
        actual_cov = float(np.mean(in_int)) * 100.0
        avg_w = float(np.mean(high_b - low_b)) * 100.0

        conformal_records.append({
            "Conformal Level": f"{int(nominal_cov)}%",
            "Target Coverage %": f"{nominal_cov:.1f}%",
            "Empirical Confirmation Coverage %": round(actual_cov, 2),
            "Mean Interval Width %": round(avg_w, 3),
            "Calibration Status": "Valid Coverage (Within 3%)" if abs(actual_cov - nominal_cov) <= 3.0 else "Miscalibrated"
        })
    df_mae_conformal = pd.DataFrame(conformal_records)

    # Combined Excursion Price Envelope on Confirmation Split
    mfe_p50 = np.median(mfe_long[val_end_idx:]) * 100.0
    mae_p50 = float(np.mean(p_conf_p50)) * 100.0
    mfe_p90 = np.quantile(mfe_long[val_end_idx:], 0.90) * 100.0
    mae_p90 = float(np.mean(pred_mat[:, 4])) * 100.0

    envelope_records = [
        {"Envelope Boundary": "Expected Median Upside (MFE P50)", "Magnitude %": f"+{mfe_p50:.2f}%", "BTCUSD (Base $100k)": f"${100000 * (1 + mfe_p50/100):,.0f}"},
        {"Envelope Boundary": "Expected Median Downside (MAE P50)", "Magnitude %": f"-{mae_p50:.2f}%", "BTCUSD (Base $100k)": f"${100000 * (1 - mae_p50/100):,.0f}"},
        {"Envelope Boundary": "Tail Favorable Upside (MFE P90)", "Magnitude %": f"+{mfe_p90:.2f}%", "BTCUSD (Base $100k)": f"${100000 * (1 + mfe_p90/100):,.0f}"},
        {"Envelope Boundary": "Tail Adverse Downside (MAE P90)", "Magnitude %": f"-{mae_p90:.2f}%", "BTCUSD (Base $100k)": f"${100000 * (1 - mae_p90/100):,.0f}"}
    ]
    df_envelope = pd.DataFrame(envelope_records)

    meta = {
        "p50_mae_coverage": float(df_mae_quantiles.loc[df_mae_quantiles["Target Quantile"] == "P50 MAE"]["Empirical Confirmation Coverage %"].values[0]),
        "envelope_p50_ratio": round(float(mfe_p50 / max(1e-6, mae_p50)), 3)
    }

    return df_mae_quantiles, df_mae_conformal, df_envelope, meta
