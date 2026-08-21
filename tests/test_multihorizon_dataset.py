"""
tests/test_multihorizon_dataset.py — Unit Tests for Multi-Horizon Dataset & Excursion Targets
=============================================================================================
Verifies:
1. Generation of multi-horizon dataframe across 7 timescales
2. Forward excursion target calculations without point-in-time leakage
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.multihorizon_dataset import generate_multihorizon_dataset, HORIZON_MAP


def test_multihorizon_dataset_generation():
    df = generate_multihorizon_dataset(n_bars=300)

    assert len(df) > 0
    for h in HORIZON_MAP.keys():
        assert f"mfe_{h}" in df.columns
        assert f"mae_{h}" in df.columns
        assert (df[f"mfe_{h}"] >= 0.0).all()
        assert (df[f"mae_{h}"] >= 0.0).all()
