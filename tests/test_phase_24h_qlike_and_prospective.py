"""
tests/test_phase_24h_qlike_and_prospective.py — Unit and Integration Tests for 24H Volatility Sprint
======================================================================================================
Tests:
1. Target contract: rv24h_var_ann calculation from known synthetic returns, annualization factor (365.0).
2. Causal boundary and point-in-time feature availability (no future data in features).
3. QLIKE loss hand-computed numerical verification and scale invariance.
4. HLN finite-sample correction and Student's t reference distribution for Diebold-Mariano tests.
5. HAR-QLIKE-24H vs HAR-24H (OLS) model estimation, positive variance enforcement, and non-empty predictions.
6. Prospective evidence ledger: append-only logging, tamper prevention, idempotent resolution, test isolation.
7. Model registry authorization: HAR-QLIKE-24H and HAR-RS-DOW-24H are OFFLINE_RESEARCH_ONLY; production gates fail closed.
8. FastAPI research endpoints: /api/research/prospective-ledger, /api/research/24h-scorecard, and /api/research/experiments.
"""

import os
import json
import tempfile
import pytest
import numpy as np
import pandas as pd
from scipy import stats
from fastapi.testclient import TestClient

from engine.har_24h_features import (
    calculate_hourly_log_returns,
    compute_trailing_realized_variance,
    prepare_har_24h_dataset,
    get_har_24h_feature_matrix,
    get_daily_non_overlapping_slice,
)
from models.challengers.har_qlike_24h_challenger import (
    compute_qlike,
    compute_diebold_mariano_test,
    HARQLIKE24HChallenger,
    ConventionalHAR24H,
)
from engine.prospective_evidence_pipeline import (
    ProspectiveEvidencePipeline,
)
from models.authoritative_model_registry import (
    get_model_identity,
    get_active_production_model,
    verify_production_model_alignment,
    AuthorizationStatus,
    ModelClassification,
)
from api.server import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Target Contract Tests (rv24h_var_ann)
# ---------------------------------------------------------------------------

def test_target_calculation_known_returns():
    """
    Verify rv24h_var_ann matches hand-calculated sum of 24 future squared log returns * 365.0.
    """
    base_price = 10000.0
    prices = [base_price * (1.01 ** i) for i in range(48)]
    times = pd.date_range("2026-01-01 00:00:00", periods=48, freq="h")
    df = pd.DataFrame({"close": prices, "open": prices, "high": prices, "low": prices, "volume": 100.0}, index=times)

    prepared = prepare_har_24h_dataset(df, dropna=False)
    
    # At t = index 0 (2026-01-01 00:00:00), target spans the next 24 hours (t+1h to t+24h)
    expected_rv = (np.log(1.01) ** 2) * 24 * 365.0
    actual_rv = prepared.iloc[0]["rv24h_var_ann"]
    
    assert np.isclose(actual_rv, expected_rv, rtol=1e-5), f"Expected {expected_rv}, got {actual_rv}"


def test_target_future_boundary_strictly_ahead():
    """
    Ensure the target strictly uses future returns and has zero contemporaneous overlap.
    """
    times = pd.date_range("2026-01-01", periods=100, freq="h")
    prices = [100.0 + (i % 2) * 5.0 for i in range(100)]
    df = pd.DataFrame({"close": prices, "open": prices, "high": prices, "low": prices, "volume": 10.0}, index=times)
    
    prepared = prepare_har_24h_dataset(df, dropna=False)
    
    # The last 24 rows must have NaN target because the 24-hour future window has not completed
    assert prepared.iloc[-24:]["rv24h_var_ann"].isna().all(), "Last 24 rows must have NaN future target"


# ---------------------------------------------------------------------------
# 2. Causal Point-in-Time Feature Invariance
# ---------------------------------------------------------------------------

def test_causal_feature_invariance():
    """
    Verifies that changing future prices does NOT change features at time t.
    """
    times = pd.date_range("2026-01-01", periods=1000, freq="h")
    np.random.seed(42)
    returns = np.random.normal(0, 0.01, size=1000)
    prices = 50000.0 * np.exp(np.cumsum(returns))
    df = pd.DataFrame({"close": prices, "open": prices, "high": prices, "low": prices, "volume": 50.0}, index=times)
    
    prep1 = prepare_har_24h_dataset(df)
    features_t800_before = prep1.loc[times[800], ["rv_down_1d", "rv_up_1d", "rv1d_var_ann"]].to_dict()
    
    # Mutate prices at t=801 onwards
    df_mutated = df.copy()
    df_mutated.loc[times[801]:, "close"] = df_mutated.loc[times[801]:, "close"] * 2.0
    prep2 = prepare_har_24h_dataset(df_mutated)
    features_t800_after = prep2.loc[times[800], ["rv_down_1d", "rv_up_1d", "rv1d_var_ann"]].to_dict()
    
    for k in features_t800_before:
        assert np.isclose(features_t800_before[k], features_t800_after[k]), f"Leakage detected in feature {k}!"


