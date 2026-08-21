"""
tests/test_volatility_context_health.py — Unit Tests for Range Health API with Context Metrics
==============================================================================================
Verifies:
1. Exposure of active_context_version and context_status in GET /prediction/range/health
2. Tracking of live context drift and fallback counters
"""

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
    assert data["active_context_version"] == "v1.0.0-volatility-bridge-context"
    assert data["context_status"] == "CONTEXT_HEALTHY"
    assert data["context_coverage"] == 91.10
    assert data["context_fallback_count"] == 0
    assert data["combined_model_version"] == "v3.0.0-ridge-volatility-context"
    assert data["baseline_delta"] == -0.0140
