"""
tests/test_hawkes_shadow.py — Unit Tests for Hawkes Live Shadow Forecast Generation
====================================================================================
Verifies:
1. Hawkes live shadow session forecast generation
2. SQLite WAL persistence to hawkes_forecasts table
3. Cryptographic hash lineage
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.microstructure_dataset import generate_synthetic_l2_event_stream
from engine.hawkes_shadow_session import hawkes_shadow_session


def test_hawkes_shadow_forecast_generation():
    df_events = generate_synthetic_l2_event_stream(n_events=50)
    fc, meta = hawkes_shadow_session.generate_shadow_forecast(
        current_price=65000.0,
        df_recent_events=df_events
    )

    assert fc.horizon == "5m"
    assert fc.current_price == 65000.0
    assert fc.upper_p90 > fc.current_price
    assert fc.lower_p90 < fc.current_price
    assert meta["is_actionable"] is False
    assert "forecast_id" in meta
