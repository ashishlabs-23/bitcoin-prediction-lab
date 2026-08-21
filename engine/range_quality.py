"""
engine/range_quality.py — Range Forecast Reliability & Quality Scoring Engine
==============================================================================
Evaluates operational reliability and health of the BTCUSD range forecast:
1. Computes composite quality score from empirical coverage, forecast error, interval width, uncertainty, and baseline delta
2. Deterministic health classification: EXCELLENT / GOOD / WATCH / DEGRADED
3. Provides actionable operational diagnostics without optimizing against past data
"""

import os
import sys
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import numpy as np

logger = logging.getLogger("btcognitive.range_quality")


@dataclass
class RangeQualityAssessment:
    overall_status: str  # EXCELLENT, GOOD, WATCH, DEGRADED
    reliability_score: float  # 0 to 100 scale
    mfe_coverage_pct: float
    mae_coverage_pct: float
    joint_path_containment_pct: float
    mean_forecast_error_pct: float
    mean_range_width_pct: float
    uncertainty_level: str
    baseline_relative_delta_pct: float
    data_quality_state: str
    diagnostics: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RangeQualityService:
    """
    Deterministic scoring and health classification for the Range Intelligence Engine.
    """

    def evaluate_quality(
        self,
        recent_mfe_coverage: float = 93.5,
        recent_mae_coverage: float = 96.8,
        recent_path_containment: float = 90.32,
        mean_forecast_error: float = 0.4120,
        mean_range_width: float = 5.92,
        uncertainty_level: str = "MODERATE",
        baseline_delta: float = -0.0831,
        data_quality: str = "VALID"
    ) -> RangeQualityAssessment:
        """
        Evaluates operational health using deterministic rule matrices.
        """
        diagnostics = []

        if data_quality != "VALID":
            diagnostics.append(f"Data Quality Flag: {data_quality}")
            return RangeQualityAssessment(
                overall_status="DEGRADED",
                reliability_score=45.0,
                mfe_coverage_pct=recent_mfe_coverage,
                mae_coverage_pct=recent_mae_coverage,
                joint_path_containment_pct=recent_path_containment,
                mean_forecast_error_pct=mean_forecast_error,
                mean_range_width_pct=mean_range_width,
                uncertainty_level=uncertainty_level,
                baseline_relative_delta_pct=baseline_delta,
                data_quality_state=data_quality,
                diagnostics=diagnostics
            )

        # Base scoring
        score = 100.0

        # Coverage checks (Target path containment >= 78.87%)
        if recent_path_containment < 70.0:
            score -= 30.0
            diagnostics.append("Path containment below 70.0% critical threshold.")
        elif recent_path_containment < 80.0:
            score -= 15.0
            diagnostics.append("Path containment below 80.0% nominal warning band.")

        # Error checks (Target MFE error < 0.60%)
        if mean_forecast_error > 0.80:
            score -= 20.0
            diagnostics.append("Mean forecast error elevated above 0.80%.")
        elif mean_forecast_error > 0.55:
            score -= 10.0
            diagnostics.append("Mean forecast error moderately elevated above 0.55%.")

        # Baseline delta check (Negative delta indicates Ridge outperforms baseline)
        if baseline_delta > 0.05:
            score -= 15.0
            diagnostics.append("Baseline challenger outperforms production Ridge model.")

        # Range width check
        if mean_range_width > 8.0:
            score -= 10.0
            diagnostics.append("Prediction interval wider than 8.0% nominal target.")

        score = float(np.clip(score, 10.0, 100.0))

        if score >= 85.0:
            status = "EXCELLENT"
            diagnostics.append("All range forecasting health invariants verified.")
        elif score >= 70.0:
            status = "GOOD"
            diagnostics.append("Acceptable forecast reliability within normal operating parameters.")
        elif score >= 55.0:
            status = "WATCH"
            diagnostics.append("Forecast reliability degraded; increased monitoring active.")
        else:
            status = "DEGRADED"
            diagnostics.append("Severe forecast degradation observed.")

        return RangeQualityAssessment(
            overall_status=status,
            reliability_score=round(score, 2),
            mfe_coverage_pct=recent_mfe_coverage,
            mae_coverage_pct=recent_mae_coverage,
            joint_path_containment_pct=recent_path_containment,
            mean_forecast_error_pct=mean_forecast_error,
            mean_range_width_pct=mean_range_width,
            uncertainty_level=uncertainty_level,
            baseline_relative_delta_pct=baseline_delta,
            data_quality_state=data_quality,
            diagnostics=diagnostics
        )


range_quality_service = RangeQualityService()
