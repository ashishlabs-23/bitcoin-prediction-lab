"""
models/interfaces/range_forecaster.py — Abstract Base Interface for Range Forecasters
=====================================================================================
Establishes the uniform contract for all production and challenger models predicting
24h MFE / MAE quantiles and conformal uncertainty.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class RangeForecastOutput:
    mfe_p10: float
    mfe_p25: float
    mfe_p50: float
    mfe_p75: float
    mfe_p90: float
    mae_p10: float
    mae_p25: float
    mae_p50: float
    mae_p75: float
    mae_p90: float
    uncertainty: float
    model_version: str


class RangeForecaster(ABC):
    """
    Abstract interface for 24h MFE/MAE Range Forecasting Models.
    """

    @abstractmethod
    def predict_range(self, features: Any) -> RangeForecastOutput:
        """
        Generates 24-hour MFE and MAE quantile forecasts.
        """
        pass
