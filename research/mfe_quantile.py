"""
research/mfe_quantile.py — Quantile MFE Forecasting & Conformal Prediction Engine
==================================================================================
Predicts:
1. MFE Quantiles: P10, P25, P50, P75, P90 using Quantile Loss with non-crossing monotonicity
2. Pinball loss, empirical coverage, coverage error, and interval width
3. Conformal 90% and 95% MFE prediction intervals using rolling calibration
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import QuantileRegressor
from typing import Dict, List, Tuple, Any

from research.mfe_target_audit import compute_directional_excursions


def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, q: float) -> float:
    """Computes pinball (quantile) loss for quantile q."""
    diff = y_true - y_pred
    return float(np.mean(np.maximum(q * diff, (q - 1.0) * diff)))


def evaluate_mfe_quantile_and_conformal(
    df: pd.DataFrame,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    train_end_idx: int,
    val_end_idx: int,
    quantiles: List[float] = [0.10, 0.25, 0.50, 0.75, 0.90]
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Fits quantile regressors and evaluates coverage, monotonicity, and conformal intervals on Confirmation partition.
    """
    exc = compute_directional_excursions(close, high, low, horizon_bars=24)
    mfe_long = exc["mfe_long"]

    feat_cols = [c for c in df.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    X_mat = df[feat_cols].values.astype(np.float32)

    mean_tr = np.nanmean(X_mat[:train_end_idx], axis=0, keepdims=True)
    std_tr = np.nanstd(X_mat[:train_end_idx], axis=0, keepdims=True) + 1e-6

    X_tr = np.nan_to_num((X_mat[:train_end_idx] - mean_tr) / std_tr, nan=0.0)
    X_conf = np.nan_to_num((X_mat[val_end_idx:] - mean_tr) / std_tr, nan=0.0)

    y_tr = mfe_long[:train_end_idx]
    y_conf = mfe_long[val_end_idx:]

    quantile_preds = {}
    records_q = []

    # Fit quantile regressors with pinball loss
    for q in quantiles:
        # Use QuantileRegressor (or linear proxy if large)
        qr = QuantileRegressor(quantile=q, alpha=0.01, solver='highs')
        qr.fit(X_tr, y_tr)
        p_conf = qr.predict(X_conf)
        quantile_preds[q] = p_conf

    # Enforce non-crossing monotonicity
    sorted_quantiles = sorted(quantiles)
    pred_mat = np.column_stack([quantile_preds[q] for q in sorted_quantiles])
    pred_mat = np.maximum.accumulate(pred_mat, axis=1)  # Non-crossing guarantee

    for idx, q in enumerate(sorted_quantiles):
        p_q = pred_mat[:, idx]
        emp_cov = float(np.mean(y_conf <= p_q)) * 100.0
        cov_err = float(emp_cov - (q * 100.0))
        ploss = pinball_loss(y_conf, p_q, q) * 100.0

        records_q.append({
            "Target Quantile": f"P{int(q*100)} MFE",
            "Nominal Quantile %": f"{int(q*100)}%",
            "Empirical Confirmation Coverage %": round(emp_cov, 2),
            "Coverage Error %": round(cov_err, 2),
            "Pinball Loss (x100)": round(ploss, 4),
            "Mean Predicted MFE %": round(float(np.mean(p_q)) * 100.0, 3)
        })

    df_quantiles = pd.DataFrame(records_q)

    # Conformal Prediction Intervals (90% and 95%)
    # Calibration on Validation partition
    X_val = np.nan_to_num((X_mat[train_end_idx:val_end_idx] - mean_tr) / std_tr, nan=0.0)
    y_val = mfe_long[train_end_idx:val_end_idx]

    p50_model = QuantileRegressor(quantile=0.50, alpha=0.01, solver='highs')
    p50_model.fit(X_tr, y_tr)
    p_val_p50 = p50_model.predict(X_val)
    p_conf_p50 = p50_model.predict(X_conf)

    val_residuals = np.abs(y_val - p_val_p50)
    n_val = len(y_val)

    conformal_records = []
    for alpha_conf in [0.10, 0.05]:
        nominal_cov = (1.0 - alpha_conf) * 100.0
        k = int(np.ceil((n_val + 1) * (1.0 - alpha_conf)))
        k = min(n_val - 1, max(0, k - 1))
        q_val_radius = float(np.sort(val_residuals)[k])

        lower_bound = np.maximum(0.0, p_conf_p50 - q_val_radius)
        upper_bound = p_conf_p50 + q_val_radius

        in_interval = (y_conf >= lower_bound) & (y_conf <= upper_bound)
        actual_cov = float(np.mean(in_interval)) * 100.0
        avg_width = float(np.mean(upper_bound - lower_bound)) * 100.0

        conformal_records.append({
            "Conformal Confidence Level": f"{int(nominal_cov)}%",
            "Target Coverage %": f"{nominal_cov:.1f}%",
            "Empirical Confirmation Coverage %": round(actual_cov, 2),
            "Mean Interval Width %": round(avg_width, 3),
            "Calibration Status": "Valid Coverage (Within 3%)" if abs(actual_cov - nominal_cov) <= 3.0 else "Miscalibrated"
        })

    df_conformal = pd.DataFrame(conformal_records)

    meta = {
        "p50_empirical_coverage": float(df_quantiles.loc[df_quantiles["Target Quantile"] == "P50 MFE"]["Empirical Confirmation Coverage %"].values[0]),
        "is_monotonic": bool((np.diff(pred_mat, axis=1) >= 0).all()),
        "conformal_90_coverage": float(df_conformal.iloc[0]["Empirical Confirmation Coverage %"])
    }

    return df_quantiles, df_conformal, meta
