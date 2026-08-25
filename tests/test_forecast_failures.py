"""
tests/test_forecast_failures.py — Unit Tests for Forecast Failure & Breach Library
==================================================================================
Verifies:
1. Searchable index of tail prediction failures and envelope breaches
2. Total breach rate aligns with conformal alpha (target 10.0%, observed 8.9%)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.forecast_failure_analysis import run_forecast_failure_analysis


def test_forecast_failure_analysis():
    df_fails, meta = run_forecast_failure_analysis()

    assert len(df_fails) == 3
    assert meta["conformal_alignment"] == "COMPLIANT"
    assert meta["breach_rate_pct"] < 10.0
