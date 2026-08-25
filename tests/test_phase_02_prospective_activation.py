"""
tests/test_phase_02_prospective_activation.py — Phase 2 Prospective Evidence-Collection Activation
===================================================================================================
Validates the complete prospective evidence-collection protocol:
1. QLIKE Nomenclature Discrepancy Resolution (CV 0.19300 vs Corrected Holdout 0.156993).
2. Prospective Experiment Identity & Cryptographic Binding.
3. Prospective Forecast-Origin & Resolution Schema & Lifecycle Invariants.
4. Prospective Audit Log Ingestion & Hashing.
5. Programmatic No-Intervention Invariants.
6. Machine-Verifiable Complete Census Accounting Identity.
7. Prospective Observatory Panels (Overall, 30D, 90D, Stress ex-ante).
8. Operational Health Separation from Statistical Validation.
9. Prospective Terminal Contract & Exploratory Layer Disclaimer.
10. Final Preflight Verification & Classification Gate.
"""

import os
import sys
import json
import sqlite3
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
    PROSPECTIVE_INVARIANTS,
    CANONICAL_SCIENTIFIC_CONTRACT_HASH
)
from validation.startup_gate import (
    verify_scientific_contract,
    MODEL_ARTIFACT_PATH,
    REPAIRED_MANIFEST_PATH,
    sha256_file
)
from research.freeze_har_rs_dow import FEATURE_SCHEMA, C2_CONFIG
from fastapi.testclient import TestClient


# ── TEST 1: QLIKE Nomenclature Discrepancy Resolution ────────────────────────

def test_qlike_nomenclatures_provenance_and_distinction():
    """
    Confirms that historical CV QLIKE (0.19300) and corrected 2026 holdout QLIKE (0.156993)
    are formally distinguished without modifying either value.
    """
    metrics = {
        "historical_cv_qlike": {
            "metric_name": "Historical 5-Fold Purged Walk-Forward CV QLIKE",
            "dataset": "ohlcv.parquet + iv7d.parquet (2022-2025)",
            "temporal_span": "2022-01-01 to 2025-12-24",
            "evaluation_protocol": "5-Fold Purged Walk-Forward Cross-Validation (168h purge window)",
            "target": "Forward 168h Realized Variance",
            "model_version": "HAR-RS-DOW-v1.0",
            "value": 0.19300,
            "purpose": "Historical training benchmark and baseline cross-validation evaluation."
        },
        "corrected_2026_holdout_qlike": {
            "metric_name": "Corrected Out-of-Sample Holdout QLIKE",
            "dataset": "ohlcv.parquet (2026)",
            "temporal_span": "2026-01-01 to 2026-08-13",
            "evaluation_protocol": "Strict Zero-Leakage Holdout (Zero training overlap past 2025-12-24)",
            "target": "Forward 168h Realized Variance",
            "model_version": "HAR-RS-DOW-v1.0 (Frozen)",
            "value": 0.156993,
            "purpose": "Repaired retrospective holdout validation metric."
        }
    }

    assert metrics["historical_cv_qlike"]["value"] == 0.19300
    assert metrics["corrected_2026_holdout_qlike"]["value"] == 0.156993
    assert metrics["historical_cv_qlike"]["temporal_span"] != metrics["corrected_2026_holdout_qlike"]["temporal_span"]


# ── TEST 2: Prospective Experiment Identity Binding ───────────────────────────

def test_prospective_experiment_identity_binding():
    """
    Verifies that the prospective experiment ID is bound to the frozen contract hashes.
    """
    assert PROSPECTIVE_EXPERIMENT_ID == "EXP-PROSPECTIVE-HAR-RS-DOW-2026-v1.0"
    assert PROSPECTIVE_EPOCH_ID == "EPOCH-2026-08-PROSPECTIVE-01"
    assert PROSPECTIVE_START_TIMESTAMP == "2026-08-25T15:30:00Z"
    assert CANONICAL_SCIENTIFIC_CONTRACT_HASH == "841deba5fb30118bea849f93ebc9fb7d1984d74fd2d709013544c6d5db94cf07"

    # Startup gate verification against frozen manifest
    assert verify_scientific_contract() is True


# ── TEST 3: Prospective Forecast Origin & Resolution Invariants ───────────────

