"""
engine/forecast_intelligence.py — Unified Forecast Intelligence Orchestrator
=============================================================================
Translates validated production models, shadow models, foundation challengers,
and market state conditioning into a cohesive, decoupled intelligence experience.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


@dataclass
class ForecastIntelligence:
    timestamp: str
    symbol: str
    current_price: Optional[float]
    production_forecast: Dict[str, Any]
    shadow_forecast: Dict[str, Any]
    research_forecasts: Dict[str, Any]
    market_state: Dict[str, Any]
    volatility_state: Dict[str, Any]
    uncertainty_state: Dict[str, Any]
    calibration_state: Dict[str, Any]
    model_health: Dict[str, Any]
    data_quality: str
    forecast_reliability: Dict[str, Any]
    directional_evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ForecastIntelligenceOrchestrator:
    def generate_intelligence(
        self,
        current_price: Optional[float] = None,
        vol_24h: Optional[float] = None,
        hawkes_direction: str = "BULLISH_PRESSURE",
        uncertainty: float = 1.6
    ) -> ForecastIntelligence:
        """Return unavailable states until verified inputs and model artifacts are supplied."""
        now_iso = datetime.now(timezone.utc).isoformat()
        return ForecastIntelligence(
            timestamp=now_iso,
            symbol="BTCUSD",
            current_price=None,
            production_forecast={
                "status": "NOT_ESTABLISHED",
                "system_status": "OFFLINE_RESEARCH_ONLY",
                "authoritative": False,
                "target": "rv7d_var_ann (168h)",
                "point_forecast": None,
                "lower_bound": None,
                "upper_bound": None,
                "calibration_status": "UNAVAILABLE",
                "reason": "Registered Standard HAR artifact and validated local market snapshot are unavailable."
            },
            shadow_forecast={
                "status": "UNAVAILABLE_NOT_EXECUTED",
                "authoritative": False,
                "reason": "No verified input snapshot or validated shadow result is available."
            },
            research_forecasts={
                "status": "UNAVAILABLE_NOT_EXECUTED",
                "authoritative": False,
                "reason": "No research model output is available for this request."
            },
            market_state={"status": "UNAVAILABLE"},
            volatility_state={"status": "UNAVAILABLE"},
            uncertainty_state={"status": "UNAVAILABLE"},
            calibration_state={
                "status": "UNAVAILABLE",
                "joint_containment_p90": None,
                "independent_blocks": None
            },
            model_health={"overall": "OFFLINE_RESEARCH_ONLY"},
            data_quality="DATA_UNAVAILABLE",
            forecast_reliability={"status": "UNAVAILABLE"},
            directional_evidence={"status": "UNAVAILABLE"}
        )


forecast_intelligence_orchestrator = ForecastIntelligenceOrchestrator()
