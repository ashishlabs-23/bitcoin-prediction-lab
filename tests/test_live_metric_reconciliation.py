"""
tests/test_live_metric_reconciliation.py — Unit Tests for Metric Lineage & Reconciliation
==========================================================================================
Verifies:
1. Mathematical taxonomy: MFE P90, MAE P90, High Containment, Low Containment, Joint Path
2. Correct handling of resolved vs unresolved snapshots
3. Consistency with research/live_metric_contract.md
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.live_metric_reconciliation import run_metric_reconciliation


def test_live_metric_reconciliation_execution():
    df_rec, df_tax, meta = run_metric_reconciliation()

    assert len(df_rec) == 276
    assert meta["n_resolved"] == 276
    # Derive copula bounds from empirical marginal event indicators:
    # Let A = {actual_high <= upper_P90}, B = {actual_low >= lower_P90}.
    # Joint full-path containment C = A ∩ B satisfies the Fréchet–Hoeffding bounds:
    # max(0, P(A) + P(B) - 1) <= P(A ∩ B) <= min(P(A), P(B))
    p_high = float(df_rec["high_contained"].mean())
    p_low = float(df_rec["low_contained"].mean())
    frechet_lower = max(0.0, p_high + p_low - 1.0) * 100.0
    frechet_upper = min(p_high, p_low) * 100.0

    assert frechet_lower <= meta["path_containment"] <= frechet_upper
    assert meta["path_containment"] > 50.0
    assert len(df_tax) == 6

    # Verify column existence in reconciliation records
    assert "high_contained" in df_rec.columns
    assert "low_contained" in df_rec.columns
    assert "joint_path_contained" in df_rec.columns
    assert "endpoint_contained" in df_rec.columns
