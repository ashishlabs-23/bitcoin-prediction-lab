"""
research/analyst_layer/derivatives.py — Deterministic Derivatives Analyst Factor Generator
==========================================================================================
Transforms perpetual futures funding, open interest, and basis into 3 bounded numerical factors:
1. deriv_leverage_risk [0.0, +1.0]: Extreme OI/Volume ratio and liquidation vulnerability
2. deriv_funding_pressure [-1.0, +1.0]: Funding rate directional drag and squeeze potential
3. deriv_oi_pressure [-1.0, +1.0]: Price and Open Interest accumulation/distribution divergence
"""

import numpy as np
import pandas as pd


def compute_derivatives_analyst_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Computes deterministic derivatives analyst factor scores."""
    factors = pd.DataFrame(index=df.index)

    funding = df.get('funding_rate', pd.Series(0, index=df.index))
    oi_change = df.get('open_interest_change_24h', pd.Series(0, index=df.index))
    oi_vol = df.get('oi_vol_ratio', pd.Series(1.0, index=df.index))
    ret24 = df.get('ret_24h', pd.Series(0, index=df.index))

    # 1. Leverage Risk: High OI relative to volume indicates crowded speculative positioning
    oi_vol_z = (oi_vol - oi_vol.rolling(168, min_periods=24).mean()) / (oi_vol.rolling(168, min_periods=24).std() + 1e-6)
    factors['deriv_leverage_risk'] = np.clip(1.0 / (1.0 + np.exp(-oi_vol_z)), 0.0, 1.0)

    # 2. Funding Pressure: Crowded longs (positive funding) vs crowded shorts (negative funding)
    funding_z = (funding - funding.rolling(168, min_periods=24).mean()) / (funding.rolling(168, min_periods=24).std() + 1e-6)
    factors['deriv_funding_pressure'] = np.tanh(funding_z * 0.5)

    # 3. OI Divergence Pressure: Price rising + OI rising (Healthy Trend) vs Price rising + OI falling (Short Squeeze / Exhaustion)
    price_sign = np.sign(ret24)
    oi_sign = np.sign(oi_change)
    divergence = price_sign * oi_sign  # +1 = confirming, -1 = diverging
    factors['deriv_oi_pressure'] = np.clip(divergence * np.abs(oi_change) * 5.0, -1.0, 1.0)

    return factors.fillna(0.0)
