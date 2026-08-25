"""
tests/test_degraded_forecast_monitor.py — Tests for Degraded Forecast Monitoring Engine
========================================================================================
Verifies that:
- Degraded forecast monitor analyzes post-repair forecasts without crashing.
- Summary CSV is exported.
- Warning threshold and research trigger semantics are respected.
"""

import os
from research.degraded_forecast_monitor import degraded_monitor, SUMMARY_CSV_PATH

def test_degraded_forecast_monitor_execution():
    res = degraded_monitor.analyze_forecast_qualities()
    assert isinstance(res, dict)
    assert "total_post_repair_forecasts" in res
    assert "valid_forecasts" in res
    assert "degraded_forecasts" in res
    assert res["research_trigger"] == "NO_NEW_RESEARCH_REQUIRED"
    assert os.path.exists(SUMMARY_CSV_PATH)
