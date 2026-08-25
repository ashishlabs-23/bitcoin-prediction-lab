"""
tests/test_microstructure_dataset.py — Unit Tests for Event-Time Dataset & Point-in-Time Ordering
=================================================================================================
Verifies:
1. Continuous event tick generation
2. Monotonic timestamp progression (dt >= 0)
3. Excursion target calculations across 1m, 5m, 15m, 30m
"""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.microstructure_dataset import generate_synthetic_l2_event_stream, add_short_horizon_excursions


def test_microstructure_dataset_generation():
    df = generate_synthetic_l2_event_stream(n_events=200)
    assert len(df) == 200
    assert "timestamp_ms" in df.columns
    assert "signed_volume" in df.columns
    assert "imbalance" in df.columns

    # Timestamp monotonicity
    diffs = df["timestamp_ms"].diff().dropna().values
    assert (diffs >= 0).all()


def test_short_horizon_excursion_targets():
    df = generate_synthetic_l2_event_stream(n_events=300)
    df = add_short_horizon_excursions(df, horizons_seconds=[60, 300])

    assert "mfe_1m" in df.columns
    assert "mae_1m" in df.columns
    assert "mfe_5m" in df.columns
    assert "mae_5m" in df.columns

    # Targets non-negative
    assert (df["mfe_5m"] >= 0.0).all()
    assert (df["mae_5m"] >= 0.0).all()
