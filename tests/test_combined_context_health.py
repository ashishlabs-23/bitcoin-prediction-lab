"""
tests/test_combined_context_health.py — Unit Tests for 6-Pillar Combined Production Health
===========================================================================================
Verifies:
1. Operational status of all 6 health pillars
2. Overall HEALTHY system assessment
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.combined_context_health import evaluate_combined_production_health


def test_combined_production_health_evaluation():
    df_h, meta = evaluate_combined_production_health()

    assert len(df_h) == 6
    assert meta["overall_status"] == "HEALTHY"
    assert meta["pillars_passed"] == 6
    assert meta["is_all_healthy"] is True
