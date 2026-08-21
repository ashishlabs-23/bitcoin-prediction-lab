"""
tests/test_horizon_health.py — Unit Tests for Multi-Horizon Health API & Gap Analysis
=====================================================================================
Verifies:
1. Operational health and gap monitoring across all 7 horizons
2. Integration with GET /prediction/horizons/health
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.horizon_health import evaluate_horizon_health_and_gaps
from api.server import app

client = TestClient(app)


def test_horizon_health_and_gap_analysis():
    df_h, meta = evaluate_horizon_health_and_gaps()

    assert len(df_h) == 7
    assert "primary_gap" in meta


def test_get_prediction_horizons_health_endpoint():
    response = client.get("/prediction/horizons/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["horizon_count"] == 7
    assert "primary_research_gap" in data
