"""
tests/test_multiscale_decay.py — Unit Tests for Multiscale Information Decay
=============================================================================
Verifies:
1. Hawkes point-process intensity decay tracking across horizons
2. Derivatives signal emergence and decay tracking across horizons
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.multiscale_decay import evaluate_multiscale_decay


def test_multiscale_decay_audit():
    df_decay, meta = evaluate_multiscale_decay()

    assert len(df_decay) == 7
    assert meta["hawkes_half_life_min"] > 0
    assert "Realized Volatility" in meta["universal_bridge"]
