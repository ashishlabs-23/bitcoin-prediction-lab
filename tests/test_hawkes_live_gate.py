"""
tests/test_hawkes_live_gate.py — Unit Tests for Live Statistical Promotion Gate
===============================================================================
Verifies:
1. Live paired block comparison and Holm-Bonferroni p-values
2. Final decision CASE A (VALIDATED_SHADOW_MODEL)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.hawkes_live_statistical_gate import run_live_hawkes_statistical_gate


def test_hawkes_live_statistical_gate_decision():
    df_gate, meta = run_live_hawkes_statistical_gate()

    assert len(df_gate) == 3
    assert meta["verdict"] == "CASE_A_REPRODUCES_OFFLINE_IMPROVEMENT"
    assert meta["hawkes_status"] == "VALIDATED_SHADOW_MODEL"
    assert meta["p_adj"] < 0.05
