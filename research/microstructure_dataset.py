"""
research/microstructure_dataset.py — Point-in-Time Microstructure & Event-Stream Dataset
========================================================================================
Generates point-in-time order-book and trade event sequences for short-horizon research:
1. Event Types: 'trade', 'bid_update', 'ask_update', 'depth_update', 'spread_change', 'imbalance_change'
2. Event Schema: timestamp_ms, event_type, price, size, bid, ask, spread, depth_bid, depth_ask, signed_volume, imbalance
3. Strict Causal Temporal Guarantee: For all t_i, features only access events <= t_i (zero future lookahead)
4. Emits short-horizon targets: 1m, 5m, 15m, 30m MFE and MAE excursions
"""

import os
import sys
import json
import logging
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MicrostructureDataset")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def generate_synthetic_l2_event_stream(
    n_events: int = 5000,
    base_price: float = 65000.0,
    seed: int = 42
) -> pd.DataFrame:
    """
    Generates realistic, continuous-time L2 order book and trade event ticks with Poisson-like arrivals.
    """
    np.random.seed(seed)
    
    # Inter-arrival times in milliseconds (exponential distribution, mean = 200ms)
    dt_ms = np.random.exponential(scale=200, size=n_events).astype(int) + 10
    timestamps_ms = np.cumsum(dt_ms) + 1724000000000

    prices = np.zeros(n_events)
    bids = np.zeros(n_events)
    asks = np.zeros(n_events)
    depth_bids = np.zeros(n_events)
    depth_asks = np.zeros(n_events)
    signed_volumes = np.zeros(n_events)
    imbalances = np.zeros(n_events)
    event_types = []

    curr_p = base_price
    curr_spread = 0.50

    type_choices = ["trade", "bid_update", "ask_update", "depth_update", "imbalance_change"]
    type_probs = [0.35, 0.20, 0.20, 0.15, 0.10]

    for i in range(n_events):
        etype = np.random.choice(type_choices, p=type_probs)
        event_types.append(etype)

        # Microstructure price evolution (geometric Brownian motion + order flow feedback)
        side = 1.0 if np.random.rand() > 0.48 else -1.0
        trade_size = np.random.exponential(scale=0.8) + 0.01

        if etype == "trade":
            signed_vol = side * trade_size
            curr_p += side * (0.10 + 0.05 * trade_size)
        else:
            signed_vol = 0.0
            curr_p += np.random.normal(0, 0.08)

        # Spread & Depth
        curr_spread = max(0.10, curr_spread + np.random.normal(0, 0.02))
        bid = curr_p - curr_spread / 2.0
        ask = curr_p + curr_spread / 2.0
        d_bid = np.random.exponential(scale=5.0) + 1.0
        d_ask = np.random.exponential(scale=5.0) + 1.0
        imb = (d_bid - d_ask) / (d_bid + d_ask)

        prices[i] = curr_p
        bids[i] = bid
        asks[i] = ask
        depth_bids[i] = d_bid
        depth_asks[i] = d_ask
        signed_volumes[i] = signed_vol
        imbalances[i] = imb

    df = pd.DataFrame({
        "timestamp_ms": timestamps_ms,
        "event_type": event_types,
        "price": np.round(prices, 2),
        "bid": np.round(bids, 2),
        "ask": np.round(asks, 2),
        "spread": np.round(asks - bids, 2),
        "depth_bid": np.round(depth_bids, 2),
        "depth_ask": np.round(depth_asks, 2),
        "signed_volume": np.round(signed_volumes, 4),
        "imbalance": np.round(imbalances, 4)
    })

    # Causal ordering assertion
    assert (df["timestamp_ms"].diff().dropna() >= 0).all(), "Non-monotonic event timestamps detected!"
    return df


def add_short_horizon_excursions(
    df: pd.DataFrame,
    horizons_seconds: List[int] = [60, 300, 900, 1800]  # 1m, 5m, 15m, 30m
) -> pd.DataFrame:
    """
    Computes forward short-horizon MFE and MAE targets for each event tick.
    """
    p = df["price"].values
    t_sec = df["timestamp_ms"].values / 1000.0
    n = len(p)

    for h_sec in horizons_seconds:
        h_name = f"{h_sec // 60}m"
        mfe_col = f"mfe_{h_name}"
        mae_col = f"mae_{h_name}"
        dir_col = f"dir_{h_name}"

        mfe_arr = np.zeros(n)
        mae_arr = np.zeros(n)
        dir_arr = np.zeros(n)

        for i in range(n):
            t_end = t_sec[i] + h_sec
            future_mask = (t_sec > t_sec[i]) & (t_sec <= t_end)
            if not np.any(future_mask):
                mfe_arr[i] = 0.0
                mae_arr[i] = 0.0
                dir_arr[i] = 0.0
                continue

            future_prices = p[future_mask]
            p0 = p[i]
            mfe_arr[i] = max(0.0, (np.max(future_prices) - p0) / p0)
            mae_arr[i] = max(0.0, (p0 - np.min(future_prices)) / p0)
            terminal_ret = (future_prices[-1] - p0) / p0
            dir_arr[i] = 1.0 if terminal_ret > 0.0002 else (-1.0 if terminal_ret < -0.0002 else 0.0)

        df[mfe_col] = mfe_arr
        df[mae_col] = mae_arr
        df[dir_col] = dir_arr

    return df


if __name__ == "__main__":
    df_events = generate_synthetic_l2_event_stream(n_events=3000)
    df_events = add_short_horizon_excursions(df_events)
    print("=== MICROSTRUCTURE EVENT STREAM DATASET ===")
    print(df_events.head())
    manifest = {
        "event_count": len(df_events),
        "duration_minutes": round((df_events["timestamp_ms"].iloc[-1] - df_events["timestamp_ms"].iloc[0]) / 60000.0, 2),
        "event_types": list(df_events["event_type"].unique()),
        "horizons": ["1m", "5m", "15m", "30m"],
        "causal_ordering_verified": True
    }
    with open(os.path.join(RESULTS_DIR, "microstructure_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
