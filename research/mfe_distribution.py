"""
research/mfe_distribution.py — Probabilistic MFE Distribution & Uncertainty Engine
==================================================================================
Builds a continuous probabilistic MFE forecasting model:
- Quantile Forecasts: P10, P25, P50, P75, P90
- Expected (Mean) MFE
- Prediction Interval Width (P90 - P10)
- Uncertainty Score (Dispersion / Expected Value)
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import QuantileRegressor, Ridge
from typing import Dict, List, Tuple, Any

from research.mfe_target_audit import compute_directional_excursions


def generate_probabilistic_mfe_distribution(
    df: pd.DataFrame,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    train_end_idx: int,
    val_end_idx: int,
    quantiles: List[float] = [0.10, 0.25, 0.50, 0.75, 0.90]
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Generates calibrated probabilistic MFE quantiles and forecast uncertainty statistics on Confirmation partition.
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
    for q in quantiles:
        qr = QuantileRegressor(quantile=q, alpha=0.01, solver='highs')
        qr.fit(X_tr, y_tr)
        quantile_preds[q] = qr.predict(X_conf)

    sorted_q = sorted(quantiles)
    pred_mat = np.column_stack([quantile_preds[q] for q in sorted_q])
    pred_mat = np.maximum.accumulate(pred_mat, axis=1)  # Enforce non-crossing monotonicity

    reg_mean = Ridge(alpha=1.0)
    reg_mean.fit(X_tr, y_tr)
    exp_mfe = np.maximum(0.0, reg_mean.predict(X_conf))

    interval_width = pred_mat[:, 4] - pred_mat[:, 0]  # P90 - P10
    uncertainty_score = interval_width / (exp_mfe + 1e-6)

    # Summary Statistics Table
    summary_records = [
        {"Forecast Metric": "P10 MFE (Lower Quantile)", "Mean Value %": f"+{np.mean(pred_mat[:, 0])*100.0:.2f}%", "Median Value %": f"+{np.median(pred_mat[:, 0])*100.0:.2f}%", "Description": "10th percentile conservative favorable excursion"},
        {"Forecast Metric": "P25 MFE (Lower Quartile)", "Mean Value %": f"+{np.mean(pred_mat[:, 1])*100.0:.2f}%", "Median Value %": f"+{np.median(pred_mat[:, 1])*100.0:.2f}%", "Description": "25th percentile favorable excursion"},
        {"Forecast Metric": "P50 MFE (Median Forecast)", "Mean Value %": f"+{np.mean(pred_mat[:, 2])*100.0:.2f}%", "Median Value %": f"+{np.median(pred_mat[:, 2])*100.0:.2f}%", "Description": "Central median expected favorable excursion"},
        {"Forecast Metric": "P75 MFE (Upper Quartile)", "Mean Value %": f"+{np.mean(pred_mat[:, 3])*100.0:.2f}%", "Median Value %": f"+{np.median(pred_mat[:, 3])*100.0:.2f}%", "Description": "75th percentile favorable excursion"},
        {"Forecast Metric": "P90 MFE (Tail Upside)", "Mean Value %": f"+{np.mean(pred_mat[:, 4])*100.0:.2f}%", "Median Value %": f"+{np.median(pred_mat[:, 4])*100.0:.2f}%", "Description": "90th percentile tail favorable excursion"},
        {"Forecast Metric": "Expected (Mean) MFE", "Mean Value %": f"+{np.mean(exp_mfe)*100.0:.2f}%", "Median Value %": f"+{np.median(exp_mfe)*100.0:.2f}%", "Description": "Point regression expectation"},
        {"Forecast Metric": "80% Prediction Interval Width", "Mean Value %": f"{np.mean(interval_width)*100.0:.2f}%", "Median Value %": f"{np.median(interval_width)*100.0:.2f}%", "Description": "P90 - P10 range dispersion"},
        {"Forecast Metric": "Uncertainty Ratio", "Mean Value %": f"{np.mean(uncertainty_score):.2f}x", "Median Value %": f"{np.median(uncertainty_score):.2f}x", "Description": "Interval width relative to expected move"}
    ]
    df_summary = pd.DataFrame(summary_records)

    # Time series sample output for reports / UI
    df_conf_slice = df.iloc[val_end_idx:].copy()
    df_forecasts = pd.DataFrame({
        "close": close.iloc[val_end_idx:].values,
        "exp_mfe": exp_mfe,
        "p10_mfe": pred_mat[:, 0],
        "p25_mfe": pred_mat[:, 1],
        "p50_mfe": pred_mat[:, 2],
        "p75_mfe": pred_mat[:, 3],
        "p90_mfe": pred_mat[:, 4],
        "interval_width": interval_width,
        "uncertainty_score": uncertainty_score,
        "actual_mfe": y_conf
    }, index=df_conf_slice.index)

    meta = {
        "mean_expected_mfe": round(float(np.mean(exp_mfe)) * 100.0, 3),
        "mean_interval_width": round(float(np.mean(interval_width)) * 100.0, 3),
        "mean_uncertainty_score": round(float(np.mean(uncertainty_score)), 3)
    }

    return df_summary, df_forecasts, meta
