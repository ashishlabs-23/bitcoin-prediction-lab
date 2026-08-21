"""
models/challengers/hawkes_microstructure.py — Multivariate Hawkes Point-Process Model
=====================================================================================
Models self-exciting and cross-exciting event intensities in BTCUSD order flow:
1. Event Dimensions: BUY_PRESSURE, SELL_PRESSURE, LIQUIDITY_CHANGE, VOLATILITY_SHOCK
2. Parametric Intensity: lambda_m(t) = mu_m + sum_{j} alpha_{mj} * exp(-beta_{mj} * (t - t_k))
3. Emits structured point-in-time intensity features:
   - lambda_buy, lambda_sell, lambda_liquidity, lambda_volatility
   - buy_sell_intensity_ratio
   - event_pressure (lambda_buy - lambda_sell)
   - event_cluster_score (ratio of total intensity to baseline)
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional


class MultivariateHawkesIntensityModel:
    """
    Multivariate exponential Hawkes process for high-frequency order-flow events.
    """

    def __init__(
        self,
        n_dimensions: int = 4,
        mu: Optional[np.ndarray] = None,
        alpha: Optional[np.ndarray] = None,
        beta: Optional[np.ndarray] = None
    ):
        self.dim_names = ["buy_pressure", "sell_pressure", "liquidity_change", "volatility_shock"]
        self.n_dim = len(self.dim_names)

        # Baseline intensities (events / second)
        self.mu = mu if mu is not None else np.array([0.50, 0.50, 0.30, 0.10])
        # Excitation matrix alpha (self and cross excitation)
        self.alpha = alpha if alpha is not None else np.array([
            [0.25, 0.05, 0.10, 0.15],
            [0.05, 0.25, 0.10, 0.15],
            [0.10, 0.10, 0.20, 0.10],
            [0.20, 0.20, 0.15, 0.30]
        ])
        # Decay rates beta (decay speed per second)
        self.beta = beta if beta is not None else np.array([
            [1.5, 1.5, 1.5, 1.5],
            [1.5, 1.5, 1.5, 1.5],
            [1.0, 1.0, 1.0, 1.0],
            [2.0, 2.0, 2.0, 2.0]
        ])

    def compute_intensities(self, df_events: pd.DataFrame) -> pd.DataFrame:
        """
        Computes recursive exponential decay intensities along event sequence.
        """
        t_sec = df_events["timestamp_ms"].values / 1000.0
        n_events = len(t_sec)

        # Map event types to dimension index
        event_indices = np.zeros(n_events, dtype=int)
        for i, row in df_events.iterrows():
            etype = row["event_type"]
            if etype == "trade":
                event_indices[i] = 0 if row["signed_volume"] > 0 else 1
            elif etype in ["bid_update", "ask_update", "depth_update"]:
                event_indices[i] = 2
            else:
                event_indices[i] = 3

        intensities = np.zeros((n_events, self.n_dim))
        decayed_kernel = np.zeros((self.n_dim, self.n_dim))

        intensities[0] = self.mu

        for i in range(1, n_events):
            dt = max(0.0001, t_sec[i] - t_sec[i - 1])
            prev_event = event_indices[i - 1]

            # Decay previous excitation
            decayed_kernel = decayed_kernel * np.exp(-self.beta * dt)
            # Add jump from the event that just occurred
            decayed_kernel[:, prev_event] += self.alpha[:, prev_event]

            # Compute current lambda = mu + sum(decayed_kernel)
            current_lambda = self.mu + np.sum(decayed_kernel, axis=1)
            intensities[i] = current_lambda

        # Derived structured intensity factors
        l_buy = intensities[:, 0]
        l_sell = intensities[:, 1]
        l_liq = intensities[:, 2]
        l_vol = intensities[:, 3]

        bs_ratio = l_buy / (l_sell + 1e-6)
        pressure = l_buy - l_sell
        base_sum = np.sum(self.mu)
        cluster_score = np.sum(intensities, axis=1) / base_sum

        return pd.DataFrame({
            "lambda_buy": np.round(l_buy, 4),
            "lambda_sell": np.round(l_sell, 4),
            "lambda_liquidity": np.round(l_liq, 4),
            "lambda_volatility": np.round(l_vol, 4),
            "buy_sell_intensity_ratio": np.round(bs_ratio, 4),
            "event_pressure": np.round(pressure, 4),
            "event_cluster_score": np.round(cluster_score, 4)
        })


hawkes_model = MultivariateHawkesIntensityModel()
