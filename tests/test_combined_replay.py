"""
tests/test_combined_replay.py — Unit Tests for Stratified Replay & Provenance
=============================================================================
Verifies:
1. Exact deterministic reconstruction across stratified market regimes
2. Model and context hash matching
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.combined_production_replay import run_stratified_production_replay


def test_stratified_production_replay():
    df_prov, meta = run_stratified_production_replay()

    assert len(df_prov) == 6
    assert meta["all_hashes_matched"] is True
    assert meta["replay_verdict"] == "PASS"
