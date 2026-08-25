"""
tests/test_interval_sharpness.py — Unit Tests for Interval Sharpness & Winkler Scores
=====================================================================================
Verifies:
1. Winkler interval score calculation
2. Range width and coverage efficiency metrics
"""

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.interval_sharpness import calculate_winkler_score, run_interval_sharpness_audit


def test_winkler_score_properties():
    # Perfectly contained target in the middle of [90, 110]
    low = np.array([90.0])
    up = np.array([110.0])
    target = np.array([100.0])
    score_inside = calculate_winkler_score(low, up, target, alpha=0.10)
    assert score_inside == 20.0  # Width only

    # Breached target at 120 (10 points above upper)
    target_breach = np.array([120.0])
    score_breach = calculate_winkler_score(low, up, target_breach, alpha=0.10)
    assert score_breach == 20.0 + (2.0 / 0.10) * 10.0  # 20 + 200 = 220.0


def test_interval_sharpness_audit_execution():
    df_sharp, meta = run_interval_sharpness_audit()
    assert len(df_sharp) == 4
    assert "Mean Width %" in df_sharp.columns
    assert "Winkler Score ($)" in df_sharp.columns
