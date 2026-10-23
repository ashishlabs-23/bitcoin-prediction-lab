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
    assert data["observed_blocks"] == 0
    assert data["archived_pre_repair_evidence"]["archived_blocks"] == 35
    assert data["target_blocks"] == 90
    assert data["next_milestone_block"] == 5
    assert data["progress_pct"] == 0.0
    # Verified: fail-closed fallback returns None when valid evidence is insufficient
    assert data["observed_metrics"]["mfe_error_pct"] is None
    assert data["observed_metrics"]["p90_coverage_pct"] is None
    assert data["observed_metrics"]["baseline_delta_bps"] is None
    assert len(data["milestone_targets"]) == 7
    assert data["milestone_targets"][0]["target_block"] == 5
    assert data["milestone_targets"][0]["status"] == "NOT_YET_OBSERVED"
