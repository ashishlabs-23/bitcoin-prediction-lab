"""
tests/test_stage5_dependency_and_model_identity.py — Stage 5 Acceptance Suite
=============================================================================
Verifies all 6 Section 3 acceptance criteria for runtime vs research dependency contracts,
as well as Section 2 single source of truth for model identity.

Acceptance Test Cases:
1. Case 1: All required runtime inputs and artifacts are present -> PASS.
2. Case 2: A research-only benchmark is absent but runtime dependencies remain valid -> PASS.
3. Case 3: A required runtime input is missing (ohlcv.parquet) -> FAIL-CLOSED.
4. Case 4: A required model artifact is missing or corrupted -> FAIL-CLOSED.
5. Case 5: A freeze manifest or contract checksum is invalid -> FAIL-CLOSED.
6. Case 6: A research-only endpoint requested while dataset unavailable -> 404/503 (no fabrication).
7. Case 7: Model identity registry provides single source of truth matching live terminal.
8. Case 8: Legacy excursion endpoints fail closed with explicit archived model metadata.
9. Case 9: Directional research endpoints are isolated as offline research only.
"""

import os
import sys
import json
import tempfile
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from validation.dependency_schema import (
    validate_full_runtime_contract,
    validate_runtime_dependencies,
    validate_research_benchmarks,
    classify_dependency,
    is_runtime_dependency,
    is_research_benchmark,
    RUNTIME_MODEL_ARTIFACT_REL_PATH,
    RUNTIME_FREEZE_MANIFEST_REL_PATH,
    EXPECTED_ARTIFACT_SHA256,
    EXPECTED_CONTRACT_HASH,
)
from models.authoritative_model_registry import (
    get_active_production_model,
    get_directional_research_baseline,
    get_model_identity,
    list_authoritative_models,
    verify_production_model_alignment,
    ModelClassification,
    AuthorizationStatus,
)
from api.server import app

client = TestClient(app)


# ── CASE 1: All required runtime inputs and artifacts are present ─────────

def test_case_1_all_runtime_inputs_and_artifacts_present():
    """Case 1: Baseline verification when all runtime dependencies exist."""
    res = validate_full_runtime_contract(REPO_ROOT)
    assert res["status"] == "PASS"
    assert res["valid"] is True
    assert res["model_version"] == "HAR-RS-DOW-v1.0"
    assert res["artifact_hash"] == EXPECTED_ARTIFACT_SHA256
    assert res["contract_hash"] == EXPECTED_CONTRACT_HASH


# ── CASE 2: Research-only benchmark is absent, runtime remains valid ──────

def test_case_2_research_benchmark_absent_runtime_remains_valid():
    """
    Case 2: If a research-only benchmark (e.g. iv7d.parquet) is absent,
    the active inference path is NOT blocked.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_dir = os.path.join(tmp_dir, "data", "raw")
        os.makedirs(raw_dir, exist_ok=True)
        # Copy only the runtime dependency ohlcv.parquet
        real_ohlcv = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
        with open(real_ohlcv, "rb") as src, open(os.path.join(raw_dir, "ohlcv.parquet"), "wb") as dst:
            dst.write(src.read())

        # Copy model artifact and manifest
        freeze_dir = os.path.join(tmp_dir, "experiments", "results", "freeze")
        os.makedirs(freeze_dir, exist_ok=True)
        real_joblib = os.path.join(REPO_ROOT, RUNTIME_MODEL_ARTIFACT_REL_PATH)
        real_manifest = os.path.join(REPO_ROOT, RUNTIME_FREEZE_MANIFEST_REL_PATH)
        with open(real_joblib, "rb") as src, open(os.path.join(freeze_dir, "har_rs_dow_v1.joblib"), "wb") as dst:
            dst.write(src.read())
        with open(real_manifest, "rb") as src, open(os.path.join(freeze_dir, "repaired_scientific_contract_manifest.json"), "wb") as dst:
            dst.write(src.read())

        # Assert research benchmark iv7d.parquet is absent
        assert not os.path.exists(os.path.join(raw_dir, "iv7d.parquet"))
        all_bench_present, missing_benchmarks = validate_research_benchmarks(raw_dir)
        assert not all_bench_present
        assert "iv7d.parquet" in missing_benchmarks

        # Assert runtime contract STILL PASSES completely
        contract_res = validate_full_runtime_contract(tmp_dir)
        assert contract_res["status"] == "PASS"
        assert contract_res["valid"] is True


# ── CASE 3: Required runtime input is missing -> FAIL-CLOSED ──────────────

def test_case_3_required_runtime_input_missing_fails_closed():
    """Case 3: Missing ohlcv.parquet must trigger fail-closed state."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_dir = os.path.join(tmp_dir, "data", "raw")
        os.makedirs(raw_dir, exist_ok=True)
        # ohlcv.parquet is NOT created
        contract_res = validate_full_runtime_contract(tmp_dir)
        assert contract_res["status"] == "FAIL_DATA_MISSING"
        assert contract_res["valid"] is False
        assert "ohlcv.parquet" in contract_res["missing_dependencies"]


