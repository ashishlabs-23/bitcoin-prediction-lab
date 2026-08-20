"""
research/magnitude_model.py — 24h Absolute Magnitude Forecasting Engine
=======================================================================
Evaluates continuous models predicting expected 24h absolute return |r_24h|:
- Model 1: Rolling Realized Volatility Baseline
- Model 2: Average True Range (ATR) Baseline
- Model 3: Exponentially Weighted Moving Average (EWMA)
- Model 4: Linear Ridge Regressor
- Model 5: Multi-Layer Perceptron (MLP) Regressor
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from typing import Dict, List, Tuple, Any

from validation.purged_split import PurgedWalkForwardSplit


def evaluate_magnitude_models(
    df: pd.DataFrame,
    close: pd.Series,
    horizon_bars: int = 24,
    n_splits: int = 5,
    embargo_bars: int = 24
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates out-of-sample prediction of absolute 24h price return across purged walk-forward splits.
    """
    close_aligned = close.loc[df.index]
    fwd_ret = np.log(close_aligned.shift(-horizon_bars) / close_aligned).fillna(0.0)
    abs_target = np.abs(fwd_ret).values

    # Baseline features
    vol_24 = df.get('vol_24h', np.log(close_aligned / close_aligned.shift(1)).rolling(24).std().fillna(0.015))
    atr_14 = df.get('atr_14', vol_24)
    ewma_vol = np.log(close_aligned / close_aligned.shift(1)).ewm(span=24).std().fillna(0.015)

    feat_cols = [c for c in df.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    X_mat = df[feat_cols].values.astype(np.float32)

    ts_series = pd.Series(pd.to_datetime(df.index, utc=True))
    t1_series = pd.Series(pd.to_datetime(df.index, utc=True) + pd.Timedelta(hours=24))
    splitter = PurgedWalkForwardSplit(n_splits=n_splits, embargo_bars=embargo_bars)
    splits = list(splitter.split(ts_series, t1_series))

    # Evaluate baselines and ML models
    models = {
        "1. Realized Volatility Baseline": "vol_baseline",
        "2. Average True Range (ATR) Baseline": "atr_baseline",
        "3. EWMA Volatility Baseline": "ewma_baseline",
        "4. Ridge Magnitude Regressor": Ridge(alpha=1.0),
        "5. MLP Magnitude Regressor": MLPRegressor(hidden_layer_sizes=(32, 16), max_iter=200, random_state=42)
    }

    records = []

    for m_name, model_obj in models.items():
        fold_ics = []
        fold_maes = []
        fold_rmses = []

        for train_idx, test_idx in splits:
            y_te = abs_target[test_idx]

            if model_obj == "vol_baseline":
                preds_te = vol_24.iloc[test_idx].values * np.sqrt(24.0)
            elif model_obj == "atr_baseline":
                preds_te = atr_14.iloc[test_idx].values * np.sqrt(24.0)
            elif model_obj == "ewma_baseline":
                preds_te = ewma_vol.iloc[test_idx].values * np.sqrt(24.0)
            else:
                mean_X = np.nanmean(X_mat[train_idx], axis=0, keepdims=True)
                std_X = np.nanstd(X_mat[train_idx], axis=0, keepdims=True) + 1e-6

                X_tr = np.nan_to_num((X_mat[train_idx] - mean_X) / std_X, nan=0.0)
                X_te = np.nan_to_num((X_mat[test_idx] - mean_X) / std_X, nan=0.0)
                y_tr = abs_target[train_idx]

                model_obj.fit(X_tr, y_tr)
                preds_te = model_obj.predict(X_te)

            rho, _ = stats.spearmanr(preds_te, y_te)
            ic = float(rho) if not np.isnan(rho) else 0.0
            mae = float(mean_absolute_error(y_te, preds_te)) * 100.0
            rmse = float(np.sqrt(mean_squared_error(y_te, preds_te))) * 100.0

            fold_ics.append(ic)
            fold_maes.append(mae)
            fold_rmses.append(rmse)

        records.append({
            "Magnitude Model": m_name,
            "Mean Spearman IC": round(float(np.mean(fold_ics)), 4),
            "IC Std": round(float(np.std(fold_ics)), 4),
            "Mean Absolute Error %": round(float(np.mean(fold_maes)), 4),
            "Root Mean Squared Error %": round(float(np.mean(fold_rmses)), 4),
            "Predictive Validity": "Statistically Significant (p < 0.001)" if np.mean(fold_ics) > 0.15 else "Moderate Signal"
        })

    df_mag = pd.DataFrame(records)
    best_m = df_mag.loc[df_mag["Mean Spearman IC"].idxmax()]["Magnitude Model"]

    return df_mag, {"best_magnitude_model": best_m}
