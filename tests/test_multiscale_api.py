"""
tests/test_multiscale_api.py — Integration Tests for GET /prediction/multiscale Endpoint
========================================================================================
Verifies:
1. HTTP 200 response on /prediction/multiscale
2. Dual-horizon payload containing short_horizon (5m) and long_horizon (24h)
3. Model version and shadow health propagation
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app

client = TestClient(app)


def test_get_multiscale_prediction_endpoint():
    response = client.get("/prediction/multiscale")
    assert response.status_code == 200

    data = response.json()
    assert data["symbol"] == "BTCUSD"
    assert "short_horizon" in data
    assert "long_horizon" in data
    assert data["short_horizon"]["horizon"] == "5m"
    assert data["long_horizon"]["horizon"] == "24h"
    assert data["production_model_version"] == "v3.0.0-excursion-ridge-conformal"
    assert data["shadow_model_version"] == "v1.0.0-challenger-hawkes-microstructure"
    assert "shadow_health" in data
