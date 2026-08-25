"""
tests/test_model_disagreement.py — Unit Tests for Model Disagreement Diagnostic
================================================================================
Verifies:
1. Computation of model dispersion metrics across disagreement tiers
2. Verification that disagreement tracks market volatility rather than voting alpha
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.model_disagreement import run_model_disagreement_analysis


def test_model_disagreement_analysis_execution():
    df_dis, meta = run_model_disagreement_analysis()

    assert len(df_dis) == 3
    assert meta["is_independent_factor"] is False
    assert meta["verdict"] == "DISAGREEMENT_TRACKS_VOLATILITY_NOT_NEW_ALPHA"
