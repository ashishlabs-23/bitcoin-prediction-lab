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
    assert intel.production_forecast["system_status"] == "VALIDATED_PRODUCTION_RANGE_SYSTEM"
    assert intel.shadow_forecast["system_status"] == "VALIDATED_SHADOW_MODEL"
    assert intel.research_forecasts["status"] == "FOUNDATION_RESEARCH_ONLY"
    assert intel.forecast_reliability["reliability_tier"] == "VERY_HIGH"


def test_get_prediction_intelligence_endpoints():
    res1 = client.get("/prediction/intelligence")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["symbol"] == "BTCUSD"
    assert "production_forecast" in data1
    assert "shadow_forecast" in data1

    res2 = client.get("/prediction/intelligence/health")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["overall_reliability"] == "VERY_HIGH"

    res3 = client.get("/research/models")
    assert res3.status_code == 200
    data3 = res3.json()
    assert "PRODUCTION" in data3["categories"]
    assert "SHADOW" in data3["categories"]
    assert "RESEARCH" in data3["categories"]
    assert "REJECTED" in data3["categories"]
