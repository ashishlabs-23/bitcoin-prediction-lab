"""
tests/test_event_independence.py — Unit Tests for Event Clustering & Effective Sample Size
==========================================================================================
Verifies:
1. Event cluster identification
2. Bretherton / Thiébaux N_eff calculation and export
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.microstructure_dataset import generate_synthetic_l2_event_stream
from research.event_independence import analyze_event_independence


def test_event_independence_analysis():
    df_events = generate_synthetic_l2_event_stream(n_events=200)
    df_res, meta = analyze_event_independence(df_events, cluster_threshold_ms=300)

    assert len(df_res) >= 6
    assert meta["n_events"] == 200
    assert meta["n_clusters"] > 0
    assert meta["n_eff"] > 0
