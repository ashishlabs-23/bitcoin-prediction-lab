"""
tests/test_combined_longitudinal.py — Unit Tests for Longitudinal Production Validation
======================================================================================
Verifies:
1. Longitudinal metric tracking across 24h non-overlapping blocks
2. Stability of the -14 bps MFE advantage
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.combined_longitudinal_validation import evaluate_combined_longitudinal_validation


def test_combined_longitudinal_validation_execution():
    df_long, meta = evaluate_combined_longitudinal_validation()

    assert len(df_long) == 6
    assert meta["current_blocks"] == 31
    assert meta["mfe_delta_bps"] == -14.0
    assert meta["p90_coverage"] >= 90.0
    assert meta["verdict"] == "CASE_A_COMBINED_IMPROVEMENT_PERSISTS_WITH_SIGNIFICANCE"
