"""
engine/forecast_path.py — Forward BTCUSD Forecast Trajectory & Range Path Generator
===================================================================================
Constructs point-in-time forward 24-hour forecast paths:
1. Derives trajectory from Range Forecast (MFE/MAE bounds) + Directional Evidence Overlay
2. Directional Trajectories:
   - BULLISH: Upward drift reaching median MFE target at horizon
   - BEARISH: Downward drift reaching median MAE target at horizon
   - NO_DIRECTIONAL_EDGE / NEUTRAL: Mean-preserving baseline with symmetric conformal expansion
3. Emits 24 hourly trajectory points: median_path, upper_p90_path, lower_p90_path, and uncertainty band
4. Includes historical realized vs forecast comparison resolution
"""

import os
import sys
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_forecast_service import BTCUSDRangeForecast

logger = logging.getLogger("btcognitive.forecast_path")


@dataclass
class ForecastPathPoint:
    step_hour: int
    projected_price: float
    upper_p90: float
    lower_p90: float
    median_price: float
    uncertainty: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ForecastTrajectoryResult:
    current_price: float
    horizon_hours: int
    direction_state: str  # BULLISH, BEARISH, NEUTRAL, NO_DIRECTIONAL_EDGE, LOW_CONFIDENCE
    path_class: str  # EXPERIMENTAL_DIRECTIONAL_PATH or PROBABILISTIC_RANGE_ENVELOPE
    path_points: List[Dict[str, Any]]
    expected_mfe_p50_pct: float
    expected_mae_p50_pct: float
    upper_p90_terminal: float
    lower_p90_terminal: float
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ForecastPathGenerator:
    """
    Constructs deterministic forward 24h forecast trajectories.
    """

    def generate_trajectory(
        self,
        range_forecast: BTCUSDRangeForecast,
        horizon_hours: int = 24
    ) -> ForecastTrajectoryResult:
        p0 = range_forecast.current_price
        dir_state = range_forecast.direction_state
        mfe_50 = range_forecast.mfe_p50
        mae_50 = range_forecast.mae_p50
        unc = range_forecast.uncertainty

        points: List[Dict[str, Any]] = []

        # Classification label
        if dir_state in ["BULLISH", "BEARISH"]:
            path_class = "EXPERIMENTAL_DIRECTIONAL_PATH"
        else:
            path_class = "PROBABILISTIC_RANGE_ENVELOPE"

        for h in range(1, horizon_hours + 1):
            time_fraction = np.sqrt(h / horizon_hours)  # Diffusion scaling

            # Conformal bounds expand with sqrt(t)
            upper_h = p0 * (1.0 + (range_forecast.mfe_p90 * time_fraction))
            lower_h = p0 * (1.0 - (range_forecast.mae_p90 * time_fraction))
            median_h = p0

            if dir_state == "BULLISH":
                # Upward trajectory towards MFE P50
                projected_h = p0 * (1.0 + (mfe_50 * (h / horizon_hours)))
            elif dir_state == "BEARISH":
                # Downward trajectory towards MAE P50
                projected_h = p0 * (1.0 - (mae_50 * (h / horizon_hours)))
            else:
                # No directional edge - center line remains neutral
                projected_h = p0

            point = ForecastPathPoint(
                step_hour=h,
                projected_price=round(projected_h, 2),
                upper_p90=round(upper_h, 2),
                lower_p90=round(lower_h, 2),
                median_price=round(median_h, 2),
                uncertainty=round(unc * time_fraction, 2)
            )
            points.append(point.to_dict())

        return ForecastTrajectoryResult(
            current_price=p0,
            horizon_hours=horizon_hours,
            direction_state=dir_state,
            path_class=path_class,
            path_points=points,
            expected_mfe_p50_pct=round(mfe_50 * 100.0, 4),
            expected_mae_p50_pct=round(mae_50 * 100.0, 4),
            upper_p90_terminal=range_forecast.upper_p90,
            lower_p90_terminal=range_forecast.lower_p90,
            status="SUCCESS"
        )


forecast_path_generator = ForecastPathGenerator()
