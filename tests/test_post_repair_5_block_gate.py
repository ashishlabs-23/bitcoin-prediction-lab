"""
tests/test_post_repair_5_block_gate.py — Tests for 5-Block Milestone Gate
========================================================================
Verifies:
- Gate returns WAITING_FOR_5_POST_REPAIR_BLOCKS when observed_blocks < 5.
- Milestone 5 report exists and follows Zero-Projection policy.
"""

import os
from research.milestone_5_post_repair_gate import evaluate_milestone_5_gate, REPORT_PATH

def test_milestone_5_gate_evaluation():
    res = evaluate_milestone_5_gate()
    assert res["decision"] == "WAITING_FOR_5_POST_REPAIR_BLOCKS"
    assert res["observed_blocks"] < 5
    assert os.path.exists(REPORT_PATH)

    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    assert "TARGET / NOT YET OBSERVED" in content
    assert "Zero-Projection Policy" in content
