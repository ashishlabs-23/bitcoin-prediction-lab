"""
tests/test_volatility_context_ab.py — Unit Tests for Production A/B Replay
==========================================================================
Verifies:
1. Exact side-by-side A/B execution on identical feature snapshots
2. Preservation of the -14 bps MFE delta
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.volatility_context_ab_test import run_volatility_context_ab_replay


def test_volatility_context_ab_replay_execution():
    df_ab, meta = run_volatility_context_ab_replay()

    assert len(df_ab) == 5
    assert meta["mfe_delta_bps"] == -14.0
    assert meta["replay_status"] == "DETERMINISTIC_MATCH"
