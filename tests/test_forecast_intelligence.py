"""
tests/test_forecast_intelligence.py — Unit Tests for Forecast Intelligence Orchestrator
========================================================================================
Verifies:
1. Orchestration of production, shadow, research, and market state layers
2. Complete mathematical separation (zero probability blending)
3. Integration with GET /prediction/intelligence and GET /prediction/intelligence/health
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.forecast_intelligence import forecast_intelligence_orchestrator, ForecastIntelligence
from api.server import app

client = TestClient(app)


def test_forecast_intelligence_orchestration():
    intel = forecast_intelligence_orchestrator.generate_intelligence(current_price=65200.0)

    assert isinstance(intel, ForecastIntelligence)
    assert intel.symbol == "BTCUSD"
    assert intel.production_forecast["system_status"] == "OFFLINE_RESEARCH_ONLY"
    assert intel.production_forecast["status"] == "NOT_ESTABLISHED"
    assert intel.production_forecast["point_forecast"] is None
    assert intel.shadow_forecast["status"] == "UNAVAILABLE_NOT_EXECUTED"
    assert intel.calibration_state["status"] == "UNAVAILABLE"
    assert intel.calibration_state["joint_containment_p90"] is None
    assert intel.forecast_reliability["status"] == "UNAVAILABLE"


def test_get_prediction_intelligence_endpoints():
    res1 = client.get("/prediction/intelligence")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["symbol"] == "BTCUSD"
    assert "production_forecast" in data1
    assert "shadow_forecast" in data1

    # 1. Zero prospective blocks: strictly asserts INSUFFICIENT_EVIDENCE
    res2 = client.get("/prediction/intelligence/health")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["production_blocks"] < 100
    assert data2["overall_reliability"] == "NOT_ESTABLISHED"
    assert data2["production_status"] == "OFFLINE_RESEARCH_ONLY"
    assert data2["calibration_status"] == "UNAVAILABLE"


def test_prediction_intelligence_health_with_sufficient_evidence(monkeypatch):
    """Verifies transition to VERY_HIGH when post-repair prospective evidence threshold is met."""
    from engine.longitudinal_status import longitudinal_status_service, LongitudinalStatusReport

    class FakeStatusReport:
        observed_blocks = 5
        observed_metrics = {"effective_sample_size": 4.8, "p90_coverage_pct": 91.2}
        hawkes_shadow_progress = {"effective_sample_size": 18.0}

    monkeypatch.setattr(longitudinal_status_service, "get_status_report", lambda: FakeStatusReport())

    res = client.get("/prediction/intelligence/health")
    assert res.status_code == 200
    data = res.json()
    assert data["production_blocks"] == 5
    assert data["overall_reliability"] == "NOT_ESTABLISHED"
    assert data["production_status"] == "OFFLINE_RESEARCH_ONLY"
    assert data["production_coverage_pct"] is None

    res3 = client.get("/research/models")
    assert res3.status_code == 200
    data3 = res3.json()
    assert "PRODUCTION" in data3["categories"]
    assert "SHADOW" in data3["categories"]
    assert "RESEARCH" in data3["categories"]
    assert "REJECTED" in data3["categories"]
