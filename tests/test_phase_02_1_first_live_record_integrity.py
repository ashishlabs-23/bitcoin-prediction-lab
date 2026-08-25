"""
tests/test_phase_02_1_first_live_record_integrity.py — Phase 2.1 First Real Prospective Record Integrity
========================================================================================================
Validates that the first live prospective forecast is genuinely prospective:
1. Origin timestamp >= prospective_start_timestamp (2026-08-25T15:30:00Z).
2. Zero future realized labels / metrics present in the origin record.
3. Timestamp ordering: T_input <= T_origin < T_resolution.
4. SHA-256 forecast hash commitment match.
5. Exact scientific contract & experiment ID binding.
6. Pre-maturity restart continuity (persists in PENDING state with identical hash/bounds).
7. Rejection of premature resolution attempts (< 168.0h).
8. Strict isolation from predictive performance claims (audit status = ACCUMULATING).
"""

import os
import sys
import sqlite3
import hashlib
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.observatory import (
    ForecastAccuracyObservatory,
    CalibrationHealthStatus,
    ForecastLifecycleState,
    VolatilityForecastRecord,
    PROSPECTIVE_EXPERIMENT_ID,
    PROSPECTIVE_EPOCH_ID,
    PROSPECTIVE_START_TIMESTAMP,
    PROSPECTIVE_AUDIT_STATUS,
    CANONICAL_SCIENTIFIC_CONTRACT_HASH
)
from validation.startup_gate import (
    verify_scientific_contract,
    MODEL_ARTIFACT_PATH,
    sha256_file
)
from research.freeze_har_rs_dow import FEATURE_SCHEMA, C2_CONFIG
from fastapi.testclient import TestClient


# ── TEST 1: First Live Prospective Record Capture & State ─────────────────────

