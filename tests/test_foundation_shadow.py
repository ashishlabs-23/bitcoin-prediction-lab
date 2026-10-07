"""
tests/test_foundation_shadow.py — Unit Tests for Foundation Shadow Isolation
=============================================================================
Verifies:
1. Complete isolation of foundation shadow forecasts from production
2. Integration with GET /research/foundation-models API endpoint
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.foundation_shadow import foundation_shadow_harness
from api.server import app

client = TestClient(app)


def test_foundation_shadow_execution():
    res = foundation_shadow_harness.execute_shadow_evaluation(current_price=65200.0)

    assert res["isolation_status"] == "STRICTLY_ISOLATED_FROM_PRODUCTION"
    assert "timesfm_2.5" in res["shadow_forecasts"]
    assert "moirai_2.0" in res["shadow_forecasts"]
    assert "chronos_2" in res["shadow_forecasts"]


def test_get_research_foundation_models_endpoint():
    resp = client.get("/research/foundation-models")
    assert resp.status_code == 200

    data = resp.json()
    assert data["title"] == "BTCUSD FORECAST MODEL BENCHMARK"
    assert data["status"] == "UNAVAILABLE_NOT_EXECUTED"
    assert data["authoritative"] is False
    assert data["leaderboard"] == []


def test_model_leaderboards_do_not_publish_synthetic_foundation_scores(monkeypatch):
    from types import SimpleNamespace
    from engine.forecast_intelligence import forecast_intelligence_orchestrator

    monkeypatch.setattr(
        forecast_intelligence_orchestrator.range_service,
        "generate_forecast",
        lambda **kwargs: SimpleNamespace(upper_p90=1.0, lower_p90=0.5),
    )
    all_models = client.get("/research/models").json()
    assert all_models["foundation_models"]["status"] == "UNAVAILABLE_NOT_EXECUTED"
    assert all_models["foundation_models"]["leaderboard"] == []

    intelligence = client.get("/prediction/intelligence").json()
    research = intelligence["research_forecasts"]
    assert research["status"] == "UNAVAILABLE_NOT_EXECUTED"
    assert research["models"] == {}
