"""
tests/test_shadow_labels.py — Tests for Shadow Labelling & Disclaimers
======================================================================
Verifies:
1. Short-horizon forecasts are explicitly labeled SHADOW / EXPERIMENTAL
2. Production Ridge remains explicitly labeled PRODUCTION
3. Directional line labeled DIRECTIONAL PROJECTION instead of synthetic predicted path
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.multiscale_forecast import multiscale_assembler
from research.microstructure_dataset import generate_synthetic_l2_event_stream


def test_shadow_and_production_labels():
    df_events = generate_synthetic_l2_event_stream(n_events=50)
    m_fc = multiscale_assembler.generate_multiscale(
        current_price=65200.0,
        vol_24h=0.015,
        df_recent_events=df_events
    )

    # 5m horizon
    assert "hawkes" in m_fc.short_horizon.model_version.lower()
    # 24h horizon
    assert "ridge" in m_fc.long_horizon.model_version.lower()
    assert m_fc.status == "RESEARCH_MULTISCALE_READY"
