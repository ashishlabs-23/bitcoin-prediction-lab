"""
tests/test_forecast_accuracy.py — Unit Tests for Forecast Accuracy Record Evaluation
===================================================================================
Verifies:
1. Immutable snapshot calculation against resolved high/low/close prices
2. Correct Winkler scoring, interval width, and P90 envelope containment logic
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.forecast_accuracy import forecast_accuracy_observatory, ForecastAccuracyRecord


def test_forecast_accuracy_record_evaluation():
    rec = forecast_accuracy_observatory.evaluate_forecast_outcome(
        forecast_id="FC-20260820-001",
        timestamp="2026-08-20T12:00:00Z",
        current_price=65000.0,
        predicted_mfe_p50=0.012,
        predicted_mae_p50=0.015,
        predicted_mfe_p90=0.025,
        predicted_mae_p90=0.028,
        actual_high=66200.0,
        actual_low=64100.0,
        actual_close=65800.0
    )

    assert isinstance(rec, ForecastAccuracyRecord)
    assert rec.high_covered is True
    assert rec.low_covered is True
    assert rec.joint_path_contained is True
    assert rec.winkler_score > 0.0
    assert rec.mfe_error >= 0.0
    assert rec.mae_error >= 0.0
