"""Uncertainty diagnostics that fail closed when calibration is unavailable."""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class UncertaintyEvaluation:
    interval_width_pct: float
    relative_uncertainty: float
    data_quality_score: float
    confidence_level: str  # HIGH, MODERATE, LOW_CONFIDENCE, UNAVAILABLE
    coverage_confidence_pct: Optional[float]
    explanation: str


class UncertaintyService:
    """
    Reports interval dispersion without implying empirical calibration.
    """

    def __init__(
        self,
        high_uncertainty_threshold: float = 2.50,
        moderate_uncertainty_threshold: float = 1.80
    ):
        self.high_uncertainty_threshold = high_uncertainty_threshold
        self.moderate_uncertainty_threshold = moderate_uncertainty_threshold

    def evaluate_uncertainty(
        self,
        mfe_p10: float,
        mfe_p90: float,
        exp_mfe: float,
        data_quality_score: float = 1.0,
        degraded: bool = False
    ) -> UncertaintyEvaluation:
        """
        Calculates interval width, relative dispersion, and assigns confidence gating.
        No verifiable calibration artifact is configured, so coverage is always unavailable.
        """
        interval_width = max(1e-6, mfe_p90 - mfe_p10)
        expected_move = max(1e-6, exp_mfe)
        relative_unc = interval_width / expected_move

        conf_level = "UNAVAILABLE"
        expl = "Dispersion is measurable, but no verifiable calibration artifact is configured."
        if degraded or data_quality_score < 0.70 or relative_unc >= self.high_uncertainty_threshold:
            expl += " The input quality or dispersion also warrants caution."
        elif relative_unc >= self.moderate_uncertainty_threshold or data_quality_score < 0.90:
            expl += " Dispersion is moderate."

        return UncertaintyEvaluation(
            interval_width_pct=round(interval_width * 100.0, 3),
            relative_uncertainty=round(relative_unc, 3),
            data_quality_score=round(data_quality_score, 3),
            confidence_level=conf_level,
            coverage_confidence_pct=None,
            explanation=expl
        )


# Global Singleton Instance
uncertainty_service = UncertaintyService()
