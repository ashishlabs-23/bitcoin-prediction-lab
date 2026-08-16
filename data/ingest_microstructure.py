"""
Microstructure Data Ingestion & Feature Extraction Module for bitcoin-prediction-lab.

Computes L2 Order Book Imbalance (OBI), Bid-Ask Spread Dynamics, Order Flow Toxicity (VPIN),
and Taker Buy/Sell Aggressor Flow features.
"""

import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_RAW_DIR, DATA_PROCESSED_DIR


def compute_microstructure_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Computes synthetic/estimated or raw microstructure features from OHLCV and trade tick proxies:
    - order_book_imbalance (OBI): proxy based on high/low intraday pressure & volume
    - bid_ask_spread_pct: Corwin-Schultz (2012) spread estimator from High/Low prices
    - taker_buy_ratio: estimated aggressor buy volume ratio
    - vpin: Volume-Synchronized Probability of Toxicity
    """
    if ohlcv.empty:
        return pd.DataFrame(columns=['timestamp', 'available_time', 'order_book_imbalance', 'bid_ask_spread_pct', 'taker_buy_ratio', 'vpin'])

    df = ohlcv.copy().sort_values('timestamp').reset_index(drop=True)

    # 1. Corwin-Schultz Bid-Ask Spread Estimator (High-Low volatility estimator)
    high_low_ratio = np.log(df['high'] / df['low'])
    beta = high_low_ratio.rolling(2, min_periods=1).sum()**2
    gamma = (np.log(df['high'].rolling(2, min_periods=1).max() / df['low'].rolling(2, min_periods=1).min()))**2
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / (3 - 2 * np.sqrt(2)) - np.sqrt(gamma / (3 - 2 * np.sqrt(2)))
    alpha = np.maximum(0, alpha)
    spread_est = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    df['bid_ask_spread_pct'] = pd.Series(spread_est).fillna(0.0005)

    # 2. Order Book Imbalance (OBI) Proxy (-1.0 to +1.0)
    # Buy pressure vs Sell pressure based on Close relative to High-Low range
    range_hl = (df['high'] - df['low']).replace(0, np.nan)
    close_loc = ((df['close'] - df['low']) / range_hl).clip(0.0, 1.0)
    obi_raw = (close_loc - 0.5) * 2.0
    df['order_book_imbalance'] = obi_raw.fillna(0.0).rolling(3, min_periods=1).mean().clip(-1.0, 1.0)

    # 3. Taker Buy Volume Ratio
    # Volume weighted by close position
    taker_buy_vol = df['volume'] * np.maximum(0, close_loc)
    taker_sell_vol = df['volume'] * np.maximum(0, 1.0 - close_loc)
    df['taker_buy_ratio'] = (taker_buy_vol / (taker_buy_vol + taker_sell_vol + 1e-8)).fillna(0.5).clip(0.0, 1.0)

    # 4. VPIN (Volume-Synchronized Probability of Toxicity)
    # Measured as rolling absolute order imbalance over total volume
    vol_imbalance = (taker_buy_vol - taker_sell_vol).abs()
    total_vol_24h = df['volume'].rolling(24, min_periods=1).sum().replace(0, np.nan)
    df['vpin'] = (vol_imbalance.rolling(24, min_periods=1).sum() / total_vol_24h).fillna(0.2).clip(0.0, 1.0)

    cols = ['timestamp', 'available_time', 'order_book_imbalance', 'bid_ask_spread_pct', 'taker_buy_ratio', 'vpin']
    return df[cols]


if __name__ == "__main__":
    ohlcv_path = os.path.join(DATA_RAW_DIR, "ohlcv.parquet")
    if os.path.exists(ohlcv_path):
        ohlcv = pd.read_parquet(ohlcv_path)
        micro = compute_microstructure_features(ohlcv)
        print("Microstructure Features Generated:")
        print(micro.tail(10))
        print(f"Shape: {micro.shape}")
        print("PASS: Microstructure module execution completed.")
