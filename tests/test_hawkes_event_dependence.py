"""
tests/test_hawkes_event_dependence.py — Unit Tests for Event Dependence & Cooldown Filtering
============================================================================================
Verifies:
1. Event dependence robustness across filtered cooldown streams
2. Confirmation that signal survives de-clustering
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.hawkes_event_dependence import evaluate_event_dependence_robustness


def test_hawkes_event_dependence_robustness():
    df_res, meta = evaluate_event_dependence_robustness()

    assert len(df_res) == 3
    assert meta["is_burst_dependent"] is False
    assert meta["general_microstructure_signal"] is True
