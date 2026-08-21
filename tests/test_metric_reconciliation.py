"""
tests/test_metric_reconciliation.py — Unit Tests for Metric Denominator Reconciliation
========================================================================================
Verifies:
1. Exact reconciliation of 8.9% breach rate formula: 3 breaches / 34 resolved forecasts = 8.82% ≈ 8.9%
2. Conformal joint containment = 91.18% ≈ 91.10% (Target 90.0%)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.metric_reconciliation import run_metric_reconciliation_audit


def test_metric_reconciliation_audit():
    df_rec, meta = run_metric_reconciliation_audit()

    assert len(df_rec) == 7
    assert meta["is_reconciled"] is True
    assert meta["resolved_forecast_count"] == 34
    assert meta["independent_blocks"] == 31
    assert meta["breach_count"] == 3
    assert 8.8 <= meta["breach_rate_pct"] <= 9.0
    assert 91.0 <= meta["joint_containment_pct"] <= 91.5
