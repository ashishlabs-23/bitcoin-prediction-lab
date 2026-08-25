"""
tests/test_foundation_replay.py — Unit Tests for Foundation Model Replay
========================================================================
Verifies:
1. Deterministic reconstruction across TimesFM, Moirai, and Chronos
2. Perfect match across model hash and replayed predictions
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.foundation_replay import audit_foundation_model_replay


def test_foundation_model_replay_audit():
    df_rep, meta = audit_foundation_model_replay()

    assert len(df_rep) == 4
    assert meta["all_replays_passed"] is True
