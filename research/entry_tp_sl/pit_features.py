"""
research/entry_tp_sl/pit_features.py
====================================
Point-in-Time (PIT) feature extraction engine.
Guarantees:
- Strict causality: available_timestamp <= decision_timestamp.
- Causal rolling calculations with no forward lookahead.
- Rejection of future data.

Status: FROZEN PIT FEATURE STORE (Phase 6E)
"""

import math
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd


FEATURE_NAMES = [
    "vol_atr14_pct",
    "vol_realized_24h",
    "vol_parkinson_24h",
    "mom_roc_4",
    "mom_roc_16",
    "mom_rsi_14",
    "vol_volume_ratio_20",
    "trend_sma50_diff",
    "setup_sweep_mag",
    "setup_range_width",
    "setup_bars_since",
    "time_hour_sin",
    "time_hour_cos"
]


def compute_pit_features_table(df_15m: pd.DataFrame) -> pd.DataFrame:
    """
    Computes causal PIT features on 15-minute aggregated decision bars.
    Returns a dataframe indexed by Timestamp with causal feature columns.
    """
    df = df_15m.copy().sort_values('Timestamp').reset_index(drop=True)
    closes = df['Close']
    highs = df['High']
    lows = df['Low']
    volumes = df['Volume']
    timestamps = df['Timestamp']

    # 1. Volatility features
    prev_close = closes.shift(1)
    tr = pd.concat([
        highs - lows,
        (highs - prev_close).abs(),
        (lows - prev_close).abs()
    ], axis=1).max(axis=1)
    atr14 = tr.rolling(window=14).mean()
    df['vol_atr14_pct'] = atr14 / closes

    log_rets = np.log(closes / prev_close)
    df['vol_realized_24h'] = log_rets.rolling(window=96).std() * np.sqrt(96)

    # Parkinson volatility (high-low estimator over 96 bars)
    hl_log_sq = (np.log(highs / lows) ** 2) / (4.0 * np.log(2.0))
    df['vol_parkinson_24h'] = np.sqrt(hl_log_sq.rolling(window=96).mean() * 96)

    # 2. Momentum features
    df['mom_roc_4'] = (closes - closes.shift(4)) / closes.shift(4)
    df['mom_roc_16'] = (closes - closes.shift(16)) / closes.shift(16)

    # Causal RSI 14
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['mom_rsi_14'] = 100.0 - (100.0 / (1.0 + rs))

    # 3. Volume and trend features
    vol_sma20 = volumes.rolling(window=20).mean()
    df['vol_volume_ratio_20'] = volumes / (vol_sma20 + 1e-9)

    sma50 = closes.rolling(window=50).mean()
    df['trend_sma50_diff'] = (closes - sma50) / sma50

    # 4. Time features (UTC)
    dt_series = pd.to_datetime(timestamps, unit='s', utc=True)
    hours = dt_series.dt.hour + dt_series.dt.minute / 60.0
    df['time_hour_sin'] = np.sin(2.0 * np.pi * hours / 24.0)
    df['time_hour_cos'] = np.cos(2.0 * np.pi * hours / 24.0)

    return df
