#!/usr/bin/env python3
"""
Synthetic Market Data Generator
==============================
Generates geometric Brownian motion (GBM) with jump-diffusion
to stress-test regime detection and backtest models under extreme tails.
"""

import numpy as np
import pandas as pd


def generate_gbm_jumps(
    n_bars: int = 1000,
    s0: float = 65000.0,
    mu: float = 0.0002,
    sigma: float = 0.015,
    jump_prob: float = 0.02,
    jump_std: float = 0.05
) -> pd.DataFrame:
    np.random.seed(42)
    dt = 1.0 / 24.0  # 1-hour intervals
    
    # Diffusion component
    returns = np.random.normal((mu - 0.5 * sigma**2) * dt, sigma * np.sqrt(dt), n_bars)
    
    # Jump component (Poisson)
    jumps = (np.random.rand(n_bars) < jump_prob) * np.random.normal(0, jump_std, n_bars)
    total_returns = returns + jumps

    prices = s0 * np.exp(np.cumsum(total_returns))
    timestamps = pd.date_range("2026-01-01", periods=n_bars, freq="1h", tz="UTC")

    highs = prices * (1.0 + np.abs(np.random.normal(0, 0.003, n_bars)))
    lows = prices * (1.0 - np.abs(np.random.normal(0, 0.003, n_bars)))
    opens = prices * (1.0 + np.random.normal(0, 0.001, n_bars))
    volumes = np.random.exponential(scale=150.0, size=n_bars)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": opens.round(2),
        "high": highs.round(2),
        "low": lows.round(2),
        "close": prices.round(2),
        "volume": volumes.round(4)
    })
    return df


if __name__ == "__main__":
    df = generate_gbm_jumps(500)
    print(f"Generated {len(df)} synthetic bars with jump diffusion.")
    print(df.head(3))
