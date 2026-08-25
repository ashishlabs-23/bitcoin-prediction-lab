"""
tests/test_horizon_1h.py — Unit Tests for 1-Hour Horizon Audit & Ablation
========================================================================
Verifies:
1. 1h horizon audit execution across 5 predefined feature variants
2. Verification of insufficient longitudinal sample size (N_eff = 48 < 150)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.horizon_1h_audit import audit_horizon_1h


def test_horizon_1h_audit_execution():
    df_1h, meta = audit_horizon_1h()

    assert len(df_1h) == 5
    assert meta["n_eff"] == 48
    assert meta["governance_status"] == "INSUFFICIENT_LONGITUDINAL_EVIDENCE"
    assert "Model E" in meta["best_1h_model"]
