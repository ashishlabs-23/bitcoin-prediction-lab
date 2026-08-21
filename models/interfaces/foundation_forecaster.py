"""
models/interfaces/foundation_forecaster.py — Foundation Model Interface Specification
====================================================================================
Canonical interface and data classes for Pretrained Time-Series Foundation Models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any


@dataclass
class FoundationForecast:
    model_name: str
    model_version: str
    timestamp: str
    horizon: str
    forecast_type: str  # "PROBABILISTIC_QUANTILES" or "POINT_FORECAST_ONLY"
    point_forecast_pct: float
    mfe_p10_pct: float
    mfe_p50_pct: float
    mfe_p90_pct: float
    mae_p10_pct: float
    mae_p50_pct: float
    mae_p90_pct: float
    upper_p90_price: float
    lower_p90_price: float
    uncertainty_score: float
    context_length_hours: int
    inference_latency_ms: float
    data_quality: str
    model_state: str  # "ZERO_SHOT", "IN_CONTEXT_FEW_SHOT", "FINE_TUNED"
    provenance_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseFoundationAdapter(ABC):
    @abstractmethod
    def prepare_input(self, series: List[float], context_hours: int = 120) -> Any:
        pass

    @abstractmethod
    def forecast(self, current_price: float, inputs: Any, horizon_hours: int = 24) -> FoundationForecast:
        pass

    @abstractmethod
    def normalize_output(self, raw_output: Any, current_price: float) -> FoundationForecast:
        pass

    @abstractmethod
    def validate_output(self, forecast: FoundationForecast) -> bool:
        pass

    @abstractmethod
    def create_provenance(self, inputs: Any, forecast: FoundationForecast) -> str:
        pass
