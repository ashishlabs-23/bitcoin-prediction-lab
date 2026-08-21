"""
tests/test_intermediate_validation.py — Unit Tests for Intermediate Horizon Validation Synthesis
================================================================================================
Verifies:
1. Complete intermediate horizon validation synthesis
2. Final governance verdict CASE B (5m decays, but derivatives/volatility bridge to 4h)
3. Retention of Ridge as 24h Production and Hawkes as 5m Validated Shadow
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.intermediate_horizon_validation import run_intermediate_horizon_validation


def test_intermediate_horizon_validation_synthesis():
    df_s, meta = run_intermediate_horizon_validation()

    assert len(df_s) == 2
    assert meta["verdict"] == "CASE_B_5M_DECAYS_BUT_DERIVATIVES_VOLATILITY_BRIDGE_TO_4H"
    assert meta["ridge_status"] == "PRODUCTION"
    assert meta["hawkes_status"] == "VALIDATED_SHADOW_MODEL"
    assert meta["intermediate_status"] == "RESEARCH_ONLY"
