"""
tests/test_hawkes_live_dependence.py — Unit Tests for Live Hawkes Dependence & N_eff
===================================================================================
Verifies:
1. Computation of non-overlapping 5m blocks and lag autocorrelations
2. Effective sample size N_eff derivation
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.hawkes_live_dependence import analyze_live_hawkes_dependence


def test_hawkes_live_dependence_analysis():
    df_dep, meta = analyze_live_hawkes_dependence(n_raw_forecasts=500)

    assert len(df_dep) >= 6
    assert meta["n_raw"] == 500
    assert meta["n_blocks_5m"] == 100
    assert meta["n_eff"] > 0
