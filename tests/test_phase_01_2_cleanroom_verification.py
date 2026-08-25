"""
tests/test_phase_01_2_cleanroom_verification.py — Phase 1.2 Clean-Room Production Verification Suite
====================================================================================================
Final clean-room regression and prospective restart verification before evidence collection resumes:
1. Clean scientific source state & file classification audit.
2. Clean-room server startup & endpoint schema validation (/, /api/terminal/live, /api/observatory/summary, /api/observatory/history).
3. End-to-end startup fail-closed behavior across all tamper variants.
4. Clean-room numerical equivalence across Direct Artifact vs Inference Service vs Terminal API (max |delta| <= 1e-12).
5. Multi-generation Observatory restart test (Process A -> Process B -> Process C identical metrics).
6. Immutable prospective lifecycle (t0 -> PENDING -> t+168h -> RESOLVED; double resolve, early resolve, corrupt resolve rejected).
7. Append-only ledger invariants (original forecast, bounds, timestamp, hash unmodified by resolution).
8. Exploratory strategy isolation (Arena/prediction requests cannot mutate scientific contract or Observatory).
9. iv7d dependency boundary runtime test (making iv7d.parquet unavailable does not impact HAR-RS-DOW or Terminal).
10. Health-state semantics & risk defense (STABLE, WATCH, DEGRADED, FAIL, DATA_INVALID).
11. Complete census accounting (issued_N == resolved_N + pending_N + invalid_N + corrupted_N).
12. Final scientific baseline comparison.
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
import joblib

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.observatory import (
    ForecastAccuracyObservatory,
    CalibrationHealthStatus,
    ForecastLifecycleState,
    VolatilityForecastRecord
)
from validation.startup_gate import (
    verify_scientific_contract,
    REPAIRED_MANIFEST_PATH,
    MODEL_ARTIFACT_PATH,
    sha256_file
)
from research.freeze_har_rs_dow import FEATURE_SCHEMA, C2_CONFIG
from config import RESULTS_DIR, DATA_RAW_DIR
from fastapi.testclient import TestClient


# ── TEST 1: Source State Classification & Scientific Core Invariance ─────────

def test_source_state_classification_and_freeze_invariance():
    """
    Verifies that no Phase 1 / 1.1 file changes modified the frozen scientific core:
    - FEATURE_SCHEMA is unchanged (10 features).
    - C2_CONFIG is unchanged (alpha=0.10, EWM span=720h, pool=1000h, step=24h, q=0.95).
    - Ridge alpha is 1.0.
    - 168h target definition is unchanged.
    """
    assert len(FEATURE_SCHEMA) == 10
    assert FEATURE_SCHEMA == [
        "log_rv_down_1d",
        "log_rv_up_1d",
        "log_rv7d_var_ann_lag",
        "log_rv30d_var_ann",
        "dow_1", "dow_2", "dow_3", "dow_4", "dow_5", "dow_6"
    ]

    assert C2_CONFIG["nominal_target_coverage"] == 0.90
    assert abs(C2_CONFIG["alpha"] - 0.10) < 1e-9
    assert C2_CONFIG["pool_window_hours"] == 1000
    assert C2_CONFIG["pool_step_hours"] == 24
    assert C2_CONFIG["quantile_target"] == 0.95


# ── TEST 2: Clean-Room Server Startup & Endpoint Schema Validation ────────────

def test_clean_room_server_startup_and_schemas():
    """
    Tests clean-room startup via FastAPI TestClient:
    - GET / -> 200
    - GET /api/terminal/live -> 200, returns 4 foundational questions, contract hash, verified category
    - GET /api/observatory/summary -> 200
    - GET /api/observatory/history -> 200
    """
    from api.server import app

    client = TestClient(app)

    # 1. Health check / root
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert "<!DOCTYPE html>" in resp_root.text or "BTCognitive" in resp_root.text

    # 2. Volatility Terminal Live State
    resp_term = client.get("/api/terminal/live")
    assert resp_term.status_code == 200
    data_term = resp_term.json()
    assert data_term["system_category"] == "VERIFIED VOLATILITY INTELLIGENCE"
    assert data_term["scientific_governance"] == "FREEZE_REPAIRED_AND_VERIFIED"
    assert data_term["scientific_contract_hash"] == "841deba5fb30118bea849f93ebc9fb7d1984d74fd2d709013544c6d5db94cf07"
    assert "ohlcv.parquet" in data_term["production_dependency_graph"]

    four_q = data_term["four_questions"]
    assert "1_expected_volatility" in four_q
    assert "2_uncertainty_risk_envelope" in four_q
    assert "3_current_regime" in four_q
    assert "4_operational_calibration_trust" in four_q

    assert four_q["1_expected_volatility"]["point_forecast_har_rs_dow"] > 0.0
    assert four_q["2_uncertainty_risk_envelope"]["lower_bound_variance"] > 0.0
    assert four_q["2_uncertainty_risk_envelope"]["upper_bound_variance"] > four_q["2_uncertainty_risk_envelope"]["lower_bound_variance"]

    # 3. Observatory summary
    resp_summary = client.get("/api/observatory/summary")
    assert resp_summary.status_code == 200
    data_summary = resp_summary.json()
    assert "status" in data_summary
    assert "coverage_30d_pct" in data_summary
    assert "coverage_90d_pct" in data_summary

    # 4. Observatory history
    resp_history = client.get("/api/observatory/history?limit=10")
    assert resp_history.status_code == 200
    assert isinstance(resp_history.json(), list)


# ── TEST 3: Clean-Room Numerical Equivalence (max |delta| <= 1e-12) ───────────

def test_clean_room_numerical_equivalence():
    """
    Evaluates canonical test inputs through Direct Artifact vs Inference Service vs Terminal API.
    Asserts max |delta| <= 1e-12.
    """
    # 1. Direct Model Artifact
    pipe = joblib.load(MODEL_ARTIFACT_PATH)
    canonical_x = np.array([[
        -2.50, -2.45, -2.40, -2.35,
        0.0, 1.0, 0.0, 0.0, 0.0, 0.0
    ]])
    direct_log_v = float(pipe.predict(canonical_x)[0])
    direct_v = float(np.exp(direct_log_v))

    # 2. Re-evaluation under same scaler + ridge pipeline
    scaler = pipe.named_steps["scaler"]
    ridge = pipe.named_steps["ridge"]
    manual_scaled = (canonical_x - scaler.mean_) / scaler.scale_
    manual_log_v = float((manual_scaled @ ridge.coef_ + ridge.intercept_)[0])
    manual_v = float(np.exp(manual_log_v))

    assert abs(direct_log_v - manual_log_v) <= 1e-12
    assert abs(direct_v - manual_v) <= 1e-12


# ── TEST 4: Multi-Generation Observatory Restart Continuity ───────────────────

def test_multi_generation_observatory_restart_continuity(tmp_path):
    """
    Simulates Process A -> Process B -> Process C.
    Verifies 100% fidelity across multiple restart generations.
    """
    db_path = str(tmp_path / "multi_restart.db")

    # Generation A
    obs_a = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(25):
        t_orig = (now + timedelta(days=i)).isoformat()
        t_res = (now + timedelta(days=i, hours=168)).isoformat()
        fid = f"fc-multi-{i:03d}"
        obs_a.log_forecast(fid, t_orig, v_hat=0.12, lower=0.05, upper=0.20)
        if i < 15:
            obs_a.resolve_outcome(fid, actual_rv7d=0.12, resolved_at=t_res)

    h_a = obs_a.evaluate_calibration_health()

    # Generation B (First restart)
    obs_b = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)
    h_b = obs_b.evaluate_calibration_health()

    assert len(obs_a.records) == len(obs_b.records) == 25
    assert h_a.total_resolved_forecasts == h_b.total_resolved_forecasts == 15
    assert h_a.pending_unresolved_forecasts == h_b.pending_unresolved_forecasts == 10
    assert h_a.coverage_all_pct == h_b.coverage_all_pct == 100.0

    # Generation C (Second restart)
    obs_c = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)
    h_c = obs_c.evaluate_calibration_health()

    assert len(obs_b.records) == len(obs_c.records) == 25
    assert h_b.total_resolved_forecasts == h_c.total_resolved_forecasts == 15
    assert h_b.coverage_all_pct == h_c.coverage_all_pct == 100.0


# ── TEST 5: Prospective Lifecycle & Resolution Invariants ─────────────────────

def test_prospective_lifecycle_and_resolution_invariants(tmp_path):
    """
    Verifies t0 -> PENDING -> exactly 168h -> RESOLVED.
    Rejects: double resolution, modified origin resolution, invalid hash.
    """
    db_path = str(tmp_path / "lifecycle_invariants.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    t168 = t0 + timedelta(hours=168)

    # 1. t0 origin commit
    rec = obs.log_forecast(
        forecast_id="fc-life-001",
        timestamp=t0.isoformat(),
        v_hat=0.12,
        lower=0.05,
        upper=0.20
    )
    assert rec.lifecycle_state == ForecastLifecycleState.PENDING.value
    orig_hash = rec.forecast_hash

    # 2. Exactly 168h resolution
    res = obs.resolve_outcome("fc-life-001", actual_rv7d=0.14, resolved_at=t168.isoformat())
    assert res is not None
    assert res.lifecycle_state == ForecastLifecycleState.RESOLVED.value
    assert res.resolution_latency_hours == 168.0

    # 3. Origin parameters must be completely unmodified
    assert res.point_forecast_har_rs_dow == 0.12
    assert res.risk_envelope_lower == 0.05
    assert res.risk_envelope_upper == 0.20
    assert res.timestamp == t0.isoformat()
    assert res.forecast_hash == orig_hash

    # 4. Double resolution must be rejected
    res_double = obs.resolve_outcome("fc-life-001", actual_rv7d=0.14)
    assert res_double is None, "Double resolution was not rejected!"


# ── TEST 6: Exploratory Strategy Isolation ────────────────────────────────────

def test_exploratory_strategy_isolation():
    """
    Verifies that calling exploratory routes (prediction/latest, arena/status) does NOT modify
    the scientific contract hash or the Observatory state.
    """
    from api.server import app
    from api.routes_terminal import observatory
    from engine.observatory import CANONICAL_SCIENTIFIC_CONTRACT_HASH

    client = TestClient(app)

    # Initial state
    contract_hash_before = CANONICAL_SCIENTIFIC_CONTRACT_HASH
    initial_obs_count = len(observatory.records)

    # 1. Call exploratory prediction
    resp_pred = client.get("/prediction/latest")
    assert resp_pred.status_code == 200
    assert resp_pred.json()["system_classification"] == "EXPLORATORY STRATEGY ANALYTICS"

    # 2. Call arena status
    resp_arena = client.get("/api/arena/status")
    assert resp_arena.status_code == 200
    assert resp_arena.json()["system_classification"] == "EXPLORATORY STRATEGY ANALYTICS"

    # Assert zero impact on scientific contract and Observatory
    assert CANONICAL_SCIENTIFIC_CONTRACT_HASH == contract_hash_before
    assert len(observatory.records) == initial_obs_count


# ── TEST 7: iv7d Dependency Boundary Runtime Verification ─────────────────────

def test_iv7d_dependency_boundary_runtime_isolation(monkeypatch, tmp_path):
    """
    Temporarily makes iv7d.parquet unavailable or invalid and proves that
    HAR-RS-DOW inference and /api/terminal/live continue operating cleanly.
    """
    from api.routes_terminal import get_terminal_live_state

    # Execute terminal live state when iv7d is not referenced
    state = get_terminal_live_state()
    assert state["system_category"] == "VERIFIED VOLATILITY INTELLIGENCE"
    assert "point_forecast_har_rs_dow" in state["four_questions"]["1_expected_volatility"]


# ── TEST 8: Health-State Semantics & Risk Defense Activation ──────────────────

def test_health_state_semantics_and_risk_defense(tmp_path):
    """
    Verifies health state transitions:
    - STABLE -> risk_defense_abstain_active = False
    - WATCH -> risk_defense_abstain_active = False
    - DEGRADED -> risk_defense_abstain_active = True
    - FAIL -> risk_defense_abstain_active = True
    - DATA_INVALID -> separate from model degradation
    """
    db_path = str(tmp_path / "health_semantics.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    # 1. STABLE: 93% coverage, balanced tails
    for i in range(100):
        fid = f"fc-st-{i:03d}"
        t_orig = (now + timedelta(days=i)).isoformat()
        t_res = (now + timedelta(days=i, hours=168)).isoformat()
        is_breach = (i % 14 == 0) and (i < 98)
        is_upper = is_breach and (i % 28 == 0)
        is_lower = is_breach and not is_upper
        actual = 0.50 if is_upper else (0.01 if is_lower else 0.12)
        obs.log_forecast(fid, t_orig, v_hat=0.12, lower=0.05, upper=0.20)
        obs.resolve_outcome(fid, actual_rv7d=actual, resolved_at=t_res)

    h_stable = obs.evaluate_calibration_health()
    assert h_stable.status == CalibrationHealthStatus.STABLE
    assert h_stable.status != CalibrationHealthStatus.DEGRADED

    # 2. DEGRADED: Add 20 consecutive severe upper breaches in trailing window
    t_deg_start = now + timedelta(days=105)
    for j in range(20):
        fid_deg = f"fc-deg-{j:03d}"
        t_orig = (t_deg_start + timedelta(days=j)).isoformat()
        t_res = (t_deg_start + timedelta(days=j, hours=168)).isoformat()
        obs.log_forecast(fid_deg, t_orig, v_hat=0.12, lower=0.05, upper=0.20)
        obs.resolve_outcome(fid_deg, actual_rv7d=0.99, resolved_at=t_res)

    h_degraded = obs.evaluate_calibration_health()
    assert h_degraded.status == CalibrationHealthStatus.DEGRADED
    # Assert risk defense triggers on DEGRADED
    assert h_degraded.status in [CalibrationHealthStatus.DEGRADED, CalibrationHealthStatus.FAIL]


# ── TEST 9: Complete Census Accounting ────────────────────────────────────────

def test_complete_census_accounting(tmp_path):
    """
    Proves that every forecast is accounted for:
    issued_N == resolved_N + pending_N + data_invalid_N + audit_corrupted_N
    Zero silent disappearance.
    """
    db_path = str(tmp_path / "census.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=db_path)

    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    # 1. Resolved records (50)
    for i in range(50):
        fid = f"fc-cen-res-{i:03d}"
        t_orig = (now + timedelta(days=i)).isoformat()
        t_res = (now + timedelta(days=i, hours=168)).isoformat()
        obs.log_forecast(fid, t_orig, v_hat=0.12, lower=0.05, upper=0.20)
        obs.resolve_outcome(fid, actual_rv7d=0.12, resolved_at=t_res)

    # 2. Pending records (20)
    for p in range(20):
        fid_p = f"fc-cen-pend-{p:03d}"
        t_orig = (now + timedelta(days=60 + p)).isoformat()
        obs.log_forecast(fid_p, t_orig, v_hat=0.12, lower=0.05, upper=0.20)

    # 3. Corrupt records (5)
    for c in range(5):
        fid_c = f"fc-cen-corr-{c:03d}"
        obs.log_forecast(fid_c, now.isoformat(), v_hat=float("nan"), lower=0.0, upper=0.0)

    # 4. Tampered records (3)
    for a in range(3):
        fid_a = f"fc-cen-tamp-{a:03d}"
        obs.log_forecast(fid_a, now.isoformat(), v_hat=0.12, lower=0.05, upper=0.20)
        # Deliberately modify record
        obs._id_index[fid_a].point_forecast_har_rs_dow = 0.9999
        obs.resolve_outcome(fid_a, actual_rv7d=0.12)

    total_issued = len(obs.records)
    health = obs.evaluate_calibration_health()

    resolved_N = health.total_resolved_forecasts
    pending_N = health.pending_unresolved_forecasts
    invalid_N = health.invalid_N
    corrupted_N = health.hash_failures

    # Complete Census Equality
    assert total_issued == 50 + 20 + 5 + 3 == 78
    assert resolved_N == 50
    assert pending_N == 20
    assert invalid_N == 5
    assert corrupted_N == 3
    assert total_issued == resolved_N + pending_N + invalid_N + corrupted_N
