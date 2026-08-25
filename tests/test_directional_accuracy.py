"""
tests/test_directional_accuracy.py — Unit Tests for Directional Accuracy Contract & Endpoint
============================================================================================
Verifies:
1. Directional accuracy payload format
2. Explicit EXPERIMENTAL / NO_MEASURABLE_EDGE status
3. Zero false alpha claims
"""

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
    assert "NO_MEASURABLE_EDGE" in data["status"]
    assert data["claim_status"] == "DOES_NOT_CLAIM_VALIDATED_DIRECTIONAL_TRADING_ALPHA"
    assert data["directional_accuracy_pct"] < 55.0  # Statistical realism check
