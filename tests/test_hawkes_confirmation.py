"""
tests/test_hawkes_confirmation.py — Unit Tests for Hawkes Confirmation Audit & Statistical Tests
================================================================================================
Verifies:
1. Frozen confirmation audit execution and manifest creation
2. Block bootstrap and permutation test calculations
3. Multiple testing correction (Holm-Bonferroni)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.hawkes_confirmation import run_hawkes_confirmation_audit
from research.hawkes_statistical_test import run_hawkes_statistical_tests


def test_hawkes_confirmation_audit_execution():
    df_conf, meta = run_hawkes_confirmation_audit()

    assert len(df_conf) == 3
    assert meta["status"] == "CONFIRMED"
    assert meta["mfe_improvement_over_candle_bps"] > 0.0


def test_hawkes_statistical_hypothesis_testing():
    res = run_hawkes_statistical_tests(n_bootstrap=500)

    assert "mean_mfe_delta_bps" in res
    assert "bootstrap_ci_95_bps" in res
    assert "holm_bonferroni_p" in res
    assert res["family_size_M"] == 12
    assert res["is_statistically_significant"] is True
