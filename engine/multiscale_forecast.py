"""
engine/multiscale_forecast.py — Multiscale (5m Hawkes + 24h Ridge) Forecast Assembler
=====================================================================================
Synchronizes dual-horizon predictions without probability blending:
1. Long-Horizon Layer (24h): Production Ridge Conformal Regressor (Primary Validated Product)
2. Short-Horizon Layer (5m): Hawkes Microstructure Shadow Challenger (Research Overlay)
3. Preserves mathematical independence between structural 24h ranges and high-frequency 5m excursions
"""

import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.interfaces.multiscale_forecaster import (
    MultiscaleForecaster,
    ShortHorizonForecast,
    LongHorizonForecast,
    MultiscaleForecast
)
from engine.range_forecast_service import RangeForecastService, BTCUSDRangeForecast
from engine.hawkes_shadow_session import hawkes_shadow_session


class MultiscaleForecastAssembler(MultiscaleForecaster):
    """
    Assembles dual-horizon multiscale forecasts without probability blending.
    """

    def __init__(self):
        self.ridge_service = RangeForecastService()

    def assemble_multiscale_forecast(
        self,
        short_state: ShortHorizonForecast,
        long_state: LongHorizonForecast
    ) -> MultiscaleForecast:
        now_iso = datetime.now(timezone.utc).isoformat()
        overall_quality = "VALID" if (short_state.data_quality == "VALID" and long_state.data_quality == "VALID") else "DEGRADED"

        return MultiscaleForecast(
            timestamp=now_iso,
            symbol="BTCUSD",
            current_price=long_state.current_price,
            short_horizon=short_state,
            long_horizon=long_state,
            overall_data_quality=overall_quality,
            status="RESEARCH_MULTISCALE_READY"
        )

    def generate_multiscale(
        self,
        current_price: float,
        vol_24h: float,
        df_recent_events: Any
    ) -> MultiscaleForecast:
        # 1. 24h Production Ridge
        ridge_fc = self.ridge_service.generate_forecast(current_price=current_price, vol_24h=vol_24h)
        long_state = LongHorizonForecast(
            horizon="24h",
            current_price=current_price,
            mfe_p10=ridge_fc.mfe_p10,
            mfe_p50=ridge_fc.mfe_p50,
            mfe_p90=ridge_fc.mfe_p90,
            mae_p10=ridge_fc.mae_p10,
            mae_p50=ridge_fc.mae_p50,
            mae_p90=ridge_fc.mae_p90,
            upper_p90=ridge_fc.upper_p90,
            lower_p90=ridge_fc.lower_p90,
            direction_state=ridge_fc.direction_state,
            uncertainty=ridge_fc.uncertainty,
            model_version=ridge_fc.model_version,
            data_quality=ridge_fc.data_quality
        )

        # 2. 5m Hawkes Shadow
        short_state, _ = hawkes_shadow_session.generate_shadow_forecast(
            current_price=current_price,
            df_recent_events=df_recent_events
        )

        return self.assemble_multiscale_forecast(short_state, long_state)


multiscale_assembler = MultiscaleForecastAssembler()
