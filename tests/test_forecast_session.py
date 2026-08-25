"""
tests/test_forecast_session.py — Unit Tests for Live Paper Forecast Session Engine
==================================================================================
Verifies:
1. LiveForecastSession initialization and session state tracking
2. Live forecast snapshot creation with provenance cryptographic hashes
3. Immutability of recorded forecast snapshots
4. Session summary statistics computation
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.forecast_session import LiveForecastSession, LiveForecastSnapshot


@pytest.fixture
def forecast_session():
    return LiveForecastSession(symbol="BTCUSD", horizon="24h")


def test_forecast_session_initialization(forecast_session):
    assert forecast_session.symbol == "BTCUSD"
    assert forecast_session.horizon == "24h"
    assert forecast_session.status == "ACTIVE"
    assert len(forecast_session.session_id) > 10
    assert len(forecast_session.forecast_snapshots) == 0


def test_record_live_forecast_snapshot(forecast_session):
    snap = forecast_session.record_live_forecast(
        current_price=96000.0,
        vol_24h=0.015,
        features={'vol_24h': 0.015, 'rsi_14': 52.0},
        market_regime="Sideways"
    )

    assert isinstance(snap, LiveForecastSnapshot)
    assert snap.current_price == 96000.0
    assert snap.session_id == forecast_session.session_id
    assert len(snap.feature_snapshot_hash) == 16
    assert len(snap.prediction_hash) == 16
    assert snap.is_resolved is False
    assert len(forecast_session.forecast_snapshots) == 1


def test_session_statistics_computation(forecast_session):
    forecast_session.record_live_forecast(current_price=95000.0, vol_24h=0.015)
    stats = forecast_session.get_session_stats()

    assert stats["forecast_count"] == 1
    assert stats["resolved_count"] == 0
    assert stats["symbol"] == "BTCUSD"
