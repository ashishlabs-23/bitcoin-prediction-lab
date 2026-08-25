"""
tests/test_accuracy_timeseries.py — Unit Tests for Live Accuracy Time-Series
=============================================================================
Verifies:
1. Generation of rolling 5-block, 10-block, 20-block, 30-block metrics
2. Integrity of canonical production accuracy summary metrics
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.accuracy_timeseries import generate_production_accuracy_timeseries


def test_production_accuracy_timeseries():
    df_ts, df_prod = generate_production_accuracy_timeseries()

    assert len(df_ts) == 4
    assert len(df_prod) == 10
    assert "Range Accuracy" in df_prod["Metric Category"].values
    assert "Sharpness" in df_prod["Metric Category"].values
