"""
tests/test_forecast_error_analysis.py — Unit Tests for Forecast Error Dissection
================================================================================
Verifies:
1. Multi-dimensional error attribution by temporal and market context
2. Uncertainty-conditioned error monotonicity test
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.forecast_error_analysis import run_forecast_error_analysis
from research.error_conditional_calibration import run_uncertainty_calibration_test


def test_forecast_error_analysis_execution():
    df_dow, df_unc, meta = run_forecast_error_analysis()

    assert len(df_dow) > 0
    assert len(df_unc) > 0
    assert "Mean Abs MFE Error %" in df_dow.columns
    assert "Path Containment %" in df_unc.columns


def test_uncertainty_calibration_monotonicity():
    df_res, meta = run_uncertainty_calibration_test()

    assert len(df_res) > 0
    assert "Uncertainty Bucket" in df_res.columns
    assert "Realized MFE Error %" in df_res.columns
    assert meta["is_monotonic"] is True