# ── CASE 4: Required model artifact is missing or corrupted -> FAIL-CLOSED

def test_case_4_required_model_artifact_missing_or_corrupted():
    """Case 4: Missing or corrupted har_rs_dow_v1.joblib fails closed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_dir = os.path.join(tmp_dir, "data", "raw")
        os.makedirs(raw_dir, exist_ok=True)
        real_ohlcv = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
        with open(real_ohlcv, "rb") as src, open(os.path.join(raw_dir, "ohlcv.parquet"), "wb") as dst:
            dst.write(src.read())

        freeze_dir = os.path.join(tmp_dir, "experiments", "results", "freeze")
        os.makedirs(freeze_dir, exist_ok=True)
        real_manifest = os.path.join(REPO_ROOT, RUNTIME_FREEZE_MANIFEST_REL_PATH)
        with open(real_manifest, "rb") as src, open(os.path.join(freeze_dir, "repaired_scientific_contract_manifest.json"), "wb") as dst:
            dst.write(src.read())

        # 4A: Artifact missing
        res_missing = validate_full_runtime_contract(tmp_dir)
        assert res_missing["status"] == "FAIL_ARTIFACT_MISSING"
        assert res_missing["valid"] is False

        # 4B: Artifact corrupted (tampered bytes)
        corrupted_path = os.path.join(freeze_dir, "har_rs_dow_v1.joblib")
        with open(corrupted_path, "wb") as f:
            f.write(b"CORRUPTED_BYTES_INJECTED_FOR_TESTING")
        res_corrupted = validate_full_runtime_contract(tmp_dir)
        assert res_corrupted["status"] == "FAIL_ARTIFACT_CORRUPTED"
        assert res_corrupted["valid"] is False


# ── CASE 5: Freeze manifest or checksum invalid -> FAIL-CLOSED ───────────

def test_case_5_freeze_manifest_or_checksum_invalid():
    """Case 5: Manifest missing or tampered contract hash fails closed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_dir = os.path.join(tmp_dir, "data", "raw")
        os.makedirs(raw_dir, exist_ok=True)
        real_ohlcv = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
        with open(real_ohlcv, "rb") as src, open(os.path.join(raw_dir, "ohlcv.parquet"), "wb") as dst:
            dst.write(src.read())

        freeze_dir = os.path.join(tmp_dir, "experiments", "results", "freeze")
        os.makedirs(freeze_dir, exist_ok=True)
        real_joblib = os.path.join(REPO_ROOT, RUNTIME_MODEL_ARTIFACT_REL_PATH)
        with open(real_joblib, "rb") as src, open(os.path.join(freeze_dir, "har_rs_dow_v1.joblib"), "wb") as dst:
            dst.write(src.read())

        # 5A: Manifest missing
        res_missing = validate_full_runtime_contract(tmp_dir)
        assert res_missing["status"] == "FAIL_MANIFEST_MISSING"

        # 5B: Manifest contract hash tampered
        tampered_manifest = {
            "model_version": "HAR-RS-DOW-v1.0",
            "scientific_contract_hash": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
        }
        with open(os.path.join(freeze_dir, "repaired_scientific_contract_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(tampered_manifest, f)
        res_tampered = validate_full_runtime_contract(tmp_dir)
        assert res_tampered["status"] == "FAIL_MANIFEST_INVALID"
        assert res_tampered["valid"] is False


# ── CASE 6: Research-only endpoint when dataset unavailable -> 404/503 ────

def test_case_6_research_endpoint_missing_data_fails_without_fabrication():
    """Case 6: A non-existent research report must return 404, not fabricated data."""
    resp = client.get("/api/research/reports/nonexistent-fabricated-experiment")
    assert resp.status_code == 404


# ── CASE 7: Model Identity Registry single source of truth ────────────────

def test_case_7_model_identity_single_source_of_truth():
    """Case 7: Registry and live terminal agree on model identity."""
    prod = get_active_production_model()
    assert prod.canonical_id == "HAR-RS-DOW-v1.0"
    assert prod.classification == ModelClassification.PRODUCTION_VOLATILITY
    assert prod.authorization_status in (
        AuthorizationStatus.AUTHORIZED_FOR_PRODUCTION,
        AuthorizationStatus.BLOCKED_AUDIT_FAILURE,
    )
    assert prod.directional_prediction_capability is False

    # Check terminal endpoint returns matching identity
    resp = client.get("/api/terminal/model-identity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["canonical_id"] == "HAR-RS-DOW-v1.0"
    assert data["classification"] == "PRODUCTION_VOLATILITY"
    assert data["forecast_target"] == "Annualized 7-Day Realized Variance (rv7d_var_ann)"
    assert data["forecast_horizon"] == "168h (7 calendar days)"
    assert data["directional_prediction_capability"] is False

    # Check authoritative catalog endpoint
    cat_resp = client.get("/api/models/authoritative-registry")
    assert cat_resp.status_code == 200
    cat_data = cat_resp.json()
    assert cat_data["active_production_model"] == "HAR-RS-DOW-v1.0"
    assert len(cat_data["models"]) >= 3


# ── CASE 8: Legacy excursion endpoints fail closed with explicit metadata ─

def test_case_8_legacy_excursion_fails_closed_with_archived_metadata():
    """Case 8: Legacy /prediction/range endpoints fail closed or withhold unverified models."""
    # 8A: Prediction range health fails closed with BLOCKED_PROVENANCE_UNVERIFIED
    health_resp = client.get("/prediction/range/health")
    assert health_resp.status_code == 200
    h_data = health_resp.json()
    assert h_data["status"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert h_data["production_model_status"] == "BLOCKED"
    assert h_data["production_forecast_available"] is False
    assert h_data["trading_enabled"] is False

    # 8B: /prediction/range empirical baseline explicitly blocks live capital and marks unverified
    resp = client.get("/prediction/range")
    assert resp.status_code == 200
    data = resp.json()
    assert data["research_authorization"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert data["live_capital_authorized"] is False
    assert data["validation_status"] == "NOT_VALIDATED_FOR_TRADING"
    assert data["forecast_mode"] == "EXPERIMENTAL_BASELINE"


# ── CASE 9: Directional research endpoints isolated as offline research ───

def test_case_9_directional_research_isolated_as_offline_research():
    """Case 9: Directional audit endpoint clearly identifies as offline research only."""
    baseline = get_directional_research_baseline()
    assert baseline.canonical_id == "directional-gbm-4lag-v1"
    assert baseline.classification == ModelClassification.DIRECTIONAL_RESEARCH_BENCHMARK
    assert baseline.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY

    resp = client.get("/api/research/directional-audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["research_category"] == "OFFLINE_DIRECTIONAL_RESEARCH_BENCHMARK"
    assert data["production_inference_status"] == "SEPARATE_OFFLINE_RESEARCH_NOT_AUTHORIZED_FOR_PRODUCTION"
    assert "70% directional accuracy is unsupported" in data["epistemic_disclaimer"]
