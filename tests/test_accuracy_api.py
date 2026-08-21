"""
tests/test_accuracy_api.py — Unit Tests for Forecast Accuracy Observatory API Routes
=====================================================================================
Verifies:
1. GET /prediction/accuracy response schema, sample accounting, and baseline metrics
2. GET /prediction/accuracy/history and GET /prediction/failures endpoints
"""

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
    assert data["system_version"] == "v3.0.0-ridge-volatility-context"
    assert data["sample_accounting"]["independent_blocks_24h"] == 31
    assert data["range_accuracy"]["calibration_status"] == "CALIBRATION_OK"
    assert data["directional_accuracy"]["status"] == "NO_MEASURABLE_EDGE"
    assert data["baseline_comparison"]["edge_status"] == "STATISTICALLY_SUPERIOR"


def test_get_prediction_accuracy_history_endpoint():
    res = client.get("/prediction/accuracy/history")
    assert res.status_code == 200

    data = res.json()
    assert data["count"] >= 4
    assert len(data["history"]) >= 4


def test_get_prediction_failures_endpoint():
    res = client.get("/prediction/failures")
    assert res.status_code == 200

    data = res.json()
    assert data["conformal_alignment"] == "COMPLIANT"
    assert len(data["failures"]) >= 3
