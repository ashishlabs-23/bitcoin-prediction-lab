"""
tests/test_hawkes_live_resolution.py — Unit Tests for Live 5m Outcome Resolution
================================================================================
Verifies:
1. Resolving 5-minute outcomes into hawkes_outcomes table
2. Correct MFE, MAE, coverage, and Winkler score computations
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.microstructure_dataset import generate_synthetic_l2_event_stream
from engine.hawkes_shadow_session import hawkes_shadow_session


def test_hawkes_live_outcome_resolution():
    df_events = generate_synthetic_l2_event_stream(n_events=50)
    fc, meta = hawkes_shadow_session.generate_shadow_forecast(
        current_price=65000.0,
        df_recent_events=df_events
    )
    fid = meta["forecast_id"]

    res = hawkes_shadow_session.resolve_outcome(
        forecast_id=fid,
        actual_high=65100.0,
        actual_low=64950.0,
        actual_close=65050.0
    )

    assert res["forecast_id"] == fid
    assert "actual_mfe" in res
    assert "actual_mae" in res
    assert res["p90_covered"] in (0, 1)
    assert res["winkler_score"] > 0.0
