"""Accuracy endpoints must withhold metrics until verified forecasts can be evaluated."""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app

client = TestClient(app)


def test_get_prediction_accuracy_endpoint():
    res = client.get("/prediction/accuracy")
    assert res.status_code == 200

    data = res.json()
    assert data["status"] == "UNAVAILABLE_UNVERIFIED"
    assert data["system_version"] is None
    assert data["governance_status"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert data["sample_accounting"]["independent_blocks_24h"] is None
    assert data["range_accuracy"]["calibration_status"] == "UNVERIFIED"
    assert data["directional_accuracy"]["direction_accuracy_pct"] is None
    assert data["baseline_comparison"]["edge_status"] == "UNVERIFIED"
    assert data["reason"]


def test_get_prediction_accuracy_history_endpoint():
    res = client.get("/prediction/accuracy/history")
    assert res.status_code == 200

    data = res.json()
    assert data["status"] == "UNAVAILABLE_UNVERIFIED"
    assert data["count"] == 0
    assert data["history"] == []
    assert data["reason"]


def test_get_prediction_failures_endpoint():
    res = client.get("/prediction/failures")
    assert res.status_code == 200

    data = res.json()
    assert data["status"] == "UNAVAILABLE_UNVERIFIED"
    assert data["conformal_alignment"] is None
    assert data["failures"] == []
    assert data["reason"]
