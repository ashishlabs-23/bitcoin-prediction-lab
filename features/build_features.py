"""
Feature Engineering Module for bitcoin-prediction-lab.

Computes technical indicators and derivatives features, then merges them onto
the primary timestamp grid using pd.merge_asof matching on available_time
to strictly prevent lookahead bias.
"""

import os
import sys
from typing import Dict
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_RAW_DIR, DATA_PROCESSED_DIR


def load_raw() -> Dict[str, pd.DataFrame]:
    """
    Loads the three parquet files from DATA_RAW_DIR, returns
    {'ohlcv': df, 'funding': df, 'oi': df}. If funding/oi are empty, still
    return them as empty DataFrames — downstream code must handle this.
    """
    raw_data = {}
    for name in ['ohlcv', 'funding', 'oi']:
        path = os.path.join(DATA_RAW_DIR, f"{name}.parquet")
        if os.path.exists(path):
            try:
                raw_data[name] = pd.read_parquet(path, engine='pyarrow')
            except Exception as e:
                print(f"Warning: Failed to read {path}: {e}")
                raw_data[name] = pd.DataFrame()
        else:
            raw_data[name] = pd.DataFrame()
    return raw_data


def compute_technical_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Input: the ohlcv DataFrame from load_raw.
    Adds these columns to a copy of ohlcv (keep 'timestamp' and
    'available_time' unchanged):
      - ret_1h, ret_4h, ret_24h: log returns over 1/4/24 bars
      - rsi_14: 14-period RSI
      - macd, macd_signal: standard MACD(12,26,9)
      - sma_ratio_20, sma_ratio_50: close / SMA(20 or 50) - 1  (ratio, NOT raw SMA level)
      - realized_vol_24h: rolling 24-bar std of ret_1h
      - volume_zscore_24h: rolling 24-bar z-score of volume

    Every feature here is derived using ONLY data at or before each row's own
    timestamp (backward-looking rolling windows/shifts). No centered or
    future-looking windows are used, ensuring no lookahead leakage.

    Returns the extended DataFrame, still with 'available_time' correct — note
    that if a feature uses a rolling window, its available_time equals the
    underlying candle's available_time (the window itself isn't a new leak
    since it only looks backward).
    """
    if ohlcv.empty:
        return ohlcv.copy()

    df = ohlcv.copy()
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Log returns
    df['ret_1h'] = np.log(df['close'] / df['close'].shift(1))
    df['ret_4h'] = np.log(df['close'] / df['close'].shift(4))
    df['ret_24h'] = np.log(df['close'] / df['close'].shift(24))

    # 14-period RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['rsi_14'] = 100.0 - (100.0 / (1.0 + rs))

    # Standard MACD(12, 26, 9)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

    # SMA ratios: close / SMA(20 or 50) - 1
    sma20 = df['close'].rolling(window=20).mean()
    sma50 = df['close'].rolling(window=50).mean()
    df['sma_ratio_20'] = (df['close'] / sma20) - 1.0
    df['sma_ratio_50'] = (df['close'] / sma50) - 1.0

    # Realized volatility & Volume Z-score
    df['realized_vol_24h'] = df['ret_1h'].rolling(window=24).std()
    vol_mean = df['volume'].rolling(window=24).mean()
    vol_std = df['volume'].rolling(window=24).std()
    df['volume_zscore_24h'] = (df['volume'] - vol_mean) / vol_std

    # ATR-14 (Average True Range over 14 bars)
    # Required by genome.fitness — tp_atr_mult and sl_atr_mult scale ATR to set TP/SL prices.
    # True Range = max(high-low, |high-prev_close|, |low-prev_close|)
    # Backward-looking only — no lookahead. Uses Wilder's EWM (alpha=1/14).
    if all(c in df.columns for c in ['high', 'low', 'close']):
        prev_close = df['close'].shift(1)
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - prev_close).abs(),
            (df['low'] - prev_close).abs(),
        ], axis=1).max(axis=1)
        df['atr_14'] = tr.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
    else:
        # Fallback if high/low absent (should not happen with standard OHLCV)
        df['atr_14'] = df['realized_vol_24h'] * df['close']

    return df


def compute_derivatives_features(funding: pd.DataFrame, oi: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a DataFrame keyed by timestamp with columns:
      funding_rate, funding_rate_change_24h, open_interest, oi_pct_change_24h,
      available_time
    If funding or oi input is empty, return an empty DataFrame with these
    columns (don't crash) — the merge step must handle a missing source.
    """
    cols = ['timestamp', 'funding_rate', 'funding_rate_change_24h', 'open_interest', 'oi_pct_change_24h', 'available_time']

    if funding.empty and oi.empty:
        return pd.DataFrame(columns=cols)

    f_df = pd.DataFrame()
    if not funding.empty and 'funding_rate' in funding.columns:
        f_df = funding.sort_values('timestamp').copy()
        # Binance funding rate settlements occur every 8h -> 3 bars = 24h
        f_df['funding_rate_change_24h'] = f_df['funding_rate'].diff(3)

    oi_df = pd.DataFrame()
    if not oi.empty and 'open_interest' in oi.columns:
        oi_df = oi.sort_values('timestamp').copy()
        # 1h open interest bars -> 24 bars = 24h
        oi_df['oi_pct_change_24h'] = oi_df['open_interest'].pct_change(24)

    if not f_df.empty and not oi_df.empty:
        f_df['available_time'] = pd.to_datetime(f_df['available_time'], utc=True).dt.as_unit('ns')
        oi_df['available_time'] = pd.to_datetime(oi_df['available_time'], utc=True).dt.as_unit('ns')
        oi_subset = oi_df.drop(columns=['timestamp'], errors='ignore')
        res = pd.merge_asof(f_df, oi_subset, on='available_time', direction='backward')
    elif not f_df.empty:
        res = f_df.copy()
        res['open_interest'] = np.nan
        res['oi_pct_change_24h'] = np.nan
    else:
        res = oi_df.copy()
        res['funding_rate'] = np.nan
        res['funding_rate_change_24h'] = np.nan

    for c in cols:
        if c not in res.columns:
            res[c] = np.nan

    return res[cols]


