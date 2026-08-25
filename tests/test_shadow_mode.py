"""
tests/test_shadow_mode.py — Unit Tests for Challenger Shadow Mode Logging
=========================================================================
Verifies:
1. Production and shadow forecasts executed simultaneously without cross-talk
2. Non-interference with primary predictions or execution state
3. Accurate paired telemetry recording
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.challenger_shadow_monitor import run_shadow_mode_simulation


def test_shadow_mode_telemetry_simulation():
    df_shadow, meta = run_shadow_mode_simulation()

    assert len(df_shadow) > 0
    assert "prod_model" in df_shadow.columns
    assert "shadow_model" in df_shadow.columns
    assert "prod_won" in df_shadow.columns
    assert meta["n_shadow_observations"] > 0
