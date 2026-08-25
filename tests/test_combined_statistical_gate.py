"""
tests/test_combined_statistical_gate.py — Unit Tests for Block Bootstrap & Permutation Gate
===========================================================================================
Verifies:
1. Execution of paired block bootstrap and permutation tests
2. Strict significance across MFE error, MAE error, and Winkler score
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.combined_statistical_gate import run_combined_statistical_gate


def test_combined_statistical_gate_significance():
    df_gate, meta = run_combined_statistical_gate()

    assert len(df_gate) == 3
    assert meta["is_gate_passed"] is True
    assert meta["mfe_p_adj"] < 0.01
    assert meta["verdict"] == "CASE_A_COMBINED_IMPROVEMENT_PERSISTS_WITH_SIGNIFICANCE"
