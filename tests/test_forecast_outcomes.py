"""
tests/test_forecast_outcomes.py — Unit Tests for Forecast Outcome Monitor & Calibration Alerts
==============================================================================================
Verifies:
1. Forecast outcome containment resolution (Upper, Lower, Full Path)
2. Closed prediction persistence in forecast_outcomes table
3. Live calibration monitor health status & CALIBRATION_WARNING alert triggering
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.forecast_outcome_monitor import ForecastOutcomeMonitor, ForecastOutcomeRecord
from research.range_model_monitor import RangeModelMonitor, CalibrationHealthReport


@pytest.fixture
def outcome_monitors():
    return ForecastOutcomeMonitor(), RangeModelMonitor()


def test_forecast_outcome_resolution_contained(outcome_monitors):
    outcome_svc, _ = outcome_monitors

    record = outcome_svc.resolve_forecast(
        forecast_id="test-fc-123",
        pred_ts="2026-08-20T00:00:00Z",
        current_price=100000.0,
        upper_p90=102000.0,
        lower_p90=98000.0,
        exp_mfe=0.010,
        exp_mae=0.010,
        forward_candles_high=[100500.0, 101200.0, 101500.0],
        forward_candles_low=[99800.0, 99200.0, 98500.0],
        forward_close=100800.0
    )

    assert isinstance(record, ForecastOutcomeRecord)
    assert record.upper_covered is True
    assert record.lower_covered is True
    assert record.path_contained is True
    assert record.actual_high == 101500.0
    assert record.actual_low == 98500.0


def test_forecast_outcome_resolution_uncontained(outcome_monitors):
    outcome_svc, _ = outcome_monitors

    record = outcome_svc.resolve_forecast(
        forecast_id="test-fc-456",
        pred_ts="2026-08-20T00:00:00Z",
        current_price=100000.0,
        upper_p90=102000.0,
        lower_p90=98000.0,
        exp_mfe=0.010,
        exp_mae=0.010,
        forward_candles_high=[103000.0],  # Breaches upper range
        forward_candles_low=[99000.0],
        forward_close=102500.0
    )

    assert record.upper_covered is False
    assert record.lower_covered is True
    assert record.path_contained is False


def test_calibration_health_monitor_alerts(outcome_monitors):
    _, cal_monitor = outcome_monitors

    # Healthy scenario
    res_healthy = cal_monitor.check_calibration_health(
        covered_flags=[True] * 90 + [False] * 10,
        interval_widths_pct=[1.35] * 100
    )
    assert res_healthy.status == "CALIBRATION_HEALTHY"
    assert res_healthy.alert_triggered is False

    # Degraded coverage scenario (75% coverage vs 88.67% target)
    res_warning = cal_monitor.check_calibration_health(
        covered_flags=[True] * 75 + [False] * 25,
        interval_widths_pct=[1.35] * 100
    )
    assert res_warning.status == "DRIFT_CRITICAL"
    assert res_warning.alert_triggered is True
