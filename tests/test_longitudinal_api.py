"""
tests/test_longitudinal_api.py — Unit Tests for Longitudinal Monitoring API Endpoints
=====================================================================================
Verifies:
1. GET /prediction/longitudinal response schema, milestone tracking, and N_eff
2. GET /research/next-trigger stop-rule response
3. Longitudinal fields in GET /prediction/intelligence/health
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app

client = TestClient(app)


def test_get_prediction_longitudinal_endpoint():
    res = client.get("/prediction/longitudinal")
    assert res.status_code == 200

    data = res.json()
    assert data["governance_mode"] == "LONGITUDINAL_MONITORING_ACTIVE"
    assert data["observed_blocks"] == 35
    assert data["target_blocks"] == 90
    assert data["next_milestone_block"] == 40
    assert data["observed_metrics"]["model_status"] == "MODEL_STABLE"
    assert data["hawkes_shadow_progress"]["role"] == "VALIDATED_SHADOW_MODEL"


def test_get_research_next_trigger_endpoint():
    res = client.get("/research/next-trigger")
    assert res.status_code == 200

    data = res.json()
    assert data["status"] == "NO_NEW_RESEARCH_REQUIRED"
    assert data["triggered_failure"] is None


def test_get_prediction_intelligence_health_longitudinal_fields():
    res = client.get("/prediction/intelligence/health")
    assert res.status_code == 200

    data = res.json()
    assert data["production_blocks"] == 35
    assert data["production_N_eff"] == 33.4
    assert data["production_baseline_delta_bps"] == -14.1
    assert data["context_status"] == "CONTEXT_STABLE"
    assert data["shadow_hawkes_N_eff"] == 135.0
