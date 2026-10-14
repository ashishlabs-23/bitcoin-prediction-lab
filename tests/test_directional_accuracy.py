"""Directional accuracy stays unavailable until validated evidence is available."""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app


def test_directional_accuracy_endpoint():
    client = TestClient(app)
    res = client.get("/prediction/direction/accuracy")

    assert res.status_code == 200
    data = res.json()

    assert data["role"] == "SECONDARY_EXPERIMENTAL_OVERLAY"
    assert data["horizon"] == "24h"
    assert "status" in data
    assert data["status"] == "UNAVAILABLE_UNVERIFIED"
    assert data["claim_status"] == "NO_PERFORMANCE_CLAIM"
    assert data["directional_accuracy_pct"] is None
    assert data["sample_count"] is None
