"""
Unit and integration tests for the Prospective Evidence Worker and Pipeline Resilience.
Tests:
1. Pipeline resilience against restarts and atomic writes.
2. Duplicate forecast issuance prevention (idempotency).
3. Graceful handling of corrupted/malformed lines in the ledger.
4. Settlement grace period (candles delayed vs expired beyond grace period).
5. Prospective worker execution in single-cycle mode.
6. Research API exposure of worker telemetry and ledger records.
"""

import os
import json
import tempfile
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from api.server import app
from engine.prospective_evidence_pipeline import ProspectiveEvidencePipeline
from engine.prospective_worker import ProspectiveEvidenceWorker

client = TestClient(app)


@pytest.fixture
def temp_ledger(tmp_path):
    """Provides a clean temporary ledger file path."""
    ledger_file = tmp_path / "test_prospective_ledger.jsonl"
    return str(ledger_file)


def test_pipeline_duplicate_issue_prevention(temp_ledger):
    """Verify that logging a forecast with the same target and issue timestamp is rejected idempotently."""
    pipe = ProspectiveEvidencePipeline(ledger_path=temp_ledger)
    
    issue_time = "2026-08-01T00:00:00+00:00"
    rec1 = pipe.record_forecast(
        issue_timestamp_utc=issue_time,
        target_name="rv24h_var_ann",
        horizon_hours=24,
        feature_cutoff_utc=issue_time,
        baseline_predictions={"persistence": 0.04},
        challenger_prediction={"point": 0.045, "q10": 0.03, "q90": 0.06},
        model_version="HAR-QLIKE-24H-v1.0",
        artifact_hash="abc123def456",
        feature_schema_hash="ctx123",
    )
    assert rec1 is not None
    assert rec1["resolution_state"] == "PENDING"
    
    # Attempt duplicate log
    rec2 = pipe.record_forecast(
        issue_timestamp_utc=issue_time,
        target_name="rv24h_var_ann",
        horizon_hours=24,
        feature_cutoff_utc=issue_time,
        baseline_predictions={"persistence": 0.04},
        challenger_prediction={"point": 0.045, "q10": 0.03, "q90": 0.06},
        model_version="HAR-QLIKE-24H-v1.0",
        artifact_hash="abc123def456",
        feature_schema_hash="ctx123",
    )
    # The duplicate call returns the existing record and skips duplicate append
    records = pipe.load_all_records()
    assert len(records) == 1


def test_pipeline_corrupted_json_recovery(temp_ledger):
    """Verify that corrupted lines in ledger are skipped without crashing or losing valid records."""
    valid_rec = {
        "record_id": "test-rec-1",
        "issue_timestamp_utc": "2026-08-01T00:00:00+00:00",
        "maturity_timestamp_utc": "2026-08-02T00:00:00+00:00",
        "target_name": "rv24h_var_ann",
        "forecast_horizon_hours": 24,
        "model_id": "TEST-MODEL",
        "model_hash_sha256": "hash1",
        "point_forecast": 0.04,
        "prediction_interval_80": [0.03, 0.05],
        "feature_context_hash": "ctx1",
        "conformal_score": 0.01,
        "resolution_state": "PENDING",
        "resolved_outcome": None,
        "resolution_timestamp_utc": None,
        "audit_signature": "sig1",
    }
    
    with open(temp_ledger, "w", encoding="utf-8") as f:
        f.write(json.dumps(valid_rec) + "\n")
        f.write("{THIS IS A CORRUPTED INVALID JSON LINE\n")
        f.write("\n")  # Empty line
    
    pipe = ProspectiveEvidencePipeline(ledger_path=temp_ledger)
    records = pipe.load_all_records()
    assert len(records) == 1
    assert records[0]["record_id"] == "test-rec-1"


