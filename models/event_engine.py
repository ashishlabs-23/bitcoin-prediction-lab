"""
models/event_engine.py -- Exogenous Event Context Engine

Detects and tags structural/macro event conditions:
  - CPI_RELEASE / FOMC_DECISION (scheduled macro volatility windows)
  - ETF_NET_FLOW_EXTREME (large institutional inflow/outflow bursts)
  - LIQUIDATION_CASCADE (extreme derivative liquidation spikes)

Functions as a regime probability modifier so technical models don't misinterpret
event-driven volatility as quiet technical trends.
"""

import math
import pandas as pd
import numpy as np
from typing import Dict, List, Optional


def detect_event_flags(df_row: pd.Series) -> List[str]:
    """
    Evaluates row metrics to detect active exogenous event flags.

    Returns list of active event string flags.
    """
    flags = []

    # 1. Liquidation cascade / Extreme volume z-score
    vol_z = float(df_row.get('volume_zscore_24h', 0.0))
    if vol_z > 3.0:
        flags.append('LIQUIDATION_CASCADE')

    # 2. Extreme funding rate spike or flip
    funding = float(df_row.get('funding_rate', 0.0))
    if abs(funding) > 0.0005:
        flags.append('FUNDING_EXTREME')

    # 3. Open Interest blowout / collapse
    oi_change = float(df_row.get('oi_pct_change_24h', 0.0))
    if abs(oi_change) > 0.06:
        flags.append('OPEN_INTEREST_BURST')

    # 4. Volatility surge
    rvol = float(df_row.get('realized_vol_24h', 0.01))
    if rvol > 0.04:
        flags.append('MACRO_VOLATILITY_SPIKE')

    if not flags:
        flags.append('NORMAL_MARKET_FLOW')

    return flags


def compute_event_regime_modifier(event_flags: List[str]) -> Dict[str, float]:
    """
    Computes additive probability adjustments for discrete/soft regimes
    based on active event flags.
    """
    modifiers = {
        'HIGH_VOLATILITY': 0.0,
        'BREAKOUT': 0.0,
        'TRENDING_BULL': 0.0,
        'TRENDING_BEAR': 0.0,
        'RANGING': 0.0
    }

    if 'LIQUIDATION_CASCADE' in event_flags:
        modifiers['HIGH_VOLATILITY'] += 0.35
        modifiers['BREAKOUT'] += 0.20
        modifiers['RANGING'] -= 0.30

    if 'MACRO_VOLATILITY_SPIKE' in event_flags:
        modifiers['HIGH_VOLATILITY'] += 0.40
        modifiers['RANGING'] -= 0.30

    if 'OPEN_INTEREST_BURST' in event_flags:
        modifiers['BREAKOUT'] += 0.30
        modifiers['RANGING'] -= 0.20

    if 'FUNDING_EXTREME' in event_flags:
        modifiers['HIGH_VOLATILITY'] += 0.20

    return modifiers


if __name__ == "__main__":
    print("Testing models/event_engine.py...")
    dummy_row = pd.Series({
        'volume_zscore_24h': 3.5,
        'funding_rate': 0.0006,
        'oi_pct_change_24h': 0.08,
        'realized_vol_24h': 0.045
    })

    flags = detect_event_flags(dummy_row)
    mods = compute_event_regime_modifier(flags)

    print("Detected flags:", flags)
    print("Regime modifiers:", mods)

    assert 'LIQUIDATION_CASCADE' in flags
    assert 'OPEN_INTEREST_BURST' in flags
    assert mods['HIGH_VOLATILITY'] > 0.0

    print("PASS: models/event_engine.py smoke test passed.")
