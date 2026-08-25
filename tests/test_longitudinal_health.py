"""
tests/test_longitudinal_health.py — Unit Tests for Longitudinal Collector Health Endpoint
=========================================================================================
Verifies:
1. GET /prediction/longitudinal/health payload schema and status
2. Verified monitor_status, provenance_health, and observed_blocks count
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app

client = TestClient(app)


def test_get_prediction_longitudinal_health_endpoint():
    res = client.get("/prediction/longitudinal/health")
    assert res.status_code == 200

    data = res.json()
    assert data["monitor_status"] == "ACTIVE_PASSIVE_COLLECTION"
    assert data["model_health"] == "HEALTHY"
    assert data["context_health"] == "HEALTHY"
    assert data["provenance_health"] == "PROVENANCE_LOCKED"
    assert data["stop_rule"] == "NO_NEW_RESEARCH_REQUIRED"
    assert data["observed_blocks"] == 35
    assert data["next_milestone"] == 40
