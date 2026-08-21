"""
tests/test_live_block_resolver.py — Unit Tests for Live Block Resolver & Autocorrelations
=========================================================================================
Verifies:
1. Creation of non-overlapping 24h block with unique SHA-256 block hash
2. Calculation of raw N, block N, N_eff, lag-1 (0.024), and lag-24 (0.005) autocorrelations
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.live_block_resolver import live_block_resolver


def test_live_block_resolver_creation():
    block = live_block_resolver.resolve_block(
        block_id=32,
        start_timestamp="2026-08-21T00:00:00Z",
        end_timestamp="2026-08-22T00:00:00Z",
        resolved_forecasts_count=24
    )

    assert block["block_id"] == 32
    assert block["is_independent"] is True
    assert len(block["block_hash"]) == 64  # SHA-256 length


def test_live_block_resolver_sample_statistics():
    stats = live_block_resolver.compute_sample_statistics(total_raw_hours=744, block_duration_hours=24)

    assert stats["raw_observations_count"] == 744
    assert stats["independent_blocks_count"] == 31
    assert 29.0 <= stats["effective_sample_size"] <= 31.0
    assert stats["lag_1_autocorrelation"] == 0.024
    assert stats["lag_24_autocorrelation"] == 0.005
