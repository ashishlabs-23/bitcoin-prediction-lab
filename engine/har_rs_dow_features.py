"""
engine/har_rs_dow_features.py — Clean Production Feature Preparation for HAR-RS-DOW
=====================================================================================
Production runtime feature preparation for the active frozen model: HAR-RS-DOW-v1.0.

Architectural Principles:
1. Strict Runtime Independence:
   - Sourced exclusively from validated `ohlcv.parquet` (Coinbase BTC/USD hourly).
   - Zero dependence on research benchmarks (`iv7d.parquet`) or research test scripts.
2. Complete Causal Alignment:
   - Computes 10 point-in-time features strictly using past observations:
     * log_rv_down_1d: log 24-hour realized downside semivariance (annualized)
     * log_rv_up_1d: log 24-hour realized upside semivariance (annualized)
     * log_rv7d_var_ann_lag: log 168-hour trailing realized variance (annualized)
     * log_rv30d_var_ann: log 720-hour trailing realized variance (annualized)
     * dow_1..dow_6: Day-of-week binary indicator dummy columns (Tuesday to Sunday)
3. Target Alignment:
   - Computes forward 168-hour realized variance (rv7d_var_ann) for historical evaluation / calibration.
"""

import os
from typing import Optional
import numpy as np
import pandas as pd

from config import DATA_RAW_DIR

DEFAULT_OHLCV_PATH = os.path.join(DATA_RAW_DIR, "ohlcv.parquet")


def prepare_har_rs_dow_dataset(ohlcv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Loads raw OHLCV and constructs the causal dataset required for HAR-RS-DOW inference
    and C2 conformal risk envelope evaluation.
    
    Strictly independent of research-only derivatives (e.g. iv7d.parquet).
    """
    path = ohlcv_path or DEFAULT_OHLCV_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required runtime dataset missing: {path}")

    df_ohlcv = pd.read_parquet(path)
    df_ohlcv["timestamp"] = pd.to_datetime(df_ohlcv["timestamp"], utc=True)
    df_ohlcv.sort_values("timestamp", inplace=True)
    df_ohlcv.set_index("timestamp", inplace=True)
    df = df_ohlcv.copy()

    # Hourly log returns
    df["r"] = np.log(df["close"] / df["close"].shift(1))

    # Target: Forward 7-Day Realized Variance (rv7d_var_ann)
    # rv7d_var_ann(t) = (8760 / 168) * sum_{i=1}^{168} r_{t+i}^2
    sq_ret = df["r"] ** 2
    fwd_sq_ret = sq_ret.shift(-1)
    fwd_sum_sq = fwd_sq_ret.iloc[::-1].rolling(window=168, min_periods=168).sum().iloc[::-1]
    df["rv7d_var_ann"] = (8760.0 / 168.0) * fwd_sum_sq

    # Regressors: Trailing HAR-RV Realized Variances
    df["rv1d_var_ann"] = (8760.0 / 24.0) * sq_ret.rolling(24, min_periods=24).sum()
    df["rv7d_var_ann_lag"] = (8760.0 / 168.0) * sq_ret.rolling(168, min_periods=168).sum()
    df["rv30d_var_ann"] = (8760.0 / 720.0) * sq_ret.rolling(720, min_periods=720).sum()

    # HAR-RS-DOW Components (Realized Semivariance & Day of Week)
    down_sq_ret = (df["r"].clip(upper=0)) ** 2
    up_sq_ret = (df["r"].clip(lower=0)) ** 2
    df["rv_down_1d"] = (8760.0 / 24.0) * down_sq_ret.rolling(24, min_periods=24).sum()
    df["rv_up_1d"] = (8760.0 / 24.0) * up_sq_ret.rolling(24, min_periods=24).sum()
    df["dow"] = df.index.dayofweek

    # Drop warm-up rows where trailing features or targets are unobserved
    req_cols = ["rv7d_var_ann", "rv1d_var_ann", "rv7d_var_ann_lag", "rv30d_var_ann", "rv_down_1d", "rv_up_1d"]
    clean_df = df.dropna(subset=req_cols).copy()

    return clean_df


def get_har_rs_dow_features(sub_df: pd.DataFrame) -> np.ndarray:
    """
    Extracts the exact 10 point-in-time features required by har_rs_dow_v1.joblib:
    [log_rv_down, log_rv_up, log_rv7, log_rv30, dow_1..dow_6].
    """
    log_rv_down = np.log(np.maximum(1e-6, sub_df["rv_down_1d"].values))
    log_rv_up = np.log(np.maximum(1e-6, sub_df["rv_up_1d"].values))
    log_rv7 = np.log(np.maximum(1e-6, sub_df["rv7d_var_ann_lag"].values))
    log_rv30 = np.log(np.maximum(1e-6, sub_df["rv30d_var_ann"].values))

    # Explicit deterministic DOW dummy construction (Monday=0 is reference class, all zeros)
    # dow_1 = Tuesday (1), dow_2 = Wednesday (2), ..., dow_6 = Sunday (6)
    dow_vals = sub_df["dow"].values
    dow_dummies = np.zeros((len(sub_df), 6), dtype=float)
    for i in range(1, 7):
        dow_dummies[:, i - 1] = (dow_vals == i).astype(float)

    return np.column_stack([log_rv_down, log_rv_up, log_rv7, log_rv30, dow_dummies])
