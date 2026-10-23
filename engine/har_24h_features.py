"""
engine/har_24h_features.py — Clean Causal 24-Hour Realized Variance Feature & Target Engine
==========================================================================================
Implements the 24-hour realized variance target and feature contracts for:
1. Conventional HAR-24H benchmark (OLS).
2. QLIKE-coherent HAR-24H challenger (Puke & Schweikert, 2026).
3. Persistence and rolling-mean volatility benchmarks.

Target Specification (Strictly Causal & Non-Overlapping Daily Slices):
- Target Name: `rv24h_var_ann`
- Horizon: Exactly 24 hours (24 future 1-hour candles: t+1 .. t+24)
- Sampling Frequency: Hourly-sampled realized variance proxy from 24 closed hourly log returns
- Formula:
    r_{t+j} = ln(Close_{t+j} / Close_{t+j-1}),  j = 1..24
    RV_{t, t+24h} = sum_{j=1}^{24} r_{t+j}^2
    rv24h_var_ann_t = (8760.0 / 24.0) * RV_{t, t+24h} = 365.0 * sum_{j=1}^{24} r_{t+j}^2
- Units: Annualized variance in decimal (e.g. 0.25 = 25% annualized variance)
- Causal Invariant:
    feature_available_at <= forecast_issue_time (t)
    Target outcomes utilize exclusively candles from t+1 to t+24. Zero future leakage.
"""

import os
from typing import Optional, Tuple, Union
import numpy as np
import pandas as pd

from config import DATA_RAW_DIR

DEFAULT_OHLCV_PATH = os.path.join(DATA_RAW_DIR, "ohlcv.parquet")


def calculate_hourly_log_returns(series: pd.Series) -> pd.Series:
    """Calculates 1-hour log returns: r_t = ln(close_t / close_{t-1})."""
    return np.log(series / series.shift(1))


def compute_trailing_realized_variance(
    squared_returns: pd.Series, window_hours: int, annualize_factor: float = 8760.0
) -> pd.Series:
    """
    Computes trailing realized variance over a given window in hours:
    RV = (annualize_factor / window_hours) * sum(r^2)
    """
    scale = annualize_factor / float(window_hours)
    return scale * squared_returns.rolling(window=window_hours, min_periods=window_hours).sum()


def prepare_har_24h_dataset(
    ohlcv_source: Optional[Union[str, pd.DataFrame]] = None,
    dropna: bool = True
) -> pd.DataFrame:
    """
    Constructs the causal dataset for 24-hour forward realized variance forecasting.
    Includes forward 24h target and strictly lagged point-in-time HAR features.
    Accepts either a parquet path string or a pandas DataFrame.
    """
    if isinstance(ohlcv_source, pd.DataFrame):
        df_ohlcv = ohlcv_source.copy()
        if "timestamp" in df_ohlcv.columns:
            df_ohlcv["timestamp"] = pd.to_datetime(df_ohlcv["timestamp"], utc=True)
            df_ohlcv.sort_values("timestamp", inplace=True)
            df_ohlcv.set_index("timestamp", inplace=True)
        elif not isinstance(df_ohlcv.index, pd.DatetimeIndex):
            df_ohlcv.index = pd.to_datetime(df_ohlcv.index, utc=True)
        df = df_ohlcv.copy()
    else:
        path = ohlcv_source or DEFAULT_OHLCV_PATH
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required OHLCV dataset missing: {path}")

        df_ohlcv = pd.read_parquet(path)
        df_ohlcv["timestamp"] = pd.to_datetime(df_ohlcv["timestamp"], utc=True)
        df_ohlcv.sort_values("timestamp", inplace=True)
        df_ohlcv.set_index("timestamp", inplace=True)
        df = df_ohlcv.copy()

    # 1. Hourly log returns
    df["r"] = calculate_hourly_log_returns(df["close"])

    # 2. Target: Forward 24-Hour Realized Variance (rv24h_var_ann)
    # Sum of future squared returns from t+1 to t+24, scaled to annual basis (8760 / 24 = 365)
    sq_ret = df["r"] ** 2
    fwd_sq_ret = sq_ret.shift(-1)
    fwd_sum_sq_24 = fwd_sq_ret.iloc[::-1].rolling(window=24, min_periods=24).sum().iloc[::-1]
    df["rv24h_var_ann"] = (8760.0 / 24.0) * fwd_sum_sq_24

    # 3. Trailing Predictors (Strictly Lagged as of timestamp t)
    # Daily, weekly, monthly realized variances (annualized)
    df["rv1d_var_ann"] = (8760.0 / 24.0) * sq_ret.rolling(24, min_periods=24).sum()
    df["rv7d_var_ann_lag"] = (8760.0 / 168.0) * sq_ret.rolling(168, min_periods=168).sum()
    df["rv30d_var_ann"] = (8760.0 / 720.0) * sq_ret.rolling(720, min_periods=720).sum()

    # Realized semivariances (downside and upside daily components)
    down_sq_ret = (df["r"].clip(upper=0)) ** 2
    up_sq_ret = (df["r"].clip(lower=0)) ** 2
    df["rv_down_1d"] = (8760.0 / 24.0) * down_sq_ret.rolling(24, min_periods=24).sum()
    df["rv_up_1d"] = (8760.0 / 24.0) * up_sq_ret.rolling(24, min_periods=24).sum()

    # Day of week (0=Monday, 6=Sunday)
    df["dow"] = df.index.dayofweek
    df["hour"] = df.index.hour

    if not dropna:
        return df

    # Drop warm-up periods where features or targets are unobserved
    req_cols = [
        "rv24h_var_ann", "rv1d_var_ann", "rv7d_var_ann_lag",
        "rv30d_var_ann", "rv_down_1d", "rv_up_1d"
    ]
    clean_df = df.dropna(subset=req_cols).copy()
    return clean_df


def get_har_24h_feature_matrix(sub_df: pd.DataFrame) -> Tuple[np.ndarray, list]:
    """
    Extracts the point-in-time feature matrix for 24H HAR models:
    [log_rv_down_1d, log_rv_up_1d, log_rv1d, log_rv7d, log_rv30d, dow_1..dow_6].
    """
    log_rv_down = np.log(np.maximum(1e-6, sub_df["rv_down_1d"].values))
    log_rv_up = np.log(np.maximum(1e-6, sub_df["rv_up_1d"].values))
    log_rv1 = np.log(np.maximum(1e-6, sub_df["rv1d_var_ann"].values))
    log_rv7 = np.log(np.maximum(1e-6, sub_df["rv7d_var_ann_lag"].values))
    log_rv30 = np.log(np.maximum(1e-6, sub_df["rv30d_var_ann"].values))

    dow_vals = sub_df["dow"].values
    dow_dummies = np.zeros((len(sub_df), 6), dtype=float)
    for i in range(1, 7):
        dow_dummies[:, i - 1] = (dow_vals == i).astype(float)

    feature_names = [
        "log_rv_down_1d", "log_rv_up_1d", "log_rv1d", "log_rv7d", "log_rv30d",
        "dow_1", "dow_2", "dow_3", "dow_4", "dow_5", "dow_6"
    ]
    X = np.column_stack([log_rv_down, log_rv_up, log_rv1, log_rv7, log_rv30, dow_dummies])
    return X, feature_names


def get_daily_non_overlapping_slice(df: pd.DataFrame, origin_hour: int = 0) -> pd.DataFrame:
    """
    Filters the dataset to a single forecast origin per UTC day (default 00:00 UTC).
    Because the target is 24 hours, daily origins at hour 0 do NOT mechanically overlap.
    """
    return df[df["hour"] == origin_hour].copy()
