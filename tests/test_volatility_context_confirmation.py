"""
tests/test_volatility_context_confirmation.py — Unit Tests for Volatility Context Confirmation
=============================================================================================
Verifies:
1. Frozen untouched confirmation execution across Config A, B, and C
2. Block bootstrap and permutation hypothesis testing metrics
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.volatility_context_confirmation import run_volatility_context_confirmation
from research.volatility_context_statistics import run_volatility_context_statistics


def test_volatility_context_confirmation_execution():
    df_conf, meta = run_volatility_context_confirmation()

    assert len(df_conf) == 3
    assert meta["b_minus_a_mfe_delta_pct"] < 0.0
    assert meta["b_status"] == "VALIDATED_PRODUCTION_CONTEXT"


def test_volatility_context_statistics_hypothesis():
    df_stats, meta = run_volatility_context_statistics()

    assert len(df_stats) == 3
    assert meta["b_vs_a_p_adj"] < 0.01
    assert meta["verdict"] == "CASE_A_VOLATILITY_TERM_STRUCTURE_INDEPENDENTLY_IMPROVES_RIDGE"