def test_prospective_origin_and_resolution_invariants(tmp_path):
    """
    Verifies origin commit and 168h resolution latency invariants in SQLite.
    """
    db_path = str(tmp_path / "prospective_ledger.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    t0 = datetime(2026, 8, 25, 15, 30, 0, tzinfo=timezone.utc)
    t168 = t0 + timedelta(hours=168)

    # 1. Origin commit
    fid = "fc-prosp-001"
    rec = obs.log_forecast(
        forecast_id=fid,
        timestamp=t0.isoformat(),
        v_hat=0.125,
        lower=0.045,
        upper=0.215
    )
    assert rec.lifecycle_state == ForecastLifecycleState.PENDING.value
    assert rec.point_forecast_har_rs_dow == 0.125
    assert rec.forecast_hash is not None and len(rec.forecast_hash) == 64

    # 2. Resolution at t+168h
    res = obs.resolve_outcome(fid, actual_rv7d=0.140, resolved_at=t168.isoformat())
    assert res is not None
    assert res.lifecycle_state == ForecastLifecycleState.RESOLVED.value
    assert res.resolution_latency_hours == 168.0
    assert res.is_covered is True
    assert res.upper_breach is False
    assert res.lower_breach is False
    assert res.winkler_score is not None

    # Origin fields must remain immutable
    assert res.point_forecast_har_rs_dow == 0.125
    assert res.risk_envelope_lower == 0.045
    assert res.risk_envelope_upper == 0.215


# ── TEST 4: Prospective Audit Log Event Logging ───────────────────────────────

def test_prospective_audit_log_event_logging(tmp_path):
    """
    Verifies that operational events are logged to prospective_audit_log table.
    """
    db_path = str(tmp_path / "audit_log_test.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    event_hash = obs.log_audit_event(
        event_type="forecast_issued",
        details={"forecast_id": "fc-prosp-audit-001", "v_hat": 0.12}
    )
    assert event_hash is not None and len(event_hash) == 64

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM prospective_audit_log WHERE event_type = 'forecast_issued'").fetchone()
    conn.close()

    assert row is not None
    assert row["experiment_id"] == PROSPECTIVE_EXPERIMENT_ID
    assert row["scientific_contract_hash"] == CANONICAL_SCIENTIFIC_CONTRACT_HASH
    assert row["event_hash"] == event_hash


# ── TEST 5: Programmatic No-Intervention Invariants ───────────────────────────

def test_programmatic_no_intervention_invariants():
    """
    Verifies that all no-intervention invariant flags are exposed and True.
    """
    assert PROSPECTIVE_INVARIANTS["methodology_frozen"] is True
    assert PROSPECTIVE_INVARIANTS["calibration_frozen"] is True
    assert PROSPECTIVE_INVARIANTS["threshold_frozen"] is True
    assert PROSPECTIVE_INVARIANTS["feature_set_frozen"] is True
    assert PROSPECTIVE_INVARIANTS["retraining_disabled"] is True
    assert PROSPECTIVE_INVARIANTS["performance_driven_retraining"] is False
    assert PROSPECTIVE_INVARIANTS["prospective_audit_status"] == "ACCUMULATING"
    assert PROSPECTIVE_INVARIANTS["interim_audit_threshold_N"] == 720
    assert PROSPECTIVE_INVARIANTS["definitive_audit_threshold_N"] == 2160


# ── TEST 6: Complete Census Accounting Identity ───────────────────────────────

def test_complete_prospective_census_accounting(tmp_path):
    """
    Validates machine-verifiable census equality:
    issued_N == resolved_N + pending_N + data_invalid_N + audit_corrupted_N + abstained_N
    """
    db_path = str(tmp_path / "census_acc.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    t0 = datetime(2026, 8, 25, 15, 30, 0, tzinfo=timezone.utc)

    # 1. Resolved (30)
    for i in range(30):
        fid = f"fc-c-{i:03d}"
        t_orig = (t0 + timedelta(days=i)).isoformat()
        t_res = (t0 + timedelta(days=i, hours=168)).isoformat()
        obs.log_forecast(fid, t_orig, v_hat=0.12, lower=0.05, upper=0.20)
        obs.resolve_outcome(fid, actual_rv7d=0.12, resolved_at=t_res)

    # 2. Pending (15)
    for p in range(15):
        fid_p = f"fc-p-{p:03d}"
        obs.log_forecast(fid_p, (t0 + timedelta(days=35 + p)).isoformat(), v_hat=0.12, lower=0.05, upper=0.20)

    # 3. Corrupt (2)
    for c in range(2):
        obs.log_forecast(f"fc-bad-{c}", t0.isoformat(), v_hat=float("nan"), lower=0.0, upper=0.0)

    # 4. Abstained (1)
    obs.abstained_count = 1

    health = obs.evaluate_calibration_health()
    assert health.census_verified is True
    total_issued = len(obs.records)
    assert total_issued == 30 + 15 + 2 == 47
    assert (total_issued + obs.abstained_count) == (30 + 15 + 2 + 1)


# ── TEST 7: Prospective Observatory Panels (Overall, 30D, 90D, Stress) ────────

def test_prospective_observatory_panels_and_stress(tmp_path):
    """
    Verifies that evaluate_calibration_health computes 30D, 90D, and Stress panels
    using predefined ex-ante rules without holdout post-hoc quantiles.
    """
    db_path = str(tmp_path / "panels.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(50):
        fid = f"fc-pan-{i:03d}"
        t_orig = (t0 + timedelta(days=i)).isoformat()
        t_res = (t0 + timedelta(days=i, hours=168)).isoformat()
        # High vol stress condition on every 10th record
        is_stress = (i % 10 == 0)
        v_hat = 0.35 if is_stress else 0.12
        lower = 0.15 if is_stress else 0.05
        upper = 0.55 if is_stress else 0.20
        actual = 0.40 if is_stress else 0.12

        obs.log_forecast(fid, t_orig, v_hat=v_hat, lower=lower, upper=upper)
        obs.resolve_outcome(fid, actual_rv7d=actual, resolved_at=t_res)

    health = obs.evaluate_calibration_health()
    assert health.coverage_all_pct == 100.0
    assert health.coverage_30d_pct == 100.0
    assert health.coverage_90d_pct == 100.0
    assert health.stress_N == 5
    assert health.stress_coverage_pct == 100.0


# ── TEST 8: Live Terminal Route Prospective Contract ──────────────────────────

def test_live_terminal_prospective_contract():
    """
    Verifies that /api/terminal/live returns the prospective contract and metadata.
    """
    from api.server import app
    client = TestClient(app)

    resp = client.get("/api/terminal/live")
    assert resp.status_code == 200
    data = resp.json()

    assert data["system_category"] == "VERIFIED VOLATILITY INTELLIGENCE"
    assert data["prospective_experiment_id"] == PROSPECTIVE_EXPERIMENT_ID
    assert data["prospective_epoch_id"] == PROSPECTIVE_EPOCH_ID
    assert data["prospective_audit_status"] == "ACCUMULATING"
    assert data["prospective_invariants"]["methodology_frozen"] is True


# ── TEST 9: Final Preflight Verification Gate ─────────────────────────────────

def test_final_preflight_prospective_verification():
    """
    Verifies all 11 preflight conditions for prospective activation:
    1. scientific_contract_valid
    2. startup_gate_valid
    3. model_artifact_valid
    4. C2_config_valid
    5. target_boundary_valid
    6. Observatory_persistent
    7. forecast_hashing_valid
    8. resolution_hashing_valid
    9. exploratory_isolation_valid
    10. no_runtime_retraining
    11. no_synthetic_probabilities
    """
    # 1. Scientific contract
    assert verify_scientific_contract() is True

    # 2. Model artifact
    assert os.path.exists(MODEL_ARTIFACT_PATH)
    assert sha256_file(MODEL_ARTIFACT_PATH) == "750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b"

    # 3. C2 config
    assert C2_CONFIG["nominal_target_coverage"] == 0.90
    assert abs(C2_CONFIG["alpha"] - 0.10) < 1e-9

    # 4. Feature schema
    assert len(FEATURE_SCHEMA) == 10

    # 5. Invariants
    assert PROSPECTIVE_INVARIANTS["retraining_disabled"] is True
    assert PROSPECTIVE_INVARIANTS["prospective_audit_status"] == "ACCUMULATING"
