"""
tests/test_production_integrity.py — Unit Tests for 13-Point Readiness & Scorecard
===================================================================================
Verifies:
1. 13-Point production readiness checklist outputs READY
2. Longitudinal durability scorecard execution
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.production_readiness import run_production_readiness_audit
from research.longitudinal_scorecard import generate_longitudinal_scorecard


def test_production_readiness_checklist_ready():
    df_check, verdict = run_production_readiness_audit()
    assert verdict == "READY"
    assert len(df_check) == 13
    assert all(df_check["Status"] == "PASS")


def test_longitudinal_durability_scorecard():
    df_score, meta = generate_longitudinal_scorecard()
    assert len(df_score) >= 4
    assert meta["current_state"] == "MODEL_STABLE"
