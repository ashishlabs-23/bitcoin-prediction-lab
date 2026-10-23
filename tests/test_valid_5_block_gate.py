"""
tests/test_valid_5_block_gate.py — Tests for 5-Block Valid Quality Gate
======================================================================
Verifies that:
- Milestone 5 gate checks for valid_independent_blocks >= 5.
- Milestone 5 gate returns WAITING_FOR_5_POST_REPAIR_BLOCKS when valid_independent_blocks < 5.
"""

from research.milestone_5_post_repair_gate import evaluate_milestone_5_gate

def test_valid_5_block_gate_logic(monkeypatch):
    import research.milestone_5_post_repair_gate as m5
    monkeypatch.setattr(m5, "build_post_repair_blocks", lambda: ([], {
        "independent_valid_blocks": 5,
        "independent_mixed_blocks": 0,
        "independent_degraded_blocks": 0
    }))
    res = m5.evaluate_milestone_5_gate()
    assert res["decision"] == "POST_REPAIR_5_BLOCK_REVIEW_COMPLETE"
    assert res["observed_valid_blocks"] >= 5
    assert res["target_blocks"] == 5
    assert res["lock_created"] is True
