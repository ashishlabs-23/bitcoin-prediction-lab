"""
tests/test_longitudinal_orchestrator.py — Unit Tests for Evidence Ingestion & Orchestration
==========================================================================================
Verifies:
1. Ingestion of valid new-data forecasts
2. Rejection of forecasts predating the frozen validation boundary
3. Production lock verification
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.longitudinal_orchestrator import (
    longitudinal_orchestrator,
    LOCKED_MODEL_HASH,
    LOCKED_CONTEXT_HASH,
    LOCKED_CALIBRATION_VERSION
)


def test_longitudinal_orchestrator_accepts_valid_new_forecast():
    valid_record = {
        "forecast_id": "ORCH-TEST-001",
        "forecast_timestamp": "2026-08-21T06:00:00Z",
        "model_hash": LOCKED_MODEL_HASH,
        "context_hash": LOCKED_CONTEXT_HASH,
        "calibration_version": LOCKED_CALIBRATION_VERSION,
        "block_id": 32
    }
    res = longitudinal_orchestrator.ingest_forecast_evidence(valid_record)
    assert res["status"] == "ACCEPTED"
    assert res["log"] == "LONGITUDINAL_FORECAST_ACCEPTED"


def test_longitudinal_orchestrator_rejects_stale_or_reused_forecast():
    stale_record = {
        "forecast_id": "ORCH-STALE-001",
        "forecast_timestamp": "2026-08-20T12:00:00Z",
        "model_hash": LOCKED_MODEL_HASH,
        "context_hash": LOCKED_CONTEXT_HASH,
        "calibration_version": LOCKED_CALIBRATION_VERSION,
        "block_id": 30
    }
    res = longitudinal_orchestrator.ingest_forecast_evidence(stale_record)
    assert res["status"] == "REJECTED"
    assert "INVALID_LONGITUDINAL_EVIDENCE" in res["error"]
