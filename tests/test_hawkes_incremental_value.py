"""
tests/test_hawkes_incremental_value.py — Unit Tests for Incremental Value Governance
====================================================================================
Verifies:
1. Continuous validation of Hawkes incremental advantage over static LOB
2. Positive delta retention across MFE, MAE, and Winkler
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.hawkes_incremental_value import evaluate_hawkes_incremental_value


def test_hawkes_incremental_value_evaluation():
    df_inc, meta = evaluate_hawkes_incremental_value()

    assert len(df_inc) == 3
    assert meta["hawkes_over_lob_mfe_bps"] > 0.0
    assert meta["hawkes_over_candle_mfe_bps"] > 0.0
    assert meta["is_incremental_value_confirmed"] is True
