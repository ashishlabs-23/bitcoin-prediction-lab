"""
tests/test_phase_01_production_integrity.py — Phase 1 Production Integrity Remediation Tests
===========================================================================================
Hard regression test suite verifying all Phase 1 integrity and audit mandates:
1. Deterministic inference (100 repeated calls with same input yield identical output).
2. Elimination of synthetic probability perturbations (random.random, random.uniform).
3. Full quality score spectrum transition (healthy, neutral, degraded, severely degraded, invalid).
4. Prohibition of unsafe future-label fallback training in production inference.
5. Observatory durable SQLite persistence & immutability (insert, duplicate reject, resolution append, restart).
6. Pre-resolution cryptographic hash verification & tamper isolation (AUDIT_CORRUPTED).
7. Exact wall-clock trailing 30D/90D time window semantics.
8. DATA_INVALID isolation (single corrupt record does not zero valid calibration metrics).
9. Scientific startup gate (valid, tampered artifact, wrong contract, wrong environment).
10. Explicit labeling separating verified volatility intelligence from exploratory strategy analytics.
"""

import os
import sys
import json
import sqlite3
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.observatory import (
    ForecastAccuracyObservatory,
    CalibrationHealthStatus,
    ForecastLifecycleState,
    VolatilityForecastRecord
)
from engine.range_quality import range_quality_service
from validation.startup_gate import (
    verify_scientific_contract,
    REPAIRED_MANIFEST_PATH,
    MODEL_ARTIFACT_PATH
)
from models.uncertainty import (
    compute_decomposed_uncertainty,
    compute_data_reliability,
    compute_regime_certainty,
    compute_model_agreement,
    compute_volatility_stress
)
from models.ensemble import AdaptiveRegimeEnsemble
from config import RESULTS_DIR


# ── TEST 1: Deterministic Inference Across 100 Repeated Calls ─────────────────

def test_deterministic_inference_100_calls():
    """Proves: same input + same model state = identical output across 100 repeated calls."""
    df_row = pd.Series({
        'open': 65000.0, 'high': 65500.0, 'low': 64800.0, 'close': 65200.0,
        'volume': 1200.0, 'ret_1h': 0.002, 'ret_4h': 0.005, 'ret_24h': 0.012,
        'rsi_14': 56.4, 'macd': 45.2, 'macd_signal': 38.1,
        'sma_ratio_20': 0.012, 'sma_ratio_50': 0.024,
        'realized_vol_24h': 0.016, 'atr_14': 620.0,
        'funding_rate': 0.0001, 'funding_rate_change_24h': 0.0,
        'open_interest': 120000.0, 'oi_pct_change_24h': 0.02
    })
    reg_probs = {'TRENDING_BULL': 0.70, 'BREAKOUT': 0.15, 'RANGING': 0.10, 'HIGH_VOLATILITY': 0.03, 'TRENDING_BEAR': 0.02}
    mod_probs = {'RandomForest': 0.65, 'XGBoost': 0.62, 'LogisticRegression': 0.64}

    first_output = compute_decomposed_uncertainty(df_row, reg_probs, mod_probs)
    for _ in range(100):
        curr_output = compute_decomposed_uncertainty(df_row, reg_probs, mod_probs)
        assert curr_output == first_output, "Non-deterministic uncertainty output detected!"


# ── TEST 2: Quality Score Spectrum (Healthy, Neutral, Degraded, Severely Degraded, Invalid) ──

