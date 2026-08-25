"""
tests/test_terminal_routes.py — Unit Tests for Terminal & Observatory Routes
=============================================================================
Verifies that /api/terminal/live, /api/observatory/summary, and /api/observatory/history
return valid schemas and correct answers to the 4 foundational decision questions.
"""

import pytest
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)


def test_terminal_live_endpoint():
    response = client.get("/api/terminal/live")
    assert response.status_code == 200
    data = response.json()
    assert "four_questions" in data
    q = data["four_questions"]
    
    # Check Question 1
    assert "1_expected_volatility" in q
    assert "point_forecast_har_rs_dow" in q["1_expected_volatility"]
    
    # Check Question 2
    assert "2_uncertainty_risk_envelope" in q
    assert "lower_bound_variance" in q["2_uncertainty_risk_envelope"]
    assert "upper_bound_variance" in q["2_uncertainty_risk_envelope"]
    
    # Check Question 3
    assert "3_current_regime" in q
    assert "macro_epoch" in q["3_current_regime"]
    
    # Check Question 4
    assert "4_operational_calibration_trust" in q
    assert "calibration_health_status" in q["4_operational_calibration_trust"]
    assert q["4_operational_calibration_trust"]["calibration_health_status"] in [
        "STABLE", "WATCH", "DEGRADED", "FAIL", "DATA_INVALID"
    ]


def test_observatory_summary_endpoint():
    response = client.get("/api/observatory/summary")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "total_resolved_forecasts" in data
    assert "pending_unresolved_forecasts" in data


def test_observatory_history_endpoint():
    response = client.get("/api/observatory/history?limit=10")
    assert response.status_code == 200
    records = response.json()
    assert isinstance(records, list)
    if records:
        rec = records[0]
        assert "forecast_id" in rec
        assert "forecast_hash" in rec
        assert "lifecycle_state" in rec
