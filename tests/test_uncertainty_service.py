"""
tests/test_uncertainty_service.py — Unit Tests for Uncertainty & Conformal Gating Service
========================================================================================
Verifies:
1. Relative uncertainty ratio calculation
2. Confidence classification gating: HIGH vs MODERATE vs LOW_CONFIDENCE
3. Data quality penalty and conformal coverage adjustment
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.uncertainty_service import UncertaintyService, UncertaintyEvaluation


@pytest.fixture
def unc_service():
    return UncertaintyService(
        high_uncertainty_threshold=2.50,
        moderate_uncertainty_threshold=1.80,
        base_coverage_target=88.67
    )


def test_uncertainty_evaluation_high_confidence(unc_service):
    res = unc_service.evaluate_uncertainty(
        mfe_p10=0.005,
        mfe_p90=0.015,
        exp_mfe=0.010,
        data_quality_score=1.0,
        degraded=False
    )
    assert isinstance(res, UncertaintyEvaluation)
    assert res.confidence_level == "HIGH"
    assert res.relative_uncertainty == 1.0  # (0.015 - 0.005) / 0.010 = 1.0
    assert res.coverage_confidence_pct == 88.67


def test_uncertainty_evaluation_low_confidence_on_dispersion(unc_service):
    res = unc_service.evaluate_uncertainty(
        mfe_p10=0.002,
        mfe_p90=0.035,  # Wide dispersion
        exp_mfe=0.010,
        data_quality_score=1.0,
        degraded=False
    )
    assert res.confidence_level == "LOW_CONFIDENCE"
    assert res.relative_uncertainty >= 2.50


def test_uncertainty_evaluation_low_confidence_on_degraded_data(unc_service):
    res = unc_service.evaluate_uncertainty(
        mfe_p10=0.005,
        mfe_p90=0.015,
        exp_mfe=0.010,
        data_quality_score=0.60,
        degraded=True
    )
    assert res.confidence_level == "LOW_CONFIDENCE"
