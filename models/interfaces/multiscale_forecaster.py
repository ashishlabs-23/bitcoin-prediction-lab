"""
models/interfaces/multiscale_forecaster.py — Canonical Multiscale Data Contracts
================================================================================
Defines the uniform data contracts for decoupled dual-horizon forecasting:
1. ShortHorizonForecast (5-minute Hawkes / LOB dynamics)
2. LongHorizonForecast (24-hour Production Ridge Conformal range)
3. MultiscaleForecast (Synchronized dual-horizon container without probability blending)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class MultiscaleForecastResult:
    short_term_horizon: str
    short_term_mfe_p50: float
    short_term_mae_p50: float
    short_term_direction: str
    long_term_horizon: str
    long_term_mfe_p50: float
    long_term_mae_p50: float
    long_term_direction: str
    multiscale_uncertainty: float
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShortHorizonForecast:
    horizon: str  # e.g., "5m"
    current_price: float
    mfe_p10: float
    mfe_p50: float
    mfe_p90: float
    mae_p10: float
    mae_p50: float
    mae_p90: float
    upper_p90: float
    lower_p90: float
    direction_state: str  # BULLISH, BEARISH, NEUTRAL, NO_EDGE
    uncertainty: float
    model_version: str
    data_quality: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LongHorizonForecast:
    horizon: str  # e.g., "24h"
    current_price: float
    mfe_p10: float
    mfe_p50: float
    mfe_p90: float
    mae_p10: float
    mae_p50: float
    mae_p90: float
    upper_p90: float
    lower_p90: float
    direction_state: str
    uncertainty: float
    model_version: str
    data_quality: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MultiscaleForecast:
    timestamp: str
    symbol: str
    current_price: float
    short_horizon: ShortHorizonForecast
    long_horizon: LongHorizonForecast
    overall_data_quality: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiscaleForecaster(ABC):
    """
    Abstract interface for multiscale forecasting assemblies.
    """

    def assemble_multiscale_forecast(
        self,
        short_state: ShortHorizonForecast,
        long_state: LongHorizonForecast
    ) -> MultiscaleForecast:
        pass

    def predict_multiscale(
        self,
        microstructure_state: Any,
        macro_feature_state: Any
    ) -> MultiscaleForecastResult:
        pass
