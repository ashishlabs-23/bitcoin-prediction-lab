"""
tests/test_mamba_vs_ridge.py — Integration Tests for Mamba vs Ridge Benchmark & Promotion Gate
==============================================================================================
Verifies:
1. Multi-model baseline evaluation execution
2. Ridge retention when Mamba fails promotion criteria
3. Mamba shadow mode isolation
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.mamba_range_validation import run_mamba_validation_suite
from research.mamba_shadow import run_mamba_shadow_telemetry


def test_mamba_vs_ridge_validation_verdict():
    df_comp, meta = run_mamba_validation_suite()

    assert len(df_comp) >= 5
    assert meta["verdict"] == "RETAIN_PRODUCTION_RIDGE"
    assert meta["production_model"] == "v3.0.0-excursion-ridge-conformal"


def test_mamba_shadow_mode_isolation():
    df_s, meta = run_mamba_shadow_telemetry(n_samples=10)
    assert len(df_s) == 10
    assert meta["production_modified"] is False
    assert meta["actionable"] is False
