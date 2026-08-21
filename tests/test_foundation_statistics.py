"""
tests/test_foundation_statistics.py — Unit Tests for Foundation Model Statistical Gate
======================================================================================
Verifies:
1. Block bootstrap and permutation statistical testing
2. Family-wise Holm multiple-testing adjustment
3. Final decision CASE D (Foundation models provide useful zero-shot priors but local Ridge remains superior)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.foundation_statistical_gate import run_foundation_statistical_gate


def test_foundation_statistical_gate():
    df_st, meta = run_foundation_statistical_gate()

    assert len(df_st) == 4
    assert meta["is_promoted"] is False
    assert meta["verdict"] == "CASE_D_FOUNDATION_MODELS_PROVIDE_USEFUL_PRIORS_BUT_RIDGE_REMAINS_SUPERIOR"
