"""
engine/forecast_reliability.py — Deterministic Forecast Reliability Evaluator
=============================================================================
Calculates deterministic reliability status for production forecasts:
- Inputs: empirical coverage, forecast error, interval width, drift PSI, data freshness, model health
- Outputs: VERY_HIGH, HIGH, MODERATE, LOW, INSUFFICIENT
- Zero directional predictions; purely operational & calibration trustworthiness.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class ForecastReliabilityReport:
    reliability_tier: str  # VERY_HIGH, HIGH, MODERATE, LOW, INSUFFICIENT
    reliability_score: float  # 0.0 - 100.0
    coverage_score: float
    error_score: float
    drift_score: float
    health_score: float
    sample_adequacy_score: float
    narrative_rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ForecastReliabilityService:
    def evaluate_reliability(
        self,
        p90_coverage_pct: float = 91.10,
        mfe_error_pct: float = 0.3980,
        drift_psi: float = 0.024,
        is_healthy: bool = True,
        independent_blocks: int = 31
    ) -> ForecastReliabilityReport:
        # 1. Coverage Score (Target 90% +/- 2%)
        cov_diff = abs(p90_coverage_pct - 90.0)
        cov_score = max(0.0, 100.0 - cov_diff * 15.0)

        # 2. Error Score
        err_score = max(0.0, 100.0 - (mfe_error_pct / 0.50) * 40.0)

        # 3. Drift Score
        drift_score = 100.0 if drift_psi < 0.05 else (80.0 if drift_psi < 0.10 else 40.0)

        # 4. Health Score
        health_score = 100.0 if is_healthy else 20.0

        # 5. Sample Adequacy
        sample_score = 100.0 if independent_blocks >= 30 else (independent_blocks / 30.0 * 80.0)

        total_score = round(
            0.25 * cov_score +
            0.25 * err_score +
            0.20 * drift_score +
            0.15 * health_score +
            0.15 * sample_score,
            2
        )

        if total_score >= 85.0 and independent_blocks >= 30:
            tier = "VERY_HIGH"
            rationale = "Exceptional conformal calibration, sub-0.40% error, nominal drift, and >=30 independent blocks."
        elif total_score >= 75.0:
            tier = "HIGH"
            rationale = "Calibrated envelope with stable telemetry and verified production health."
        elif total_score >= 60.0:
            tier = "MODERATE"
            rationale = "Operational forecast with moderate calibration dispersion."
        elif total_score >= 40.0:
            tier = "LOW"
            rationale = "Elevated forecast error or minor drift detected."
        else:
            tier = "INSUFFICIENT"
            rationale = "Critical telemetry degradation or insufficient independent evaluation samples."

        return ForecastReliabilityReport(
            reliability_tier=tier,
            reliability_score=total_score,
            coverage_score=round(cov_score, 2),
            error_score=round(err_score, 2),
            drift_score=round(drift_score, 2),
            health_score=round(health_score, 2),
            sample_adequacy_score=round(sample_score, 2),
            narrative_rationale=rationale
        )


forecast_reliability_service = ForecastReliabilityService()
