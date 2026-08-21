"""
models/forecast_quality_contract.py — Forecast Quality & Validation Eligibility Contract
========================================================================================
Defines formal forecast data-quality tiers to ensure degraded fallback observations
are strictly isolated from canonical primary validation metrics:

Tiers:
  - VALID: Complete primary & secondary features, valid volatility context. validation_eligible = True.
  - DEGRADED: Missing secondary features, bounded fallback used. validation_eligible = False.
  - INVALID: Missing core pricing/volatility, corrupt payload. validation_eligible = False.
"""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any


class ForecastQuality(str, Enum):
    VALID = "VALID"
    DEGRADED = "DEGRADED"
    INVALID = "INVALID"


class BlockQuality(str, Enum):
    VALID = "VALID"        # 100% of forecasts in block are VALID
    MIXED = "MIXED"        # Contains mix of VALID and DEGRADED
    DEGRADED = "DEGRADED"  # All forecasts in block are DEGRADED
    INVALID = "INVALID"    # Contains invalid or corrupt forecasts


@dataclass
class ForecastQualityRecord:
    data_quality: ForecastQuality
    validation_eligible: bool
    context_status: str
    degraded_reason: Optional[str]
    missing_features: List[str]
    source: str
    model_version: str
    context_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_quality": self.data_quality.value if isinstance(self.data_quality, ForecastQuality) else str(self.data_quality),
            "validation_eligible": bool(self.validation_eligible),
            "context_status": str(self.context_status),
            "degraded_reason": self.degraded_reason,
            "missing_features": self.missing_features,
            "source": str(self.source),
            "model_version": str(self.model_version),
            "context_version": str(self.context_version)
        }


def assess_forecast_quality(
    current_price: float,
    vol_24h: float,
    features: Optional[Dict[str, Any]],
    context_healthy: bool = True
) -> ForecastQualityRecord:
    """
    Deterministically evaluates forecast inputs and assigns quality tier and validation eligibility.
    """
    missing = []
    if current_price is None or current_price <= 0 or vol_24h is None or vol_24h <= 0:
        return ForecastQualityRecord(
            data_quality=ForecastQuality.INVALID,
            validation_eligible=False,
            context_status="INVALID_PRICING",
            degraded_reason="Core pricing or realized volatility missing or non-positive",
            missing_features=["current_price", "vol_24h"],
            source="live_feature_pipeline",
            model_version="v3.0.0-ridge-volatility-context",
            context_version="v1.0.0-volatility-bridge-context"
        )

    required_secondary = ["rsi_14", "atr_14", "ret_24h"]
    if features is None:
        missing = required_secondary
    else:
        for f in required_secondary:
            if f not in features or features[f] is None:
                missing.append(f)

    if not context_healthy or len(missing) > 0:
        reason = f"Missing secondary features: {missing}" if missing else "Volatility context degraded"
        return ForecastQualityRecord(
            data_quality=ForecastQuality.DEGRADED,
            validation_eligible=False,
            context_status="CONTEXT_DEGRADED" if not context_healthy else "FEATURE_DEGRADED",
            degraded_reason=reason,
            missing_features=missing,
            source="live_feature_pipeline",
            model_version="v3.0.0-ridge-volatility-context",
            context_version="v1.0.0-volatility-bridge-context"
        )

    return ForecastQualityRecord(
        data_quality=ForecastQuality.VALID,
        validation_eligible=True,
        context_status="CONTEXT_HEALTHY",
        degraded_reason=None,
        missing_features=[],
        source="live_feature_pipeline",
        model_version="v3.0.0-ridge-volatility-context",
        context_version="v1.0.0-volatility-bridge-context"
    )