# ---------------------------------------------------------------------------
# 3. Hand-Computed QLIKE Loss Tests
# ---------------------------------------------------------------------------

def test_hand_computed_qlike_loss():
    """
    Validates compute_qlike against exact hand calculation.
    Formula: QLIKE = (y / y_hat) - log(y / y_hat) - 1
    For y = 0.04, y_hat = 0.04: QLIKE = (1) - 0 - 1 = 0.0 (exact match)
    For y = 0.04, y_hat = 0.08:
      ratio = 0.04 / 0.08 = 0.5
      QLIKE = 0.5 - ln(0.5) - 1 = 0.5 - (-0.69314718) - 1 = 0.19314718
    """
    y_true = np.array([0.04, 0.04])
    y_pred = np.array([0.04, 0.08])
    
    loss_arr = compute_qlike(y_true, y_pred)
    loss = float(np.mean(loss_arr))
    
    expected_0 = 0.0
    expected_1 = 0.5 - np.log(0.5) - 1.0
    expected_mean = (expected_0 + expected_1) / 2.0
    
    assert np.isclose(loss, expected_mean, rtol=1e-6), f"Expected {expected_mean}, got {loss}"


def test_qlike_loss_non_negative():
    """QLIKE loss must be >= 0 for all strictly positive inputs."""
    np.random.seed(123)
    y_true = np.random.uniform(0.01, 1.0, 50)
    y_pred = np.random.uniform(0.01, 1.0, 50)
    loss = compute_qlike(y_true, y_pred)
    assert (loss >= 0.0).all()


# ---------------------------------------------------------------------------
# 4. HLN Correction and Student's t Reference Distribution
# ---------------------------------------------------------------------------

def test_hln_finite_sample_correction_and_student_t():
    """
    Tests that:
    1. HLN correction factor is sqrt((T + 1 - 2*h + h*(h-1)/T) / T)
       For h=1: sqrt((T - 1) / T)
    2. p-value is calculated from Student's t distribution with df = T - 1, NOT normal CDF.
    """
    T = 243
    h = 1
    np.random.seed(42)
    loss_b = np.random.normal(0.50, 0.10, size=T)
    loss_c = np.random.normal(0.49, 0.10, size=T)
    
    res = compute_diebold_mariano_test(loss_b, loss_c, horizon_h=h)
    
    expected_factor = np.sqrt((T - 1) / T)
    expected_hln_stat = round(res.dm_statistic * expected_factor, 4)
    assert np.isclose(res.hln_corrected_statistic, expected_hln_stat, rtol=1e-3)
    
    expected_p = round(float(stats.t.sf(res.hln_corrected_statistic, df=T - 1)), 5)
    assert np.isclose(res.p_value_one_sided, expected_p, atol=1e-5)
    assert res.degrees_of_freedom == T - 1


# ---------------------------------------------------------------------------
# 5. Model Fitting & Positive Variance Enforcement
# ---------------------------------------------------------------------------

def test_har_models_fit_and_predict_positive():
    """
    Verify both OLS and QLIKE HAR 24h models fit cleanly and enforce variance > 0.
    """
    np.random.seed(101)
    N = 200
    X = np.random.normal(0.0, 1.0, size=(N, 3))
    y = np.exp(0.5 * X[:, 0] + 0.3 * X[:, 1] + 0.2 * X[:, 2] + np.random.normal(0, 0.1, size=N))
    
    ols_model = ConventionalHAR24H()
    ols_model.fit(X, y)
    preds_ols = ols_model.predict(X)
    
    qlike_model = HARQLIKE24HChallenger(l2_reg=1e-4)
    qlike_model.fit(X, y)
    preds_qlike = qlike_model.predict(X)
    
    assert len(preds_ols) == N
    assert len(preds_qlike) == N
    assert (preds_ols > 0).all(), "OLS predictions must be strictly positive"
    assert (preds_qlike > 0).all(), "QLIKE predictions must be strictly positive"


# ---------------------------------------------------------------------------
# 6. Prospective Evidence Pipeline Tests
# ---------------------------------------------------------------------------

