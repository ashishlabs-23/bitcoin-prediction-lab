"""
tests/test_multiscale_health.py — Unit Tests for Multiscale Health Service & Endpoint
=====================================================================================
Verifies:
1. Multiscale health report generation across Ridge and Hawkes
2. Integration with GET /prediction/multiscale/health
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.multiscale_health import multiscale_health_service, MultiscaleHealthReport
from api.server import app

client = TestClient(app)


def test_multiscale_health_service_evaluation():
    report = multiscale_health_service.get_health_report()

    assert isinstance(report, MultiscaleHealthReport)
    assert report.ridge_status == "PRODUCTION"
    assert report.hawkes_status == "VALIDATED_SHADOW_MODEL"
    assert report.overall_health == "HEALTHY"


def test_get_multiscale_health_endpoint():
    response = client.get("/prediction/multiscale/health")
    assert response.status_code == 200

    data = response.json()
    assert data["ridge_status"] == "PRODUCTION"
    assert data["hawkes_status"] == "VALIDATED_SHADOW_MODEL"
    assert data["overall_health"] == "HEALTHY"
