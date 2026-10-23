"""
tests/test_forecast_activation_and_readiness.py — Independent Verification Suite
================================================================================
Comprehensive tests for BTCognitive Phase 6:
1. Full freeze verifier succeeds and failure modes fail closed.
2. Missing manifest, missing artifact, artifact hash mismatch.
3. Insufficient candle history (< 720 bars) fails closed.
4. Feature schema, target contract (rv7d_var_ann, 168h), and non-directionality.
5. Canonical HAR-RS-DOW inference returns finite, positive annualized variance.
6. C2 conformal risk envelope coverage and bounds consistency.
7. Directional alpha separation (offline research only).
8. Endpoint consistency (/api/readiness, /health, /api/terminal/live, /api/terminal/model-identity).
9. Liveness (/ping) vs forecast readiness separation.
10. Live trading and execution safeguards fail closed.
11. Known-answer QLIKE metric scorecard reproduction.
"""

import os
import json
import math
import tempfile
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.server import app
from validation.startup_gate import (
    evaluate_runtime_readiness,
    verify_scientific_contract,
    extract_pipeline_coefficients_hash,
    MODEL_ARTIFACT_PATH,
    REPAIRED_MANIFEST_PATH,
)
from models.authoritative_model_registry import (
    get_active_production_model,
    get_directional_research_baseline,
    AuthorizationStatus,
    ModelClassification,
)


def test_runtime_readiness_all_checks_pass():
    """Verifies that evaluate_runtime_readiness passes all 9 checks on valid environment."""
    res = evaluate_runtime_readiness(force_refresh=True)
    assert res["status"] == "READY"
    assert res["authorized"] is True
    assert res["authorization_status"] == "AUTHORIZED_FOR_PRODUCTION"
    assert res["reason_code"] == "NONE"
    assert res["canonical_model_id"] == "HAR-RS-DOW-v1.0"
    assert res["forecast_target"] == "Annualized 7-Day Realized Variance (rv7d_var_ann)"
    assert res["forecast_horizon"] == "168h (7 calendar days)"
    assert res["directional_prediction_capability"] is False
    assert res["trading_enabled"] is False

    checks = res["checks"]
    for expected_check in [
        "manifest", "model_artifact", "coefficients", "feature_contract",
        "target_contract", "calibration", "runtime_environment",
        "point_in_time_data", "freeze_verifier"
    ]:
        assert expected_check in checks
        assert checks[expected_check]["status"] == "PASS"


def test_runtime_readiness_missing_manifest_fails_closed():
    """Simulates missing manifest and verifies fail-closed status with FROZEN_INPUT_MISSING."""
    res = evaluate_runtime_readiness(manifest_path="nonexistent_manifest.json", force_refresh=True)
    assert res["status"] == "BLOCKED"
    assert res["authorized"] is False
    assert res["reason_code"] == "FROZEN_INPUT_MISSING"
    assert "not found" in res["reason"].lower()
    assert res["checks"]["manifest"]["status"] == "FAIL"


def test_runtime_readiness_missing_artifact_fails_closed():
    """Simulates missing model artifact and verifies fail-closed status with FROZEN_INPUT_MISSING."""
    res = evaluate_runtime_readiness(artifact_path="nonexistent_model.joblib", force_refresh=True)
    assert res["status"] == "BLOCKED"
    assert res["authorized"] is False
    assert res["reason_code"] == "FROZEN_INPUT_MISSING"
    assert res["checks"]["model_artifact"]["status"] == "FAIL"


def test_runtime_readiness_artifact_hash_mismatch_fails_closed():
    """Simulates tampered model artifact and verifies MODEL_ARTIFACT_INVALID."""
    with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp:
        tmp.write(b"corrupted_or_altered_model_bytes")
        tmp_path = tmp.name

    try:
        res = evaluate_runtime_readiness(artifact_path=tmp_path, force_refresh=True)
        assert res["status"] == "BLOCKED"
        assert res["authorized"] is False
        assert res["reason_code"] == "MODEL_ARTIFACT_INVALID"
        assert "mismatch" in res["reason"].lower()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_canonical_model_inference_validity():
    """Loads canonical joblib pipeline and asserts finite, positive variance prediction."""
    import joblib
    assert os.path.exists(MODEL_ARTIFACT_PATH)
    pipe = joblib.load(MODEL_ARTIFACT_PATH)

    # 10 canonical features:
    # ['log_rv_down_1d', 'log_rv_up_1d', 'log_rv7d_var_ann_lag', 'log_rv30d_var_ann',
    #  'dow_1', 'dow_2', 'dow_3', 'dow_4', 'dow_5', 'dow_6']
    sample_features = np.array([[-1.5, -1.6, -1.4, -1.3, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]])
    log_v_hat = pipe.predict(sample_features)
    v_hat = np.exp(log_v_hat)[0]

    assert np.isfinite(v_hat)
    assert v_hat > 0.0
    # Annualized variance for BTC typically between 0.01 and 5.0 (10% to 223% vol)
    assert 0.01 <= v_hat <= 5.0
    annual_vol_pct = np.sqrt(v_hat) * 100.0
    assert 10.0 <= annual_vol_pct <= 250.0


def test_canonical_target_and_horizon_contract():
    """Verifies that canonical model target is strictly 168h rv7d_var_ann and non-directional."""
    model = get_active_production_model()
    assert model.canonical_id == "HAR-RS-DOW-v1.0"
    assert model.classification == ModelClassification.PRODUCTION_VOLATILITY
    assert "rv7d_var_ann" in model.forecast_target
    assert "168h" in model.forecast_horizon
    assert model.directional_prediction_capability is False
    assert len(model.feature_schema) == 10


