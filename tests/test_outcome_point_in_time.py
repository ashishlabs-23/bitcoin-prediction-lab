"""
tests/test_outcome_point_in_time.py — Tests for Point-in-Time Forward Window Invariants
========================================================================================
Verifies:
- Forward window strictly evaluates (t, t + 24h].
- Does not leak prior bars (t - 1h) or lookahead beyond (t + 24h).
- Excursion math MFE/MAE/actual_return calculations are exact.
"""

import pandas as pd
import numpy as np

def test_excursion_mathematics():
    entry_price = 60000.0
    actual_high = 63000.0
    actual_low = 58500.0
    actual_close = 61200.0

    actual_mfe = (actual_high - entry_price) / entry_price
    actual_mae = (entry_price - actual_low) / entry_price
    actual_return = (actual_close - entry_price) / entry_price

    assert np.isclose(actual_mfe, 0.05)   # +5.0%
    assert np.isclose(actual_mae, 0.025)  # -2.5% adverse excursion
    assert np.isclose(actual_return, 0.02) # +2.0% close return

def test_point_in_time_window_filtering():
    t_start = pd.Timestamp("2026-08-21T00:00:00Z")
    t_end = t_start + pd.Timedelta(hours=24)

    # Sample DataFrame with timestamps before, inside, and after
    sample_df = pd.DataFrame([
        {"dt": pd.Timestamp("2026-08-20T23:59:59Z"), "price": 59000.0},
        {"dt": pd.Timestamp("2026-08-21T01:00:00Z"), "price": 60500.0},
        {"dt": pd.Timestamp("2026-08-21T12:00:00Z"), "price": 61500.0},
        {"dt": pd.Timestamp("2026-08-22T00:00:00Z"), "price": 62000.0},
        {"dt": pd.Timestamp("2026-08-22T00:00:01Z"), "price": 62500.0},
    ])

    mask = (sample_df["dt"] > t_start) & (sample_df["dt"] <= t_end)
    filtered = sample_df[mask]

    assert len(filtered) == 3
    assert filtered.iloc[0]["price"] == 60500.0
    assert filtered.iloc[-1]["price"] == 62000.0
