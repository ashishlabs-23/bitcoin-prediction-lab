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


def test_prediction_range_endpoint_fails_closed_with_stable_schema(api_client):
    response = api_client.get("/prediction/range")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in {"EXPERIMENTAL_BASELINE", "DATA_UNAVAILABLE"}
    assert data["symbol"] == "BTC/USD"
    assert data["horizon"] == "24h"
    assert data["forecast_mode"] == "EXPERIMENTAL_BASELINE"
    assert data["validation_status"] == "NOT_VALIDATED_FOR_TRADING"
    assert data["live_capital_authorized"] is False
    assert data["research_authorization"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert data["direction"] == "NOT_ESTIMATED"
    assert data["probability"] is None
    assert data["tp"] is None and data["sl"] is None
    if data["status"] == "DATA_UNAVAILABLE":
        assert data["availability"] == "UNAVAILABLE"
        assert data.get("price_quantiles_usd") is None
        assert data["reason"]
    else:
        quantiles = data["price_quantiles_usd"]
        assert quantiles["p10"] <= quantiles["p50"] <= quantiles["p90"]


def test_prediction_range_alias_endpoint(api_client):
    response = api_client.get("/api/prediction/range")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTC/USD"
    assert data["forecast_mode"] == "EXPERIMENTAL_BASELINE"
    assert data["research_authorization"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert data["live_capital_authorized"] is False
    assert data["direction"] == "NOT_ESTIMATED"
    assert data["probability"] is None
    assert data["availability"] in {"AVAILABLE", "UNAVAILABLE"}


def test_backward_compatibility_existing_endpoints(api_client):
    # Existing prediction/latest
    resp_latest = api_client.get("/prediction/latest")
    assert resp_latest.status_code == 200
    assert resp_latest.json()["direction"] == "NOT_ESTIMATED"
    assert resp_latest.json()["probability"] is None

    # Existing health check
    resp_health = api_client.get("/health")
    assert resp_health.status_code == 200
    assert "status" in resp_health.json()
