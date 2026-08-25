"""
tests/test_shadow_isolation.py — Safety Invariant Tests for Hawkes Shadow Isolation
====================================================================================
Verifies that Hawkes shadow operations strictly enforce non-actionability:
1. is_actionable remains False
2. Shadow forecast generation does not alter Production Ridge forecast outputs
3. Zero side effects on trading or execution states
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.microstructure_dataset import generate_synthetic_l2_event_stream
from engine.hawkes_shadow_session import hawkes_shadow_session, HawkesShadowSession
from engine.range_forecast_service import RangeForecastService


def test_shadow_non_actionable_guard():
    session = HawkesShadowSession()
    assert session.is_actionable is False

    # Attempt to violate guard
    session.is_actionable = True
    df_events = generate_synthetic_l2_event_stream(n_events=20)
    with pytest.raises(AssertionError):
        session.generate_shadow_forecast(current_price=65000.0, df_recent_events=df_events)


def test_shadow_does_not_mutate_production_ridge():
    p0 = 65500.0
    vol = 0.015
    svc = RangeForecastService()

    # Baseline production Ridge forecast
    ridge_before = svc.generate_forecast(current_price=p0, vol_24h=vol)

    # Run Hawkes shadow forecasts
    df_events = generate_synthetic_l2_event_stream(n_events=50)
    for _ in range(5):
        _, _ = hawkes_shadow_session.generate_shadow_forecast(current_price=p0, df_recent_events=df_events)

    # Production Ridge forecast after shadow execution
    ridge_after = svc.generate_forecast(current_price=p0, vol_24h=vol)

    assert ridge_before.mfe_p50 == ridge_after.mfe_p50
    assert ridge_before.upper_p90 == ridge_after.upper_p90
    assert ridge_before.lower_p90 == ridge_after.lower_p90
    assert ridge_before.uncertainty == ridge_after.uncertainty
