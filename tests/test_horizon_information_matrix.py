"""
tests/test_horizon_information_matrix.py — Unit Tests for Horizon Information Matrix
=====================================================================================
Verifies:
1. Complete construction of 5x5 information family matrix
2. Proper status assignments (SUPPORTED, WEAK, NO_SIGNAL)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.horizon_information_matrix import build_horizon_information_matrix


def test_horizon_information_matrix_generation():
    df_info, meta = build_horizon_information_matrix()

    assert len(df_info) == 5
    assert "Realized Volatility" in df_info.columns
    assert (df_info["Realized Volatility"] == "SUPPORTED").all()