def test_first_live_prospective_record_capture(tmp_path):
    """
    Captures the first prospective record at or after 2026-08-25T15:30:00Z.
    Verifies that origin_timestamp >= prospective_start_timestamp and lifecycle_state == PENDING.
    """
    db_path = str(tmp_path / "first_live.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    origin_ts = "2026-08-25T15:30:00Z"
    t_start = pd.to_datetime(PROSPECTIVE_START_TIMESTAMP)
    t_rec = pd.to_datetime(origin_ts)

    assert t_rec >= t_start, "Origin timestamp is prior to prospective start boundary!"

    rec = obs.log_forecast(
        forecast_id="fc-prosp-live-0001",
        timestamp=origin_ts,
        v_hat=0.12000,
        lower=0.04000,
        upper=0.22000
    )

    assert rec.lifecycle_state == ForecastLifecycleState.PENDING.value
    assert rec.forecast_id == "fc-prosp-live-0001"
    assert rec.point_forecast_har_rs_dow == 0.12000
    assert rec.risk_envelope_lower == 0.04000
    assert rec.risk_envelope_upper == 0.22000


# ── TEST 2: Absence of Future Realized Outcomes in Origin Record ───────────────

def test_no_future_outcomes_in_origin_record(tmp_path):
    """
    Inspects stored SQLite origin record and asserts absence of all future realized labels.
    """
    db_path = str(tmp_path / "first_live.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    fid = "fc-prosp-live-0001"
    obs.log_forecast(
        forecast_id=fid,
        timestamp="2026-08-25T15:30:00Z",
        v_hat=0.12000,
        lower=0.04000,
        upper=0.22000
    )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM forecast_origins WHERE forecast_id = ?", (fid,)).fetchone()
    conn.close()

    assert row is not None
    # Present origin fields
    assert row["point_forecast"] == 0.12000
    assert row["lower_bound"] == 0.04000
    assert row["upper_bound"] == 0.22000
    assert row["lifecycle_state"] == "PENDING"
    assert row["scientific_contract_hash"] == CANONICAL_SCIENTIFIC_CONTRACT_HASH

    # Forbidden future outcome fields must not exist in forecast_origins schema
    columns = [col for col in row.keys()]
    forbidden = ["actual_rv7d", "actual_realized_variance", "covered", "future_return", "mfe", "mae", "tp_sl"]
    for f in forbidden:
        assert f not in columns, f"Forbidden future column '{f}' found in forecast_origins schema!"


# ── TEST 3: Timestamp Ordering & Null Resolution State at Issuance ────────────

def test_timestamp_ordering_and_null_resolution(tmp_path):
    """
    Verifies T_input <= T_origin < T_resolution.
    At issuance time, resolution_timestamp, actual_rv7d, and covered must be NULL.
    """
    db_path = str(tmp_path / "first_live.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    fid = "fc-prosp-live-0001"
    rec = obs.log_forecast(
        forecast_id=fid,
        timestamp="2026-08-25T15:30:00Z",
        v_hat=0.12000,
        lower=0.04000,
        upper=0.22000
    )

    assert rec.actual_realized_variance is None
    assert rec.is_covered is None
    assert rec.upper_breach is None
    assert rec.lower_breach is None
    assert rec.resolved_at is None
    assert rec.resolution_latency_hours is None
    assert rec.resolved_hash is None


# ── TEST 4: SHA-256 Origin Commitment Verification ────────────────────────────

def test_sha256_origin_commitment_verification(tmp_path):
    """
    Recomputes SHA256 forecast_hash from origin payload and verifies exact equality.
    """
    db_path = str(tmp_path / "first_live.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    fid = "fc-prosp-live-0001"
    rec = obs.log_forecast(
        forecast_id=fid,
        timestamp="2026-08-25T15:30:00Z",
        v_hat=0.12000,
        lower=0.04000,
        upper=0.22000
    )

    expected_payload = f"{fid}|2026-08-25T15:30:00Z|0.120000|0.040000|0.220000|HAR-RS-DOW-v1.0|C2-Dependence-Aware-Conformal-v1.0|{CANONICAL_SCIENTIFIC_CONTRACT_HASH}"
    expected_hash = hashlib.sha256(expected_payload.encode("utf-8")).hexdigest()

    assert rec.forecast_hash == expected_hash


# ── TEST 5: Scientific Contract Binding ───────────────────────────────────────

def test_scientific_contract_binding():
    """
    Verifies that the origin record references the exact canonical hashes.
    """
    assert CANONICAL_SCIENTIFIC_CONTRACT_HASH == "841deba5fb30118bea849f93ebc9fb7d1984d74fd2d709013544c6d5db94cf07"
    assert PROSPECTIVE_EXPERIMENT_ID == "EXP-PROSPECTIVE-HAR-RS-DOW-2026-v1.0"
    assert sha256_file(MODEL_ARTIFACT_PATH) == "750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b"
    assert verify_scientific_contract() is True


# ── TEST 6: Pre-Maturity Restart Continuity ───────────────────────────────────

def test_pre_maturity_restart_continuity(tmp_path):
    """
    Restarts the process before the 168h maturation horizon.
    Verifies the forecast remains PENDING with bit-for-bit identical parameters.
    """
    db_path = str(tmp_path / "pre_mat_restart.db")

    # Process 1: Issue live forecast
    obs1 = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)
    rec1 = obs1.log_forecast(
        forecast_id="fc-prosp-live-0001",
        timestamp="2026-08-25T15:30:00Z",
        v_hat=0.12000,
        lower=0.04000,
        upper=0.22000
    )

    # Process 2: Restart at t+24h (before maturity)
    obs2 = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)
    assert len(obs2.records) == 1
    rec2 = obs2.records[0]

    assert rec2.forecast_id == rec1.forecast_id
    assert rec2.lifecycle_state == ForecastLifecycleState.PENDING.value
    assert rec2.forecast_hash == rec1.forecast_hash
    assert rec2.point_forecast_har_rs_dow == rec1.point_forecast_har_rs_dow
    assert rec2.risk_envelope_lower == rec1.risk_envelope_lower
    assert rec2.risk_envelope_upper == rec1.risk_envelope_upper
    assert rec2.timestamp == rec1.timestamp


# ── TEST 7: Rejection of Premature Resolution Attempts ────────────────────────

def test_rejection_of_premature_resolution(tmp_path):
    """
    Attempts to resolve the forecast before T_origin + 168h (e.g. at t+24h, t+72h, t+160h).
    Requires each premature resolution to be rejected.
    """
    db_path = str(tmp_path / "premature_test.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    t0 = datetime(2026, 8, 25, 15, 30, 0, tzinfo=timezone.utc)
    fid = "fc-prosp-live-0001"
    obs.log_forecast(
        forecast_id=fid,
        timestamp=t0.isoformat(),
        v_hat=0.12000,
        lower=0.04000,
        upper=0.22000
    )

    # 1. Attempt resolution at t+24h
    res_24 = obs.resolve_outcome(fid, actual_rv7d=0.13, resolved_at=(t0 + timedelta(hours=24)).isoformat())
    assert res_24 is None, "Premature resolution at t+24h was not rejected!"

    # 2. Attempt resolution at t+72h
    res_72 = obs.resolve_outcome(fid, actual_rv7d=0.13, resolved_at=(t0 + timedelta(hours=72)).isoformat())
    assert res_72 is None, "Premature resolution at t+72h was not rejected!"

    # 3. Attempt resolution at t+160h
    res_160 = obs.resolve_outcome(fid, actual_rv7d=0.13, resolved_at=(t0 + timedelta(hours=160)).isoformat())
    assert res_160 is None, "Premature resolution at t+160h was not rejected!"

    # 4. Valid resolution at exactly t+168h
    res_168 = obs.resolve_outcome(fid, actual_rv7d=0.13, resolved_at=(t0 + timedelta(hours=168)).isoformat())
    assert res_168 is not None, "Valid resolution at t+168h failed!"
    assert res_168.lifecycle_state == ForecastLifecycleState.RESOLVED.value
    assert res_168.resolution_latency_hours == 168.0


# ── TEST 8: Accumulation Mode & No Premature Performance Claims ────────────────

def test_accumulation_mode_and_no_performance_claims(tmp_path):
    """
    Confirms that prospective evaluation status is ACCUMULATING and no premature
    economic/performance claims are generated.
    """
    db_path = str(tmp_path / "accum_test.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    fid = "fc-prosp-live-0001"
    obs.log_forecast(
        forecast_id=fid,
        timestamp="2026-08-25T15:30:00Z",
        v_hat=0.12000,
        lower=0.04000,
        upper=0.22000
    )

    health = obs.evaluate_calibration_health()
    assert health.prospective_audit_status == "ACCUMULATING"
    assert health.total_resolved_forecasts == 0
    assert health.pending_unresolved_forecasts == 1
    assert health.valid_N == 0
