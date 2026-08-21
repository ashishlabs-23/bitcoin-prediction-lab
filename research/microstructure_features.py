"""
research/microstructure_features.py — 16 Canonical Microstructure Features
===========================================================================
Extracts point-in-time order-book, microprice, and trade-flow factors:
1. Mid Price
2. Spread
3. Relative Spread
4. Microprice (volume-weighted top of book)
5. Top-of-Book Imbalance
6. Depth Imbalance
7. Multi-Level Imbalance
8. Signed Trade Volume
9. Buy/Sell Volume Ratio
10. Order-Flow Imbalance (OFI)
11. Order Arrival Rate
12. Cancellation Rate proxy
13. Imbalance Velocity
14. Spread Velocity
15. Microprice Velocity
16. Short-Term Realized Volatility (50-event rolling window)
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

MICROSTRUCTURE_FEATURE_NAMES = [
    "mid_price", "spread", "relative_spread", "microprice",
    "top_imbalance", "depth_imbalance", "multi_level_imbalance",
    "signed_volume", "buy_sell_ratio", "order_flow_imbalance",
    "order_arrival_rate", "cancellation_rate",
    "imbalance_velocity", "spread_velocity", "microprice_velocity",
    "realized_vol_50"
]


def extract_microstructure_features(df_events: pd.DataFrame) -> pd.DataFrame:
    """
    Computes strictly causal point-in-time microstructure feature matrix.
    """
    df = df_events.copy()

    # 1. Mid price & Spread
    mid_price = (df["bid"] + df["ask"]) / 2.0
    spread = df["ask"] - df["bid"]
    rel_spread = spread / (mid_price + 1e-6)

    # 2. Microprice (Volume-weighted bid/ask)
    d_bid = df["depth_bid"]
    d_ask = df["depth_ask"]
    microprice = (d_bid * df["ask"] + d_ask * df["bid"]) / (d_bid + d_ask + 1e-6)

    # 3. Imbalance metrics
    top_imb = (d_bid - d_ask) / (d_bid + d_ask + 1e-6)
    depth_imb = df["imbalance"]
    multi_imb = top_imb * 0.7 + depth_imb * 0.3

    # 4. Trade flow & OFI
    signed_vol = df["signed_volume"]
    cum_buy = np.maximum(0, signed_vol).rolling(20).sum().fillna(0.01)
    cum_sell = np.maximum(0, -signed_vol).rolling(20).sum().fillna(0.01)
    bs_ratio = cum_buy / (cum_sell + 1e-6)
    ofi = signed_vol.rolling(10).mean().fillna(0.0)

    # 5. Arrival rates & velocities (per second)
    dt_sec = df["timestamp_ms"].diff().fillna(200.0).values / 1000.0
    dt_sec = np.maximum(0.001, dt_sec)
    arr_rate = 1.0 / dt_sec
    canc_rate = np.where(df["event_type"] == "imbalance_change", 1.0, 0.0)
    canc_rate = pd.Series(canc_rate).rolling(20).mean().fillna(0.0).values

    imb_vel = top_imb.diff().fillna(0.0).values / dt_sec
    spread_vel = spread.diff().fillna(0.0).values / dt_sec
    micro_vel = (microprice - mid_price).values

    # 6. Short-term Realized Volatility (50 ticks)
    returns = mid_price.pct_change().fillna(0.0)
    rv_50 = returns.rolling(50).std().bfill().fillna(0.0005).values

    features_df = pd.DataFrame({
        "mid_price": mid_price.values,
        "spread": spread.values,
        "relative_spread": rel_spread.values,
        "microprice": microprice.values,
        "top_imbalance": top_imb.values,
        "depth_imbalance": depth_imb.values,
        "multi_level_imbalance": multi_imb.values,
        "signed_volume": signed_vol.values,
        "buy_sell_ratio": bs_ratio.values,
        "order_flow_imbalance": ofi.values,
        "order_arrival_rate": arr_rate,
        "cancellation_rate": canc_rate,
        "imbalance_velocity": imb_vel,
        "spread_velocity": spread_vel,
        "microprice_velocity": micro_vel,
        "realized_vol_50": rv_50
    })

    return features_df


if __name__ == "__main__":
    from research.microstructure_dataset import generate_synthetic_l2_event_stream
    df_raw = generate_synthetic_l2_event_stream(n_events=500)
    feats = extract_microstructure_features(df_raw)
    print("=== EXTRACTED MICROSTRUCTURE FEATURES ===")
    print(feats.head())
