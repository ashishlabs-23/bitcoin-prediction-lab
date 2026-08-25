"""
tests/test_model_decay.py — Unit Tests for Model Edge Decay Auditor
===================================================================
Verifies:
1. Audit of error slope, coverage divergence, baseline delta advantage, and drift
2. Confirmation of MODEL_STABLE governance status
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.model_decay import audit_model_decay


def test_model_decay_audit():
    df_decay, meta = audit_model_decay()

    assert len(df_decay) == 5
    assert meta["model_status"] == "MODEL_STABLE"
    assert meta["is_edge_retained"] is True
    assert meta["decay_warning_count"] == 0