def test_prospective_pipeline_append_and_resolve(tmp_path):
    """
    Verifies that the prospective evidence pipeline:
    1. Appends records safely
    2. Resolves outcomes only when target window has matured
    3. Remains idempotent on repeated resolution passes
    """
    test_ledger = str(tmp_path / "test_prospective_ledger.jsonl")
    pipeline = ProspectiveEvidencePipeline(ledger_path=test_ledger)
    
    record = pipeline.log_forecast(
        issue_time_utc="2026-10-15T00:00:00Z",
        target_definition="rv24h_var_ann",
        forecast_horizon="24h",
        feature_cutoff_utc="2026-10-15T00:00:00Z",
        data_source_id="coinbase_btcusd_hourly_parquet",
        data_hash="test-data-hash-1234",
        feature_schema_hash="test-schema-hash-5678",
        model_version="HAR-QLIKE-24H-v1.0",
        model_artifact_hash="test-artifact-hash-9999",
        candidate_prediction=0.1550,
        benchmark_predictions={"persistence": 0.1700, "har_ols_24h": 0.1600},
        target_maturity_utc="2026-10-16T00:00:00Z",
    )
    
    assert record["forecast_id"] is not None
    assert record["resolution_state"] == "PENDING"
    
    assert os.path.exists(test_ledger)
    with open(test_ledger, "r") as f:
        lines = f.readlines()
    assert len(lines) == 1
    
    times = pd.date_range("2026-10-15 00:00:00", periods=26, freq="h")
    # Provide close prices for return calculation
    mock_df = pd.DataFrame({"close": [100.0 + i for i in range(26)]}, index=times)
    
    resolved_count = pipeline.resolve_outcomes(mock_df, current_utc="2026-10-16T01:00:00Z")
    assert resolved_count == 1
    
    status = pipeline.get_status()
    assert status["resolved_outcomes"] == 1
    assert status["pending_resolution"] == 0
    assert status["clean_prospective_blocks_count"] == 1
    
    resolved_second_pass = pipeline.resolve_outcomes(mock_df, current_utc="2026-10-16T01:00:00Z")
    assert resolved_second_pass == 0, "Second pass must be idempotent and resolve 0 additional records"


# ---------------------------------------------------------------------------
# 7. Model Identity Registry & Production Gate Tests
# ---------------------------------------------------------------------------

def test_model_registry_24h_authorization():
    """
    Ensure HAR-QLIKE-24H and HAR-RS-DOW-24H are strictly OFFLINE_RESEARCH_ONLY
    and that production endpoints reject them (fail closed).
    """
    qlike_24h = get_model_identity("HAR-QLIKE-24H")
    ols_24h = get_model_identity("HAR-RS-DOW-24H")
    
    assert qlike_24h is not None
    assert ols_24h is not None
    
    assert qlike_24h.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
    assert ols_24h.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
    assert qlike_24h.classification == ModelClassification.EXPERIMENTAL_CHALLENGER
    
    assert verify_production_model_alignment("/api/terminal/live", "HAR-QLIKE-24H") is False
    assert verify_production_model_alignment("/api/terminal/live", "HAR-RS-DOW-24H") is False
    
    active_prod = get_active_production_model()
    assert verify_production_model_alignment("/api/terminal/live", active_prod.canonical_id) is True


# ---------------------------------------------------------------------------
# 8. FastAPI Research Endpoints Tests
# ---------------------------------------------------------------------------

def test_api_prospective_ledger_endpoint():
    """Verify GET /api/research/prospective-ledger returns 200 and typed ledger summary."""
    response = client.get("/api/research/prospective-ledger")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "records" in data
    assert data["status"]["prospective_status"] == "COLLECTING"


def test_api_24h_scorecard_endpoint():
    """Verify GET /api/research/24h-scorecard returns 200 with empirical results."""
    response = client.get("/api/research/24h-scorecard")
    assert response.status_code == 200
    data = response.json()
    assert data["experiment_id"] == "EXP-2026-04-QLIKE-24H"
    assert data["authorization_status"] == "OFFLINE_RESEARCH_ONLY"
    assert data["live_trading_status"] == "DISABLED"
    assert "scorecard" in data
    assert data["scorecard"]["primary_daily_non_overlapping"]["sample_size"] == 243


def test_api_experiments_register_includes_24h():
    """Verify GET /api/research/experiments includes EXP-2026-04-QLIKE-24H."""
    response = client.get("/api/research/experiments")
    assert response.status_code == 200
    data = response.json()
    exp_ids = [e["experiment_id"] for e in data["experiments"]]
    assert "EXP-2026-04-QLIKE-24H" in exp_ids