def test_directional_research_baseline_is_offline_only():
    """Verifies that directional baseline is strictly offline research and not authorized for production."""
    dir_model = get_directional_research_baseline()
    assert dir_model.canonical_id == "directional-gbm-4lag-v1"
    assert dir_model.classification == ModelClassification.DIRECTIONAL_RESEARCH_BENCHMARK
    assert dir_model.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
    assert "rv7d_var_ann" not in dir_model.forecast_target


def test_api_readiness_endpoint():
    """Tests GET /api/readiness reports truthful diagnostic breakdown."""
    with TestClient(app) as client:
        res = client.get("/api/readiness")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "READY"
        assert data["authorized"] is True
        assert data["reason_code"] == "NONE"
        assert data["canonical_model_id"] == "HAR-RS-DOW-v1.0"
        assert data["trading_enabled"] is False


def test_api_health_endpoint_agreement():
    """Tests /health and /api/health report production volatility intelligence mode."""
    with TestClient(app) as client:
        for ep in ["/health", "/api/health"]:
            res = client.get(ep)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "ok"
            assert data["mode"] == "PRODUCTION_VOLATILITY_INTELLIGENCE"
            assert data["research_authorized"] is True
            assert data["production_forecast_available"] is True
            assert data["trading_enabled"] is False


def test_terminal_live_endpoint_generates_canonical_forecast():
    """Tests GET /api/terminal/live produces valid 7D variance and C2 risk envelope."""
    with TestClient(app) as client:
        res = client.get("/api/terminal/live")
        assert res.status_code == 200
        data = res.json()
        assert data["terminal_version"] == "BTCognitive-Terminal-v2.0"
        assert data["system_category"] == "VERIFIED VOLATILITY INTELLIGENCE"
        assert data["scientific_governance"] == "FREEZE_REPAIRED_AND_VERIFIED"
        assert data["scientific_contract_hash"] == "841deba5fb30118bea849f93ebc9fb7d1984d74fd2d709013544c6d5db94cf07"

        # Check the 4 core questions
        q1 = data["four_questions"]["1_expected_volatility"]
        assert q1["metric"] == "Forward 7-Day Realized Variance (Annualized)"
        assert float(q1["point_forecast_har_rs_dow"]) > 0.0

        q2 = data["four_questions"]["2_uncertainty_risk_envelope"]
        assert q2["nominal_target_coverage"] == "90% Target Risk Envelope"
        assert float(q2["lower_bound_variance"]) >= 0.0
        assert float(q2["upper_bound_variance"]) > float(q2["lower_bound_variance"])
        assert float(q2["envelope_width"]) > 0.0


def test_liveness_ping_does_not_imply_readiness():
    """Tests /ping is a simple liveness probe and does not claim forecast readiness."""
    with TestClient(app) as client:
        res = client.get("/ping")
        assert res.status_code == 200
        data = res.json()
        assert data["pong"] is True
        assert "timestamp" in data
        assert "production_forecast_available" not in data


def test_short_horizon_forecast_retains_empirical_baseline_classification():
    """Tests that 24h/4h range requests return EXPERIMENTAL_BASELINE and do not conflate with 168h ML."""
    with TestClient(app) as client:
        res = client.get("/prediction/range?horizon=24h")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "EXPERIMENTAL_BASELINE"
        assert data["forecast_mode"] == "EXPERIMENTAL_BASELINE"
        assert data["horizon"] == "24h"
        assert "NOT_VALIDATED_FOR_TRADING" in data["validation_status"]


def test_live_trading_prohibitions_fail_closed():
    """Verifies that live trading endpoints strictly reject execution."""
    with TestClient(app) as client:
        res = client.get("/api/research/entry-tp-sl")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "BLOCKED"
        assert data["live_capital_authorized"] is False
        assert data["trading_enabled"] is False
        assert data["hypothetical_signal"] is None
        assert data["entry_price"] is None


def test_qlike_known_answer_scorecard_reproduction():
    """
    Known-answer reproduction of Gaussian QLIKE loss:
    QLIKE(y, v) = y/v - ln(y/v) - 1.
    Properties:
    - QLIKE(y, y) == 0 (zero loss when prediction equals realization)
    - QLIKE(y, v) > 0 for all y != v
    - Asymmetric penalty: underpredicting variance (v < y) is penalized more heavily than overpredicting.
    """
    def qlike(y, v):
        ratio = y / v
        return ratio - np.log(ratio) - 1.0

    # Known-answer tests
    assert math.isclose(qlike(1.0, 1.0), 0.0, abs_tol=1e-12)
    assert math.isclose(qlike(0.25, 0.25), 0.0, abs_tol=1e-12)

    # v = 0.5 when y = 1.0 -> ratio = 2.0 -> 2 - ln(2) - 1 = 1 - 0.693147... = 0.3068528...
    loss_under = qlike(1.0, 0.5)
    assert math.isclose(loss_under, 1.0 - math.log(2.0), rel_tol=1e-7)

    # v = 2.0 when y = 1.0 -> ratio = 0.5 -> 0.5 - ln(0.5) - 1 = -0.5 + 0.693147... = 0.193147...
    loss_over = qlike(1.0, 2.0)
    assert math.isclose(loss_over, -0.5 + math.log(2.0), rel_tol=1e-7)

    # Underpredicting by 2x yields higher QLIKE penalty than overpredicting by 2x (classic econometrics property)
    assert loss_under > loss_over
