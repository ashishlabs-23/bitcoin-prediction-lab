"""
tests/test_range_quality.py — Unit Tests for Range Quality Scoring Engine
=========================================================================
Verifies:
1. EXCELLENT / GOOD / WATCH / DEGRADED status classifications
2. Score calculation bounds and diagnostics generation
3. Data quality gating behavior
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_quality import range_quality_service, RangeQualityAssessment


def test_range_quality_excellent_state():
    assessment = range_quality_service.evaluate_quality(
        recent_mfe_coverage=93.5,
        recent_mae_coverage=96.8,
        recent_path_containment=90.32,
        mean_forecast_error=0.4120,
        mean_range_width=5.92,
        baseline_delta=-0.0831,
        data_quality="VALID"
    )

    assert isinstance(assessment, RangeQualityAssessment)
    assert assessment.overall_status == "EXCELLENT"
    assert assessment.reliability_score >= 85.0
    assert len(assessment.diagnostics) > 0


def test_range_quality_degraded_data_state():
    assessment = range_quality_service.evaluate_quality(
        data_quality="DEGRADED"
    )

    assert assessment.overall_status == "DEGRADED"
    assert assessment.reliability_score == 45.0


def test_range_quality_watch_state_on_low_containment():
    assessment = range_quality_service.evaluate_quality(
        recent_path_containment=65.0,  # Below critical threshold
        mean_forecast_error=0.90,
        data_quality="VALID"
    )

    assert assessment.overall_status in ["WATCH", "DEGRADED"]
    assert assessment.reliability_score < 70.0