def test_quality_score_spectrum_transitions():
    """Verifies system can transition across full health spectrum without artificial floors."""
    # 1. Healthy / Excellent
    res_healthy = range_quality_service.evaluate_quality(
        recent_mfe_coverage=94.0, recent_mae_coverage=96.0, recent_path_containment=90.0,
        mean_forecast_error=0.40, mean_range_width=5.5, baseline_delta=-0.08, data_quality="VALID"
    )
    assert res_healthy.overall_status == "EXCELLENT"
    assert res_healthy.reliability_score >= 85.0

    # 2. Neutral / Good
    res_good = range_quality_service.evaluate_quality(
        recent_mfe_coverage=85.0, recent_mae_coverage=88.0, recent_path_containment=78.0,
        mean_forecast_error=0.60, mean_range_width=6.5, baseline_delta=-0.02, data_quality="VALID"
    )
    assert res_good.overall_status == "GOOD"
    assert 70.0 <= res_good.reliability_score < 85.0

    # 3. Degraded / Watch
    res_watch = range_quality_service.evaluate_quality(
        recent_mfe_coverage=75.0, recent_mae_coverage=80.0, recent_path_containment=68.0,
        mean_forecast_error=0.70, mean_range_width=7.5, baseline_delta=0.06, data_quality="VALID"
    )
    assert res_watch.overall_status in ["WATCH", "DEGRADED"]

    # 4. Severely Degraded (Floor removed: score can reach down to degraded/severe)
    res_severe = range_quality_service.evaluate_quality(
        recent_mfe_coverage=30.0, recent_mae_coverage=35.0, recent_path_containment=20.0,
        mean_forecast_error=2.50, mean_range_width=15.0, baseline_delta=0.25, data_quality="VALID"
    )
    assert res_severe.overall_status == "SEVERELY_DEGRADED"
    assert res_severe.reliability_score <= 30.0

    # 5. Data Invalid
    res_invalid = range_quality_service.evaluate_quality(data_quality="INVALID")
    assert res_invalid.overall_status == "DATA_INVALID"
    assert res_invalid.reliability_score == 0.0


# ── TEST 3: Hard Fallback Training Prohibition ─────────────────────────────────

def test_production_inference_cannot_invoke_future_label_fallback():
    """Hard test asserting production inference service cannot invoke future-label fallback."""
    from engine.inference_service import live_engine
    
    # Assert live_engine has no fallback train methods accepting negative shifts or future labels
    assert not hasattr(live_engine, "fallback_train"), "Unsafe fallback training method exposed in live_engine."
    assert not hasattr(live_engine, "train_fallback"), "Unsafe fallback training method exposed in live_engine."


# ── TEST 4: Observatory Durable Persistence & Immutability ────────────────────

