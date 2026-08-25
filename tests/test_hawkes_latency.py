"""
tests/test_hawkes_latency.py — Unit Tests for Pipeline Latency & Shadow Mode Isolation
=======================================================================================
Verifies:
1. End-to-end pipeline latency remains within <10ms budget
2. Shadow mode execution logs predictions without modifying production
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.hawkes_latency_audit import run_hawkes_latency_audit
from research.hawkes_shadow_evaluation import run_hawkes_shadow_evaluation


def test_hawkes_pipeline_latency_within_budget():
    df_lat, meta = run_hawkes_latency_audit()

    assert len(df_lat) == 5
    assert meta["total_latency_ms"] < 10.0
    assert all(df_lat["Status"] == "PASS")


def test_hawkes_shadow_mode_isolation():
    df_s, meta = run_hawkes_shadow_evaluation(n_steps=10)

    assert len(df_s) == 10
    assert meta["production_modified"] is False
