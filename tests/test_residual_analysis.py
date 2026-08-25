"""
tests/test_residual_analysis.py — Unit Tests for Production Residual & Blind Spot Audit
=======================================================================================
Verifies:
1. Analysis of out-of-sample prediction residuals across regimes and seasonal factors
2. Confirmation that no persistent systematic blind spots exist (p > 0.25)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.production_residual_analysis import run_production_residual_analysis
from research.foundation_usefulness import evaluate_foundation_usefulness_roles


def test_production_residual_blind_spot_audit():
    df_res, meta = run_production_residual_analysis()

    assert len(df_res) == 5
    assert meta["is_blind_spot_detected"] is False
    assert meta["verdict"] == "NO_PERSISTENT_BLIND_SPOTS_DETECTED"


def test_foundation_usefulness_evaluation():
    df_roles, meta = evaluate_foundation_usefulness_roles()

    assert len(df_roles) == 5
    assert meta["final_case"] == "CASE_A_FOUNDATION_MODELS_ADD_NO_USEFUL_RESIDUAL_INFO"
    assert meta["verdict"] == "FREEZE_ARCHITECTURE_CONTINUE_LONGITUDINAL_MONITORING"