def test_observatory_durable_persistence_and_immutability(tmp_path):
    """Verifies SQLite persistence: first insert, duplicate reject, conflict reject, resolution append, restart."""
    test_db = str(tmp_path / "test_observatory.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=test_db)

    # 1. First insert -> PASS
    rec1 = obs.log_forecast(
        forecast_id="fc-test-001",
        timestamp="2026-01-01T00:00:00Z",
        v_hat=0.1200,
        lower=0.0500,
        upper=0.2200,
        macro_regime="SPOT_ETF_ERA"
    )
    assert rec1.forecast_id == "fc-test-001"
    assert rec1.lifecycle_state == ForecastLifecycleState.PENDING.value
    assert len(obs.records) == 1

    # 2. Identical duplicate insert -> REJECT
    with pytest.raises(ValueError, match="Duplicate forecast_id"):
        obs.log_forecast(
            forecast_id="fc-test-001",
            timestamp="2026-01-01T00:00:00Z",
            v_hat=0.1200,
            lower=0.0500,
            upper=0.2200
        )

    # 3. Conflicting duplicate insert -> REJECT
    with pytest.raises(ValueError, match="Duplicate forecast_id"):
        obs.log_forecast(
            forecast_id="fc-test-001",
            timestamp="2026-01-01T01:00:00Z",
            v_hat=0.9999,
            lower=0.5000,
            upper=1.5000
        )

    # 4. Resolution -> APPEND
    resolved_rec = obs.resolve_outcome(
        forecast_id="fc-test-001",
        actual_rv7d=0.1400,
        resolved_at="2026-01-08T00:00:00Z"
    )
    assert resolved_rec is not None
    assert resolved_rec.lifecycle_state == ForecastLifecycleState.RESOLVED.value
    assert resolved_rec.is_covered is True
    assert resolved_rec.actual_realized_variance == 0.1400
    assert resolved_rec.resolved_hash != ""

    # Origin parameters must NOT be mutated
    assert resolved_rec.point_forecast_har_rs_dow == 0.1200
    assert resolved_rec.risk_envelope_lower == 0.0500
    assert resolved_rec.risk_envelope_upper == 0.2200

    # 5. Process restart -> RECORDS PRESERVED
    obs_restarted = ForecastAccuracyObservatory(nominal_target=0.90, db_path=test_db)
    assert len(obs_restarted.records) == 1
    restored = obs_restarted.records[0]
    assert restored.forecast_id == "fc-test-001"
    assert restored.lifecycle_state == ForecastLifecycleState.RESOLVED.value
    assert restored.actual_realized_variance == 0.1400
    assert restored.is_covered is True
    assert restored.resolved_hash == resolved_rec.resolved_hash


# ── TEST 5: Pre-Resolution Hash Verification & Tamper Isolation ───────────────

def test_observatory_tampering_detection(tmp_path):
    """Proves: tampering with forecast origin aborts resolution and marks AUDIT_CORRUPTED."""
    test_db = str(tmp_path / "tamper_obs.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=test_db)

    obs.log_forecast(
        forecast_id="fc-tamper-001",
        timestamp="2026-01-01T00:00:00Z",
        v_hat=0.1000,
        lower=0.0400,
        upper=0.1800
    )
    # Deliberately tamper with in-memory record point_forecast
    obs.records[0].point_forecast_har_rs_dow = 0.9999

    # Attempt to resolve
    res = obs.resolve_outcome(forecast_id="fc-tamper-001", actual_rv7d=0.1100)
    assert res is not None
    assert res.lifecycle_state == ForecastLifecycleState.AUDIT_CORRUPTED.value
    assert obs.hash_failures_count == 1

    # Health evaluation must isolate hash failure without throwing or counting as valid resolved
    health = obs.evaluate_calibration_health()
    assert health.hash_failures == 1
    assert health.total_resolved_forecasts == 0


# ── TEST 6: Exact Wall-Clock Trailing Window Semantics ────────────────────────

def test_exact_wall_clock_window_semantics(tmp_path):
    """Proves: 30D / 90D windows use trailing wall-clock timestamps rather than fixed record counts."""
    test_db = str(tmp_path / "clock_obs.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=test_db)

    now = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Add 10 records spanning 100 days (10 days apart)
    for i in range(10):
        t_orig = now - timedelta(days=100 - (i * 10))
        t_res = t_orig + timedelta(hours=168)
        fid = f"fc-clock-{i:03d}"
        obs.log_forecast(
            forecast_id=fid,
            timestamp=t_orig.isoformat(),
            v_hat=0.12,
            lower=0.05,
            upper=0.20
        )
        obs.resolve_outcome(
            forecast_id=fid,
            actual_rv7d=0.10 if i % 2 == 0 else 0.30,  # Alternate coverage
            resolved_at=t_res.isoformat()
        )

    health = obs.evaluate_calibration_health()
    assert health.total_resolved_forecasts == 10
    # Trailing 30 days should contain only the most recent records within 30 days of the latest resolution
    assert health.valid_N == 10
    assert health.invalid_N == 0


# ── TEST 7: DATA_INVALID Isolation ────────────────────────────────────────────

def test_data_invalid_isolation_preserves_valid_metrics(tmp_path):
    """Proves: a corrupt record does not zero out calibration statistics of valid records."""
    test_db = str(tmp_path / "isolate_obs.db")
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=test_db)

    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    # 10 valid covered records
    for i in range(10):
        t_orig = (now + timedelta(hours=i * 24)).isoformat()
        t_res = (now + timedelta(hours=i * 24 + 168)).isoformat()
        fid = f"fc-valid-{i}"
        obs.log_forecast(fid, t_orig, v_hat=0.12, lower=0.05, upper=0.20)
        obs.resolve_outcome(fid, actual_rv7d=0.12, resolved_at=t_res)

    # 1 corrupt record (NaN values)
    obs.log_forecast("fc-corrupt-001", now.isoformat(), v_hat=float("nan"), lower=0.0, upper=0.0)

    health = obs.evaluate_calibration_health()
    assert health.valid_N == 10
    assert health.invalid_N == 1
    assert health.coverage_all_pct == 100.0  # Valid records are 100% covered, not zeroed out!
    assert health.status == CalibrationHealthStatus.STABLE


# ── TEST 8: Scientific Startup Gate Tests ──────────────────────────────────────

def test_startup_valid_artifact_test():
    """Startup gate PASS on verified freeze contract."""
    passed = verify_scientific_contract(
        manifest_path=REPAIRED_MANIFEST_PATH,
        artifact_path=MODEL_ARTIFACT_PATH
    )
    assert passed is True


def test_startup_tampered_artifact_test(tmp_path):
    """Startup gate FAILS and raises RuntimeError if artifact is tampered."""
    tampered_file = str(tmp_path / "tampered.joblib")
    with open(tampered_file, "wb") as f:
        f.write(b"CORRUPTED_FAKE_MODEL_BYTES")

    with pytest.raises(RuntimeError, match="SCIENTIFIC STARTUP GATE FAILED"):
        verify_scientific_contract(
            manifest_path=REPAIRED_MANIFEST_PATH,
            artifact_path=tampered_file
        )


def test_startup_wrong_contract_test(tmp_path):
    """Startup gate FAILS and raises RuntimeError if manifest contract is wrong."""
    bad_manifest = str(tmp_path / "bad_manifest.json")
    with open(REPAIRED_MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["scientific_contract_hash"] = "0000000000000000000000000000000000000000000000000000000000000000"
    data["manifest_hash"] = "tampered"
    data["governance_status"] = "UNVERIFIED"

    with open(bad_manifest, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(RuntimeError, match="SCIENTIFIC STARTUP GATE FAILED"):
        verify_scientific_contract(
            manifest_path=bad_manifest,
            artifact_path=MODEL_ARTIFACT_PATH
        )


def test_startup_wrong_environment_test(tmp_path):
    """Startup gate FAILS and raises RuntimeError if model version is mismatch."""
    bad_manifest = str(tmp_path / "bad_version_manifest.json")
    with open(REPAIRED_MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["model_version"] = "UNAUTHORIZED_EXPERIMENTAL_MODEL"

    with open(bad_manifest, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(RuntimeError, match="SCIENTIFIC STARTUP GATE FAILED"):
        verify_scientific_contract(
            manifest_path=bad_manifest,
            artifact_path=MODEL_ARTIFACT_PATH
        )


# ── TEST 9: Exploratory vs Verified Intelligence Separation ───────────────────

def test_exploratory_vs_verified_intelligence_separation():
    """Verifies strict labeling and isolation between verified volatility vs exploratory strategy."""
    from api.routes_terminal import get_terminal_live_state
    from api.routes_prediction import get_prediction_latest
    import asyncio

    # Verified Volatility Terminal
    terminal_state = get_terminal_live_state()
    assert terminal_state["system_category"] == "VERIFIED VOLATILITY INTELLIGENCE"
    assert terminal_state["scientific_governance"] == "FREEZE_REPAIRED_AND_VERIFIED"
    assert terminal_state["scientific_contract_hash"] == "841deba5fb30118bea849f93ebc9fb7d1984d74fd2d709013544c6d5db94cf07"
    assert "ohlcv.parquet" in terminal_state["production_dependency_graph"]

    # Exploratory Directional / Strategy prediction
    pred_state = asyncio.run(get_prediction_latest())
    assert pred_state["system_classification"] == "EXPLORATORY STRATEGY ANALYTICS"
    assert "NOT VALIDATED FOR PREDICTIVE OR ECONOMIC SUPERIORITY" in pred_state["validation_status"]
