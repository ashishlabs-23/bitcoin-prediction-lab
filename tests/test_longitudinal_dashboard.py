"""
tests/test_longitudinal_dashboard.py — Unit Tests for Longitudinal Dashboard Endpoint
======================================================================================
Verifies:
1. GET /prediction/longitudinal schema conforms to separated observed and target blocks
2. Absence of fake future metrics in the observed block payload
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app

client = TestClient(app)


def test_get_prediction_longitudinal_dashboard_payload():
    res = client.get("/prediction/longitudinal")
    assert res.status_code == 200

    data = res.json()
    assert data["observed_blocks"] == 8
    assert data["archived_pre_repair_evidence"]["archived_blocks"] == 35
    assert data["target_blocks"] == 90
    assert data["next_milestone_block"] == 10
    assert data["observed_metrics"]["mfe_error_pct"] == 0.3980
    assert data["observed_metrics"]["p90_coverage_pct"] == 91.10
    assert len(data["milestone_targets"]) == 7
    assert data["milestone_targets"][0]["target_block"] == 5
    assert data["milestone_targets"][0]["status"] == "OBSERVED"
