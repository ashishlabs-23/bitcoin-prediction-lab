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
    assert len(data["leaderboard"]) >= 8
    assert data["leaderboard"][0]["model"] == "Ridge + Volatility Context"
