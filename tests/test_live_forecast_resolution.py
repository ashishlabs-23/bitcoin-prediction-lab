"""
tests/test_live_forecast_resolution.py — Unit Tests for 24H Closed Forecast Resolution
======================================================================================
Verifies:
1. Snapshot resolution after 24h forward elapsed period
2. Separate outcome record creation without modifying original snapshot values
3. Path containment logic: Upper Range, Lower Range, Joint Path
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.forecast_session import LiveForecastSession
from engine.forecast_outcome_monitor import ForecastOutcomeRecord


@pytest.fixture
def active_session():
    session = LiveForecastSession(symbol="BTCUSD", horizon="24h")
    session.record_live_forecast(current_price=100000.0, vol_24h=0.015)
    return session


def test_resolve_contained_forecast_outcome(active_session):
    snap = active_session.forecast_snapshots[0]
    rec = active_session.resolve_snapshot_outcome(
        forecast_id=snap.forecast_id,
        forward_candles_high=[100800.0, 101200.0, 101500.0],
        forward_candles_low=[99500.0, 99000.0, 98800.0],
        forward_close=100500.0
    )

    assert isinstance(rec, ForecastOutcomeRecord)
    assert rec.forecast_id == snap.forecast_id
    assert snap.is_resolved is True
    assert rec.upper_covered is True
    assert rec.lower_covered is True
    assert rec.path_contained is True
    assert len(active_session.resolved_outcomes) == 1


def test_resolve_uncontained_forecast_outcome(active_session):
    snap = active_session.forecast_snapshots[0]
    rec = active_session.resolve_snapshot_outcome(
        forecast_id=snap.forecast_id,
        forward_candles_high=[108000.0],  # Major breach of upper range
        forward_candles_low=[99000.0],
        forward_close=107500.0
    )

    assert rec.upper_covered is False
    assert rec.path_contained is False
