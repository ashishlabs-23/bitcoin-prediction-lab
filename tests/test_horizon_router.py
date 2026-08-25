"""
tests/test_horizon_router.py — Unit Tests for Horizon Model Allocation & Routing
================================================================================
Verifies:
1. Complete mapping across all 7 horizons to specialized model families
2. Integration with GET /prediction/horizons endpoint
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.horizon_model_matrix import generate_horizon_model_matrix
from api.server import app

client = TestClient(app)


def test_horizon_model_matrix_generation():
    df_m, meta = generate_horizon_model_matrix()

    assert len(df_m) == 7
    assert meta["status"] == "ALLOCATION_MATRIX_GENERATED"


def test_get_prediction_horizons_api_endpoint():
    response = client.get("/prediction/horizons")
    assert response.status_code == 200

    data = response.json()
    assert data["symbol"] == "BTCUSD"
    assert len(data["available_horizons"]) == 7
    assert "5m" in data["forecast_by_horizon"]
    assert "24h" in data["forecast_by_horizon"]
    assert data["forecast_by_horizon"]["5m"]["state"] == "VALIDATED_SHADOW_MODEL"
    assert data["forecast_by_horizon"]["24h"]["state"] == "PRODUCTION"
