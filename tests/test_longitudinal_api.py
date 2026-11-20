"""
tests/test_longitudinal_api.py — Unit Tests for Longitudinal Monitoring API Endpoints
=====================================================================================
Verifies:
1. GET /prediction/longitudinal response schema, milestone tracking, and N_eff
2. GET /research/next-trigger stop-rule response
3. Longitudinal fields in GET /prediction/intelligence/health

V32.73 isolation note:
  The live SQLite DB has legitimately accumulated 7 post-repair blocks during ongoing
  collection. Tests that assert schema correctness for an initial-state payload are
  isolated via monkeypatching of post_repair_monitor.get_status so they do not couple
  to the live DB block count. This does NOT weaken the assertion — it fixes test
  isolation to match the intent: "schema and milestone structure are correct when the
  system is in the initial, 0-blocks state." The live block count is externally tracked
  and reported separately.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared zero-blocks stub — mirrors the structure returned by get_status()
# but fixes observed_valid_blocks = 0 so tests verify schema, not live count.
# ---------------------------------------------------------------------------
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


def test_get_prediction_longitudinal_endpoint(monkeypatch):
    """Schema and milestone structure are correct in the 0-blocks initial state."""
    import research.post_repair_longitudinal_monitor as _mon
    monkeypatch.setattr(_mon.post_repair_monitor, "get_status", lambda: _ZERO_BLOCKS_STATUS)

    res = client.get("/prediction/longitudinal")
    assert res.status_code == 200

    data = res.json()
    assert data["governance_mode"] == "OFFLINE_RESEARCH_ONLY"
    assert data["observed_blocks"] == 0
    assert data["archived_pre_repair_evidence"]["archived_blocks"] == 35
    assert data["target_blocks"] == 90
    assert data["next_milestone_block"] == 5
    assert data["progress_pct"] == 0.0
    assert data["observed_metrics"]["model_status"] == "NOT_ESTABLISHED"
    assert data["observed_metrics"]["calibration_status"] == "UNAVAILABLE"
    assert data["observed_metrics"]["p90_coverage_pct"] is None
    assert data["observed_metrics"]["baseline_delta_bps"] is None
    assert data["hawkes_shadow_progress"]["role"] == "VALIDATED_SHADOW_ONLY"


def test_get_research_next_trigger_endpoint():
    res = client.get("/research/next-trigger")
    assert res.status_code == 200

    data = res.json()
    assert data["status"] == "NO_NEW_RESEARCH_REQUIRED"
    assert data["triggered_failure"] is None


def test_get_prediction_intelligence_health_longitudinal_fields(monkeypatch):
    """Health endpoint returns correct schema with 0-blocks isolation."""
    import research.post_repair_longitudinal_monitor as _mon
    monkeypatch.setattr(_mon.post_repair_monitor, "get_status", lambda: _ZERO_BLOCKS_STATUS)

    res = client.get("/prediction/intelligence/health")
    assert res.status_code == 200

    data = res.json()
    assert data["production_blocks"] == 0
    assert data["production_N_eff"] is None
    # Verified: production_baseline_delta_bps is None when no causal benchmark exists
    assert data["production_baseline_delta_bps"] is None
    assert data["production_status"] == "OFFLINE_RESEARCH_ONLY"
    assert data["context_status"] == "UNAVAILABLE"
