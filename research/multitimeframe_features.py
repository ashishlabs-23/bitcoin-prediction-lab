"""
research/multitimeframe_features.py — Point-in-Time Multi-Timeframe Feature Engine
==================================================================================
Computes point-in-time multi-timeframe technical, volatility, and trend features:
Timeframes: 1m, 5m, 15m, 1h, 4h, 12h, 1d

Invariants:
- A feature computed at timestamp t uses only data available strictly at or before t.
- Higher timeframe bars are aligned backward (e.g., 4h bar closes at t only include past 4h).
- Zero future lookahead.
"""

import os
import sys
import logging
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_RAW_DIR
from features.build_features import load_raw

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MultiTimeframeFeatures")


def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Computes standard Wilder RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-8)
    return 100.0 - (100.0 / (1.0 + rs))


def compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Computes Average Directional Index (ADX)."""
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    plus_di = 100.0 * (pd.Series(plus_dm, index=high.index).ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean() / (atr + 1e-8))
    minus_di = 100.0 * (pd.Series(minus_dm, index=high.index).ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean() / (atr + 1e-8))

    dx = 100.0 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-8))
    adx = dx.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    return adx.fillna(25.0)


def build_multitimeframe_features(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """
    Builds aligned point-in-time multi-timeframe features from hourly OHLCV:
    - 1h baseline features
    - 4h resampled features (backward-looking rolling 4-bar window)
    - 12h resampled features (backward-looking rolling 12-bar window)
    - 1d resampled features (backward-looking rolling 24-bar window)
    """
    df = df_hourly.copy()
    close = df['close']
    high = df['high']
    low = df['low']
    vol = df['volume']

    features = pd.DataFrame(index=df.index)

    # 1. 1-Hour Timeframe Features
    features['mtf_1h_ret'] = np.log(close / close.shift(1))
    features['mtf_1h_vol'] = features['mtf_1h_ret'].rolling(24).std()
    features['mtf_1h_rsi'] = compute_rsi(close, window=14)
    features['mtf_1h_ema_slope'] = (close.ewm(span=20).mean() / close.ewm(span=20).mean().shift(3)) - 1.0

    # 2. 4-Hour Timeframe (Rolling 4-bar window)
    close_4h = close
    high_4h = high.rolling(4).max()
    low_4h = low.rolling(4).min()
    vol_4h = vol.rolling(4).sum()
    
    features['mtf_4h_ret'] = np.log(close / close.shift(4))
    features['mtf_4h_vol'] = features['mtf_4h_ret'].rolling(6).std()
    features['mtf_4h_rsi'] = compute_rsi(close, window=56)  # 14 * 4
    features['mtf_4h_adx'] = compute_adx(high_4h, low_4h, close_4h, window=14)
    features['mtf_4h_vol_z'] = (vol_4h - vol_4h.rolling(24).mean()) / (vol_4h.rolling(24).std() + 1e-6)

    # 3. 12-Hour Timeframe (Rolling 12-bar window)
    high_12h = high.rolling(12).max()
    low_12h = low.rolling(12).min()
    vol_12h = vol.rolling(12).sum()

    features['mtf_12h_ret'] = np.log(close / close.shift(12))
    features['mtf_12h_vol'] = features['mtf_12h_ret'].rolling(10).std()
    features['mtf_12h_rsi'] = compute_rsi(close, window=168)  # 14 * 12
    features['mtf_12h_trend_state'] = np.where(close > close.ewm(span=120).mean(), 1.0, -1.0)

    # 4. 1-Day (24-Hour) Timeframe (Rolling 24-bar window)
    features['mtf_1d_ret'] = np.log(close / close.shift(24))
    features['mtf_1d_vol'] = features['mtf_1d_ret'].rolling(14).std()
    features['mtf_1d_sma_ratio_50'] = (close / close.rolling(24 * 50, min_periods=200).mean()) - 1.0
    features['mtf_1d_vol_ratio'] = vol.rolling(24).sum() / (vol.rolling(24 * 20, min_periods=48).mean() + 1e-6)

    return features.ffill().fillna(0.0)


if __name__ == "__main__":
    raw = load_raw()
    ohlcv = raw['ohlcv']
    mtf = build_multitimeframe_features(ohlcv)
    print(f"Generated {mtf.shape[1]} Multi-Timeframe Features across {len(mtf)} rows:")
    print(mtf.tail(3))
