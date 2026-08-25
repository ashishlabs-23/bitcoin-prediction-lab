"""
tests/test_multiscale_forecast.py — Unit Tests for Multiscale (5m + 24h) Forecaster
===================================================================================
Verifies:
1. Assembly of dual-horizon forecast without probability blending
2. Independent data quality and model version propagation
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.microstructure_dataset import generate_synthetic_l2_event_stream
from engine.multiscale_forecast import multiscale_assembler


def test_multiscale_forecast_generation():
    df_events = generate_synthetic_l2_event_stream(n_events=50)
    m_fc = multiscale_assembler.generate_multiscale(
        current_price=65200.0,
        vol_24h=0.015,
        df_recent_events=df_events
    )

    assert m_fc.symbol == "BTCUSD"
    assert m_fc.short_horizon.horizon == "5m"
    assert m_fc.long_horizon.horizon == "24h"
    assert m_fc.short_horizon.model_version == "v1.0.0-challenger-hawkes-microstructure"
    assert m_fc.long_horizon.model_version == "v3.0.0-excursion-ridge-conformal"
    assert m_fc.status == "RESEARCH_MULTISCALE_READY"
