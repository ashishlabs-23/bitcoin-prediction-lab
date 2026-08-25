"""
tests/test_challenger_bakeoff.py — Unit Tests for Challenger Bake-Off & Paired Testing
======================================================================================
Verifies:
1. Walk-forward 1v1 challenger bake-off execution and metric reporting
2. Paired hypothesis and bootstrap test execution
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.challenger_bakeoff import run_challenger_bakeoff
from research.paired_challenger_test import run_paired_challenger_test


def test_challenger_bakeoff_execution():
    df_bakeoff, manifest = run_challenger_bakeoff()

    assert len(df_bakeoff) >= 5
    assert manifest["bakeoff_verdict"] == "RETAIN_PRODUCTION_RIDGE"
    assert manifest["ridge_mfe_mae"] < manifest["ewma_mfe_mae"]


def test_paired_challenger_hypothesis_test():
    df_paired, meta = run_paired_challenger_test(n_bootstrap=100)

    assert len(df_paired) >= 2
    assert meta["n_blocks"] > 0
    assert meta["mean_mae_delta"] < 0.0  # Ridge has lower error than EWMA
