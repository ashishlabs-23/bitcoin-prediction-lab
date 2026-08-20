"""
research/analyst_layer/technical.py — Deterministic Technical Analyst Factor Generator
======================================================================================
Transforms raw price and technical indicators into 3 bounded numerical factors:
1. trend_score [-1.0, +1.0]: Multi-MA slope and alignment
2. momentum_score [-1.0, +1.0]: RSI, MACD, and Stochastic confluence
3. breakout_score [0.0, +1.0]: Volatility compression and Bollinger Band breakout intensity
"""

import numpy as np
import pandas as pd


def compute_technical_analyst_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Computes deterministic technical analyst factor scores."""
    factors = pd.DataFrame(index=df.index)

    # 1. Trend Score: Combines SMA 20, 50, 200 alignment and VWAP deviation
    sma20 = df.get('sma_ratio_20', pd.Series(0, index=df.index))
    sma50 = df.get('sma_ratio_50', pd.Series(0, index=df.index))
    sma200 = df.get('sma_ratio_200', pd.Series(0, index=df.index))
    vwap = df.get('vwap_ratio', pd.Series(0, index=df.index))

    trend_raw = (sma20 * 0.3) + (sma50 * 0.3) + (sma200 * 0.2) + (vwap * 0.2)
    factors['tech_trend_score'] = np.tanh(trend_raw * 20.0)

    # 2. Momentum Score: Combines RSI (centered at 50), MACD histogram, and Stochastic %K
    rsi = df.get('rsi_14', pd.Series(50, index=df.index))
    rsi_norm = (rsi - 50.0) / 50.0  # [-1, 1]
    macd_hist = df.get('macd_hist', pd.Series(0, index=df.index))
    stoch_k = df.get('stoch_k', pd.Series(50, index=df.index))
    stoch_norm = (stoch_k - 50.0) / 50.0

    mom_raw = (rsi_norm * 0.4) + (np.tanh(macd_hist * 10.0) * 0.3) + (stoch_norm * 0.3)
    factors['tech_momentum_score'] = np.clip(mom_raw, -1.0, 1.0)

    # 3. Breakout Score: Bollinger Band Width expansion + Close near band limits
    bb_width = df.get('bb_width_20', pd.Series(0.02, index=df.index))
    bb_pct = df.get('bb_pct_20', pd.Series(0.5, index=df.index))
    atr = df.get('atr_14', pd.Series(0.01, index=df.index))

    bb_extreme = np.abs(bb_pct - 0.5) * 2.0  # [0, 1]
    width_norm = np.tanh(bb_width * 50.0)
    factors['tech_breakout_score'] = np.clip(bb_extreme * 0.6 + width_norm * 0.4, 0.0, 1.0)

    return factors.fillna(0.0)
