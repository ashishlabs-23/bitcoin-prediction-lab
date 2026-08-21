"""
tests/test_independent_blocks.py — Unit Tests for Independent Block Partitioning
================================================================================
Verifies:
1. Exact non-overlapping 24h block calculation
2. Effective sample size calculation under lag-1 autocorrelation
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.independent_block_builder import independent_block_builder


def test_independent_block_partitioning():
    res = independent_block_builder.partition_into_blocks(raw_forecast_count=744, block_duration_hours=24)

    assert res["raw_forecast_count"] == 744
    assert res["independent_blocks"] == 31
    assert 29.0 <= res["effective_sample_size"] <= 31.0
    assert res["is_independent"] is True
