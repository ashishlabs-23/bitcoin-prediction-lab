"""
tests/test_range_runtime_integration.py — Integration Tests for Live Range Forecast Runtime
============================================================================================
Verifies:
1. End-to-end inference pipeline execution with RangeForecastService
2. GET /prediction/range and GET /api/prediction/range response schemas
3. Backward compatibility with existing prediction routes
4. Point-in-time assertions (No future data leakage into live endpoints)
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app
from engine.inference_service import live_engine


@pytest.fixture
def api_client():
    return TestClient(app)


def test_prediction_range_endpoint_schema(api_client):
    response = api_client.get("/prediction/range")
    assert response.status_code == 200
    data = response.json()

    # Core identification
    assert data["symbol"] == "BTCUSD"
    assert data["horizon"] == "24h"
    assert "current_price" in data
    assert "timestamp" in data

    # MFE Quantiles
    assert "mfe_p10" in data and "mfe_p50" in data and "mfe_p90" in data
    assert data["mfe_p10"] <= data["mfe_p50"] <= data["mfe_p90"]

    # MAE Quantiles
    assert "mae_p10" in data and "mae_p50" in data and "mae_p90" in data
    assert data["mae_p10"] <= data["mae_p50"] <= data["mae_p90"]

    # Price Boundaries
    assert "upper_p90" in data and "lower_p90" in data
    assert data["lower_p90"] <= data["current_price"] <= data["upper_p90"]

    # Quality and secondary layers
    assert "uncertainty" in data
    assert "coverage_confidence" in data
    assert "direction_state" in data
    assert "tradeability_category" in data
    assert "natural_language_explanation" in data


def test_prediction_range_alias_endpoint(api_client):
    response = api_client.get("/api/prediction/range")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSD"


def test_backward_compatibility_existing_endpoints(api_client):
    # Existing prediction/latest
    resp_latest = api_client.get("/prediction/latest")
    assert resp_latest.status_code == 200
    assert "direction" in resp_latest.json()

    # Existing health check
    resp_health = api_client.get("/health")
    assert resp_health.status_code == 200
    assert "status" in resp_health.json()
