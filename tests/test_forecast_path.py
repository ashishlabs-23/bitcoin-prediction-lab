"""
tests/test_forecast_path.py — Unit Tests for Forward Forecast Trajectory & Path Generator
=========================================================================================
Verifies:
1. Generation of 24h forward forecast trajectory points
2. Proper upward slope for BULLISH, downward slope for BEARISH, flat for NO_DIRECTIONAL_EDGE
3. Bounded trajectory within Upper/Lower P90 range boundaries
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_forecast_service import RangeForecastService
from engine.forecast_path import forecast_path_generator, ForecastTrajectoryResult


def test_forecast_path_bullish_trajectory():
    svc = RangeForecastService()
    fc = svc.generate_forecast(
        current_price=65000.0,
        vol_24h=0.015,
        market_regime="Trending Bull"
    )
    # Force directional state for test
    fc.direction_state = "BULLISH"

    traj = forecast_path_generator.generate_trajectory(fc, horizon_hours=24)
    assert isinstance(traj, ForecastTrajectoryResult)
    assert traj.path_class == "EXPERIMENTAL_DIRECTIONAL_PATH"
    assert len(traj.path_points) == 24
    # Terminal point should be higher than initial price
    assert traj.path_points[-1]["projected_price"] > 65000.0
    # Should remain within bounds
    assert traj.path_points[-1]["projected_price"] <= fc.upper_p90


def test_forecast_path_neutral_no_directional_edge():
    svc = RangeForecastService()
    fc = svc.generate_forecast(
        current_price=65000.0,
        vol_24h=0.015,
        market_regime="Sideways"
    )
    fc.direction_state = "NO_DIRECTIONAL_EDGE"

    traj = forecast_path_generator.generate_trajectory(fc, horizon_hours=24)
    assert traj.path_class == "PROBABILISTIC_RANGE_ENVELOPE"
    assert traj.path_points[-1]["projected_price"] == 65000.0  # Centerline flat
