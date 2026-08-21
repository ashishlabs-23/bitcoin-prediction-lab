"""
tests/test_block_quality.py — Tests for Quality-Stratified Block Construction
=============================================================================
Verifies that:
- Block builder computes stratified accounting (valid, mixed, degraded blocks).
- Blocks CSV contains block_quality column.
- Only VALID blocks have validation_eligible = True.
"""

import os
from research.post_repair_block_builder import build_post_repair_blocks, BLOCKS_CSV_PATH

def test_block_quality_stratification():
    blocks, accounting = build_post_repair_blocks()
    assert "independent_valid_blocks" in accounting
    assert "independent_mixed_blocks" in accounting
    assert "independent_degraded_blocks" in accounting
    assert os.path.exists(BLOCKS_CSV_PATH)
    
    for b in blocks:
        assert "block_quality" in b
        if b["block_quality"] == "VALID":
            assert b["validation_eligible"] is True
        else:
            assert b["validation_eligible"] is False
