"""
tests/test_horizon_4h.py — Unit Tests for 4-Hour Horizon Audit & Derivatives Bridging
====================================================================================
Verifies:
1. 4h horizon audit execution across 5 predefined feature variants
2. Verification of insufficient longitudinal sample size (N_eff = 30 < 100)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.horizon_4h_audit import audit_horizon_4h


def test_horizon_4h_audit_execution():
    df_4h, meta = audit_horizon_4h()

    assert len(df_4h) == 5
    assert meta["n_eff"] == 30
    assert meta["governance_status"] == "INSUFFICIENT_LONGITUDINAL_EVIDENCE"
    assert "Model E" in meta["best_4h_model"]
