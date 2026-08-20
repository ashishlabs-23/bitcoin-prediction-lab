"""
research/analyst_layer/orderflow.py — Deterministic Order Flow Analyst Factor Generator
========================================================================================
Transforms order book depth, trade flow, and microstructure data into 3 bounded numerical factors:
1. of_imbalance_score [-1.0, +1.0]: Multi-depth and trade flow buying/selling pressure
2. of_liquidity_score [0.0, +1.0]: Spread tightness and total depth resilience
3. of_pressure_score [-1.0, +1.0]: Order book velocity and aggressive flow direction
"""

import numpy as np
import pandas as pd


def compute_orderflow_analyst_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Computes deterministic order flow analyst factor scores."""
    factors = pd.DataFrame(index=df.index)

    # 1. Imbalance Score: Combines Top-of-Book imbalance, 1% depth ratio, and Trade Flow imbalance
    obi = df.get('order_book_imbalance', pd.Series(0, index=df.index))
    depth_ratio = df.get('depth_ratio_1pct', pd.Series(1.0, index=df.index))
    trade_imbalance = df.get('trade_flow_imbalance', pd.Series(0, index=df.index))

    # Log ratio normalized: log(depth_ratio)
    log_depth = np.tanh(np.log(np.clip(depth_ratio, 0.01, 100.0)))

    imb_raw = (obi * 0.4) + (log_depth * 0.3) + (trade_imbalance * 0.3)
    factors['of_imbalance_score'] = np.clip(imb_raw, -1.0, 1.0)

    # 2. Liquidity Score: Spread efficiency (lower spread = higher liquidity)
    spread_bps = df.get('spread_bps', pd.Series(1.0, index=df.index))
    spread_norm = np.exp(-spread_bps / 5.0)  # [0, 1]
    factors['of_liquidity_score'] = np.clip(spread_norm, 0.0, 1.0)

    # 3. Pressure Score: Imbalance velocity + volume force
    obi_velocity = obi.diff(3).fillna(0.0)
    vol_z = df.get('vol_z_24h', pd.Series(0, index=df.index))
    pressure_raw = obi_velocity * np.tanh(np.maximum(0.0, vol_z))
    factors['of_pressure_score'] = np.clip(pressure_raw, -1.0, 1.0)

    return factors.fillna(0.0)
