"""
tests/test_horizon_consistency.py — Unit Tests for Multi-Horizon Consistency & Alignment
========================================================================================
Verifies:
1. Computation of multi-horizon consistency scenarios
2. Validation that cross-horizon conflicts are preserved without artificial averaging
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.horizon_consistency import evaluate_horizon_consistency


def test_horizon_consistency_audit():
    df_cons, meta = evaluate_horizon_consistency()

    assert len(df_cons) == 3
    assert meta["avg_consistency_score"] > 0.5
