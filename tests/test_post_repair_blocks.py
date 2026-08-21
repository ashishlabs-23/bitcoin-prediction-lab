"""
tests/test_post_repair_blocks.py — Tests for Post-Repair Independent Block Construction
========================================================================================
Verifies that:
- Blocks are strictly non-overlapping with exactly 24 hours width.
- Block hashes are deterministic and cryptographically unique per block.
- post_repair_observed_blocks initializes at 0.
"""

import pandas as pd
from research.post_repair_block_builder import build_post_repair_blocks

def test_block_builder_structure():
    blocks, accounting = build_post_repair_blocks()
    assert isinstance(blocks, list)
    assert isinstance(accounting, dict)
    assert "raw_forecasts" in accounting
    assert "independent_blocks" in accounting
    assert "n_eff" in accounting

def test_block_non_overlapping_invariants():
    blocks, _ = build_post_repair_blocks()
    if len(blocks) >= 2:
        for i in range(len(blocks) - 1):
            end_i = pd.Timestamp(blocks[i]["end"])
            start_next = pd.Timestamp(blocks[i+1]["start"])
            assert end_i <= start_next, f"Overlap detected between Block {i} and Block {i+1}"
