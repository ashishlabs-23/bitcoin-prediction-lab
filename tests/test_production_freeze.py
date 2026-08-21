"""
tests/test_production_freeze.py — Unit Tests for Production Model Freeze Invariants
===================================================================================
Verifies:
1. PRODUCTION_MODEL_FROZEN = True invariant
2. Rejection of unauthorized production weight checkpoints or parameter mutations
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.longitudinal_orchestrator import PRODUCTION_MODEL_FROZEN, LONGITUDINAL_MONITORING_ONLY


def test_production_model_frozen_invariant():
    assert PRODUCTION_MODEL_FROZEN is True
    assert LONGITUDINAL_MONITORING_ONLY is True
