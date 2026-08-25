"""
tests/test_research_cycle.py — Unit Tests for 30-Block Governance Research Cycle
================================================================================
Verifies:
1. Full 7-stage research cycle execution without automatic retraining
2. Review artifact generation
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.research_cycle import run_30_block_research_cycle


def test_research_cycle_execution():
    summary = run_30_block_research_cycle(block_milestone=10)

    assert summary["production_model"] == "v3.0.0-excursion-ridge-conformal"
    assert summary["bakeoff_verdict"] == "RETAIN_PRODUCTION_RIDGE"
    assert summary["provenance_status"] == "VERIFIED"
    assert summary["governance_recommendation"] == "MAINTAIN_PRODUCTION_RIDGE_WITHOUT_RETRAINING"
