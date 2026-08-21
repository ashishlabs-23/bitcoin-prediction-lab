"""
tests/test_volatility_context_point_in_time.py — Unit Tests for Point-in-Time & Provenance
==========================================================================================
Verifies:
1. Strict causal ordering of volatility term-structure inputs
2. Untouched confirmation window and zero contamination
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.volatility_context_provenance import audit_volatility_context_provenance


def test_volatility_context_provenance():
    prov = audit_volatility_context_provenance()

    assert prov["is_confirmation_untouched"] is True
    assert prov["contamination_status"] == "CLEAN_UNCONTAMINATED"
    assert prov["verification_result"] == "PASS"