def test_pipeline_settlement_grace_period(temp_ledger):
    """Verify that records within the 6-hour settlement grace period remain PENDING instead of EXCLUDED."""
    pipe = ProspectiveEvidencePipeline(ledger_path=temp_ledger)
    
    issue_time = "2026-08-01T00:00:00+00:00"
    pipe.record_forecast(
        issue_timestamp_utc=issue_time,
        target_name="rv24h_var_ann",
        horizon_hours=24,
        feature_cutoff_utc=issue_time,
        baseline_predictions={"persistence": 0.04},
        challenger_prediction={"point": 0.045, "q10": 0.03, "q90": 0.06},
        model_version="HAR-QLIKE-24H-v1.0",
        artifact_hash="abc123def456",
        feature_schema_hash="ctx123",
    )
    # Maturity is 2026-08-02T00:00:00+00:00
    # Simulate current time 3 hours after maturity (within 6h grace period)
    now_within_grace = datetime(2026, 8, 2, 3, 0, tzinfo=timezone.utc)
    
    # Empty candles_df (exchange delay simulation)
    empty_candles = pd.DataFrame(columns=["close"], index=pd.DatetimeIndex([], tz=timezone.utc))
    resolved, skipped = pipe.resolve_matured_forecasts(empty_candles, current_utc=now_within_grace)
    
    assert resolved == 0
    assert skipped == 1
    
    records = pipe.load_all_records()
    assert records[0]["resolution_state"] == "PENDING"
    
    # Simulate current time 8 hours after maturity (exceeds 6h grace period)
    now_past_grace = datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc)
    resolved, skipped = pipe.resolve_matured_forecasts(empty_candles, current_utc=now_past_grace)
    assert resolved == 1  # Finalized as EXCLUDED
    assert skipped == 0
    
    records = pipe.load_all_records()
    assert records[0]["resolution_state"] == "EXCLUDED"
    assert "INCOMPLETE_FORWARD_CANDLES_EXCEEDED_GRACE" in records[0]["exclusion_reason"]



def test_prospective_worker_run_cycle(tmp_path):
    """Verify ProspectiveEvidenceWorker completes a cycle and writes status JSON."""
    status_file = tmp_path / "worker_status.json"
    worker = ProspectiveEvidenceWorker(status_path=str(status_file))
    
    result = worker.run_cycle()
    assert result["status"] == "SUCCESS"
    assert os.path.isfile(str(status_file))

    
    with open(str(status_file), "r", encoding="utf-8") as f:
        status_data = json.load(f)
    
    assert status_data["worker_version"] in ("PROSPECTIVE-WORKER-v1.0", "PROSPECTIVE-WORKER-v2.0")
    assert status_data["last_cycle_status"] == "SUCCESS"
    assert "ledger_summary" in status_data
    assert "runtime_environment" in status_data


def test_api_prospective_ledger_telemetry():
    """Verify GET /api/research/prospective-ledger returns ledger records and worker telemetry."""
    response = client.get("/api/research/prospective-ledger")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "records" in data
    assert "worker_telemetry" in data
    if data["worker_telemetry"] is not None:
        assert data["worker_telemetry"]["worker_version"] in ("PROSPECTIVE-WORKER-v1.0", "PROSPECTIVE-WORKER-v2.0")


def test_dual_target_prospective_issuance_and_summary(tmp_path):
    """Verify worker logs prospective forecasts and tracks separate horizon hurdles."""
    ledger_file = tmp_path / "dual_ledger.jsonl"
    status_file = tmp_path / "dual_status.json"
    worker = ProspectiveEvidenceWorker(ledger_path=str(ledger_file), status_path=str(status_file))
    
    result = worker.run_cycle(sync_live=False)
    assert result["status"] == "SUCCESS"
    assert len(result["forecasts_issued"]) >= 1
    
    summary = worker.pipeline.get_ledger_summary()
    assert "clean_prospective_blocks_24h" in summary
    assert "clean_prospective_blocks_168h" in summary
    assert summary["confirmatory_hurdle_threshold"] == 100
    assert summary["definitive_hurdle_threshold"] == 2160
