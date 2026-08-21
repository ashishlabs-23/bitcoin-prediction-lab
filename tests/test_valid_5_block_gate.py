"""
tests/test_valid_5_block_gate.py — Tests for 5-Block Valid Quality Gate
======================================================================
Verifies that:
- Milestone 5 gate checks for valid_independent_blocks >= 5.
- Milestone 5 gate returns WAITING_FOR_5_POST_REPAIR_BLOCKS when valid_independent_blocks < 5.
"""

from research.milestone_5_post_repair_gate import evaluate_milestone_5_gate

def test_valid_5_block_gate_logic():
    res = evaluate_milestone_5_gate()
    assert res["decision"] == "WAITING_FOR_5_POST_REPAIR_BLOCKS"
    assert res["observed_valid_blocks"] < 5
    assert res["target_blocks"] == 5
    assert res["lock_created"] is False
