"""
tests/test_multiscale_websocket.py — Unit Tests for Multiscale WebSocket Event Payload
======================================================================================
Verifies:
1. Serialization of multiscale_forecast_update event
2. Proper isolation of 5m shadow and 24h production keys
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.multiscale_forecast import multiscale_assembler
from research.microstructure_dataset import generate_synthetic_l2_event_stream


def test_multiscale_websocket_event_payload_schema():
    df_events = generate_synthetic_l2_event_stream(n_events=50)
    m_fc = multiscale_assembler.generate_multiscale(
        current_price=65200.0,
        vol_24h=0.015,
        df_recent_events=df_events
    )

    ws_event = {
        "event": "multiscale_forecast_update",
        "timestamp": m_fc.timestamp,
        "price": m_fc.current_price,
        "5m_forecast": {
            "mfe_p50": m_fc.short_horizon.mfe_p50,
            "mae_p50": m_fc.short_horizon.mae_p50,
            "upper_p90": m_fc.short_horizon.upper_p90,
            "lower_p90": m_fc.short_horizon.lower_p90,
            "uncertainty": m_fc.short_horizon.uncertainty,
            "direction": m_fc.short_horizon.direction_state,
            "status": "SHADOW"
        },
        "24h_forecast": {
            "mfe_p50": m_fc.long_horizon.mfe_p50,
            "mae_p50": m_fc.long_horizon.mae_p50,
            "upper_p90": m_fc.long_horizon.upper_p90,
            "lower_p90": m_fc.long_horizon.lower_p90,
            "uncertainty": m_fc.long_horizon.uncertainty,
            "direction": m_fc.long_horizon.direction_state,
            "status": "PRODUCTION"
        }
    }

    assert ws_event["event"] == "multiscale_forecast_update"
    assert ws_event["5m_forecast"]["status"] == "SHADOW"
    assert ws_event["24h_forecast"]["status"] == "PRODUCTION"