from data.ingest_microstructure import compute_microstructure_features


def merge_features(technical: pd.DataFrame, derivatives: pd.DataFrame, microstructure: pd.DataFrame = None) -> pd.DataFrame:
    """
    Merges technical, derivatives, and microstructure features onto the technical DataFrame's
    timestamp grid using pd.merge_asof with direction='backward', matching on
    `available_time` (not `timestamp`) to enforce the no-lookahead rule from
    config.py's conventions.
    """
    if technical.empty:
        return technical.copy()

    merged = technical.copy()

    if derivatives is not None and not derivatives.empty:
        merged['available_time'] = pd.to_datetime(merged['available_time'], utc=True).dt.as_unit('ns')
        deriv_df = derivatives.copy()
        deriv_df['available_time'] = pd.to_datetime(deriv_df['available_time'], utc=True).dt.as_unit('ns')

        deriv_cols = [c for c in deriv_df.columns if c != 'timestamp']
        deriv_subset = deriv_df[deriv_cols]

        merged = merged.sort_values('available_time').reset_index(drop=True)
        deriv_subset = deriv_subset.sort_values('available_time').reset_index(drop=True)
        merged = pd.merge_asof(merged, deriv_subset, on='available_time', direction='backward')

    if microstructure is not None and not microstructure.empty:
        merged['available_time'] = pd.to_datetime(merged['available_time'], utc=True).dt.as_unit('ns')
        micro_df = microstructure.copy()
        micro_df['available_time'] = pd.to_datetime(micro_df['available_time'], utc=True).dt.as_unit('ns')

        micro_cols = [c for c in micro_df.columns if c != 'timestamp']
        micro_subset = micro_df[micro_cols]

        merged = merged.sort_values('available_time').reset_index(drop=True)
        micro_subset = micro_subset.sort_values('available_time').reset_index(drop=True)
        merged = pd.merge_asof(merged, micro_subset, on='available_time', direction='backward')

    # Drop any feature column that is entirely NaN
    all_nan_cols = [c for c in merged.columns if merged[c].isna().all()]
    if all_nan_cols:
        print(f"Warning: Dropping columns with 100% missing values: {all_nan_cols}")
        merged = merged.drop(columns=all_nan_cols)

    initial_len = len(merged)
    final_df = merged.dropna().reset_index(drop=True)
    warmup_dropped = initial_len - len(final_df)
    print(f"Dropped {warmup_dropped} warmup rows with NaNs at start.")

    return final_df


if __name__ == "__main__":
    print("Loading raw datasets...")
    raw = load_raw()
    for name, df in raw.items():
        print(f"  {name}: {df.shape}")

    tech = compute_technical_features(raw['ohlcv'])
    deriv = compute_derivatives_features(raw['funding'], raw['oi'])
    micro = compute_microstructure_features(raw['ohlcv'])
    final_features = merge_features(tech, deriv, micro)

    os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
    out_path = os.path.join(DATA_PROCESSED_DIR, "features.parquet")
    final_features.to_parquet(out_path, engine="pyarrow")
    print(f"Saved feature matrix to {out_path}")

    print(f"Final shape: {final_features.shape}")
    print("\nData types:")
    print(final_features.dtypes)

    non_ts_cols = [c for c in final_features.columns if c not in ['timestamp', 'available_time']]
    has_nans = final_features[non_ts_cols].isna().any().any()

    if not has_nans and len(final_features) > 0:
        print("\nPASS: No NaNs remain in non-timestamp columns and shape > 0.")
    else:
        print("\nFAIL: Feature engineering smoke checks failed.")

