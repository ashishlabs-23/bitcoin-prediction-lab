"""
tests/test_longitudinal_dashboard.py — Unit Tests for Longitudinal Dashboard Endpoint
======================================================================================
Verifies:
1. GET /prediction/longitudinal schema conforms to separated observed and target blocks
2. Absence of fake future metrics in the observed block payload

V32.73 isolation note:
  The live SQLite DB has legitimately accumulated 7 post-repair blocks during ongoing
  collection. Tests that verify the schema of an initial-state payload are isolated
  via monkeypatching of post_repair_monitor.get_status. This preserves the intent of
  the assertion (fail-closed fallback returns None for metrics when blocks < 5) while
  decoupling from the live accumulation state.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app

client = TestClient(app)

_ZERO_BLOCKS_STATUS = {
    "evidence_phase": "POST_REPAIR",
    "monitoring_status": "ACTIVE_POST_REPAIR_COLLECTION",
    "production_model_frozen": True,
    "evidence_boundary": "2026-08-21T12:15:00Z",
    "observed_blocks": 0,
    "observed_valid_blocks": 0,
    "observed_mixed_blocks": 0,
    "observed_degraded_forecasts": 0,
    "observed_invalid_forecasts": 0,
    "target_blocks": 90,
    "next_milestone": 5,
    "raw_post_repair_forecasts": 0,
    "resolved_post_repair_forecasts": 0,
    "n_eff": 0.0,
    "model_hash": "N/A",
    "context_hash": "N/A",
    "feature_schema_hash": "N/A",
    "target_hash": "N/A",
    "repair_version": "v1.0.0-production-data-consistency-repair",
    "archived_pre_repair_blocks": 35,
    "archived_pre_repair_label": "PRE_REPAIR_HISTORY",
    "health_status": {
        "model_health": "HEALTHY",
        "context_health": "HEALTHY",
        "calibration_health": "CALIBRATION_OK",
        "drift_health": "DRIFT_NORMAL",
        "data_health": "HEALTHY",
        "provenance_health": "OK",
    },
}


def test_get_prediction_longitudinal_dashboard_payload(monkeypatch):
    """Verifies fail-closed payload schema in 0-blocks initial state."""
    import research.post_repair_longitudinal_monitor as _mon
    monkeypatch.setattr(_mon.post_repair_monitor, "get_status", lambda: _ZERO_BLOCKS_STATUS)

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
