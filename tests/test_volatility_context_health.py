"""Range-health API must not expose unverified context metrics."""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app

client = TestClient(app)


def test_get_prediction_range_health_context_metrics():
    response = client.get("/prediction/range/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert data["production_model_status"] == "BLOCKED"
    assert data["production_forecast_available"] is False
    assert data["trading_enabled"] is False
    assert data["observed_coverage_pct"] is None
    assert data["sample_size"] is None
    assert data["reason"]
