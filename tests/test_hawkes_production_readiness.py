"""
tests/test_hawkes_production_readiness.py — Unit Tests for 12-Point Readiness Audit
===================================================================================
Verifies:
1. Complete execution of the 12-point production readiness audit
2. Accurate enforcement of minimum sample scale (N_eff >= 250)
3. Correct decision assignment (CASE B: technically passes, awaiting longitudinal evidence)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.hawkes_production_readiness import evaluate_hawkes_production_readiness


def test_hawkes_readiness_current_insufficient_sample():
    df_readiness, meta = evaluate_hawkes_production_readiness(n_effective_samples=135, min_required_samples=250)

    assert len(df_readiness) == 12
    assert meta["overall_decision"] == "CASE_B_TECHNICALLY_PASSES_AWAITING_LONGITUDINAL_EVIDENCE"
    assert meta["governance_action"] == "RETAIN_VALIDATED_SHADOW_MODEL"


def test_hawkes_readiness_sufficient_sample():
    df_readiness, meta = evaluate_hawkes_production_readiness(n_effective_samples=300, min_required_samples=250)

    assert meta["overall_decision"] == "CASE_A_PRODUCTION_READY"
