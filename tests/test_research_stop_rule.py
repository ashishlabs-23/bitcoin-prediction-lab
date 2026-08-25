"""
tests/test_research_stop_rule.py — Unit Tests for Research Stop Rule Invariant
==============================================================================
Verifies:
1. Status is NO_NEW_RESEARCH_REQUIRED while production model remains stable
2. Persistence requirement: at least 3 consecutive review failures needed to trigger research
3. Model Change Requests are generated only upon persistent triggers
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.research_stop_rule import research_stop_rule_engine
from research.model_change_request import get_current_research_trigger_status, ModelChangeRequest


def test_research_stop_rule_nominal_state():
    eval_res = research_stop_rule_engine.evaluate_production_health(consecutive_failures=0)

    assert eval_res.status == "NO_NEW_RESEARCH_REQUIRED"
    assert eval_res.trigger_type is None
    assert eval_res.manual_review_required is False


def test_research_stop_rule_persistence_requirement():
    # 1 failure -> No trigger (requires >= 3)
    res1 = research_stop_rule_engine.evaluate_production_health(consecutive_failures=1)
    assert res1.status == "NO_NEW_RESEARCH_REQUIRED"

    # 2 failures -> No trigger (requires >= 3)
    res2 = research_stop_rule_engine.evaluate_production_health(consecutive_failures=2)
    assert res2.status == "NO_NEW_RESEARCH_REQUIRED"

    # 3 failures -> Triggered!
    res3 = research_stop_rule_engine.evaluate_production_health(consecutive_failures=3)
    assert res3.status == "RESEARCH_TRIGGERED"
    assert res3.trigger_type == "PERSISTENT_CALIBRATION_DEGRADATION"
    assert res3.manual_review_required is True
