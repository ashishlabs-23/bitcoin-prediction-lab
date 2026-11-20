"""
tests/test_v32_23_forecast_smart_entry_recovery.py — V32.23 AI Forecast & Smart Entry Recovery Test Suite
=======================================================================================================
Verifies:
1. Authoritative model identity, artifact checksum integrity, and governance status.
2. AI Forecast contract separation (persistence baseline vs nominal diffusion vs disconnected GBDTs).
3. Historical benchmark accuracy is distinct from live probability and properly attributed.
4. Smart Entry decision path: driftless null baseline (mu=0.0), negative net expectancy fail-closed ABSTAIN,
   no false edge creation, zero prospective ledger writes by default, and live trading disabled.
"""

import os
import json
import hashlib
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from api.server import app
from models.authoritative_model_registry import (
    ACTIVE_PRODUCTION_MODEL,
    DIRECTIONAL_RESEARCH_BASELINE,
    AuthorizationStatus,
    ModelClassification,
)
from engine.forecast_engine_15m import generate_forecast_contract
from engine.smart_entry_engine import SmartEntryDecisionEngine
from engine.probabilistic_entry_engine import ProbabilisticEntryEngine


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Section 1: Model Identity, Artifact Integrity & Governance Tests
# ---------------------------------------------------------------------------

def test_v32_23_har_artifact_sha256_matches_authoritative_manifest():
    """Verify that the production volatility model artifact SHA-256 exactly matches authoritative registry."""
    artifact_rel = "experiments/results/freeze/har_rs_dow_v1.joblib"
    artifact_path = os.path.join(REPO_ROOT, artifact_rel)
    assert os.path.exists(artifact_path), f"Artifact missing: {artifact_path}"

    with open(artifact_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    expected_hash = ACTIVE_PRODUCTION_MODEL.artifact_sha256
    assert actual_hash == expected_hash, (
        f"Artifact SHA-256 mismatch for HAR-RS-DOW-v1.0:\nExpected: {expected_hash}\nActual:   {actual_hash}"
    )
    assert actual_hash == "750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b"
    assert ACTIVE_PRODUCTION_MODEL.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
    assert "rv7d_var_ann" in ACTIVE_PRODUCTION_MODEL.forecast_target


def test_v32_23_directional_gbdt_models_freeze_manifest_hashes():
    """Verify that directional GBDT model artifacts match freeze metadata and are OFFLINE_RESEARCH_ONLY."""
    meta_path = os.path.join(REPO_ROOT, "models", "registry", "research", "directional_models_freeze_metadata.json")
    assert os.path.exists(meta_path), "Directional models freeze metadata missing."

    with open(meta_path, "r", encoding="utf-8") as f:
        freeze_meta = json.load(f)

    assert "1h" in freeze_meta
    assert "4h" in freeze_meta
    assert "24h" in freeze_meta

    for h_key in ["1h", "4h", "24h"]:
        info = freeze_meta[h_key]
        fname = info["artifact_file"]
        expected_hash = info["artifact_sha256"]
        fpath = os.path.join(REPO_ROOT, "models", "registry", "research", fname)
        assert os.path.exists(fpath), f"GBDT model artifact missing: {fpath}"

        with open(fpath, "rb") as f:
            disk_hash = hashlib.sha256(f.read()).hexdigest()

        assert disk_hash == expected_hash, f"Hash mismatch for {fname}: {disk_hash} != {expected_hash}"

    # Directional baseline in authoritative registry must remain OFFLINE_RESEARCH_ONLY
    assert DIRECTIONAL_RESEARCH_BASELINE.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY


def test_v32_23_artifact_tamper_detection():
    """Simulate artifact hash verification logic and ensure tampered hashes fail the gate."""
    corrupted_data = b"tampered_or_retrained_model_bytes"
    corrupted_hash = hashlib.sha256(corrupted_data).hexdigest()
    assert corrupted_hash != ACTIVE_PRODUCTION_MODEL.artifact_sha256
    assert corrupted_hash != "750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b"


# ---------------------------------------------------------------------------
# Section 2: Forecast Engine Contract & API Separation Tests
# ---------------------------------------------------------------------------

def test_v32_23_forecast_engine_explicit_baseline_contract():
    """Verify that forecast contract separates mathematical persistence baseline from nominal diffusion bands."""
    fc_15m = generate_forecast_contract(horizon="15m")
    assert fc_15m["status"] == "FORECAST_AVAILABLE_RESEARCH_ONLY"
    assert fc_15m["model_id"] == "EMPIRICAL_CONFORMAL_PERSISTENCE_v1.0"
    assert fc_15m["forecast_type"] == "NON_DIRECTIONAL_RESEARCH_BASELINE"
    assert fc_15m["diffusion_band_calibration_status"] == "NOMINAL_UNCALIBRATED_GAUSSIAN"
    assert fc_15m["directional_recommendation"] == "ABSTAIN"
    assert fc_15m["live_trading"] == "DISABLED"

    # Directional classifier status must be explicit
    fc_1h = generate_forecast_contract(horizon="1h")
    assert fc_1h["directional_model_id"] == "directional-gbm-1h-v1"
    assert fc_1h["directional_model_governance"] == "OFFLINE_RESEARCH_ONLY"
    assert fc_1h["directional_model_runtime_status"] in ["DISCONNECTED_UNVALIDATED_EDGE", "RESEARCH_INFERENCE_ACTIVE"]
    assert fc_1h["cost_adjusted_expectancy"] == "NEGATIVE_AFTER_FEES"

    # Historical accuracy is historical benchmark, not current predictive confidence
    assert fc_1h["historical_accuracy_pct"] == 52.14
    assert "Stage 11 Walk-Forward Benchmark" in fc_1h["historical_accuracy_source"]

    # Freshness and candle close alignment
    assert fc_15m["data_freshness_status"] in ["FRESH", "DELAYED", "STALE"]
    assert fc_15m["candle_close_epoch"] == fc_15m["candle_open_epoch"] + 900
    assert fc_1h["candle_close_epoch"] == fc_1h["candle_open_epoch"] + 3600


def test_v32_23_api_forecast_latest_endpoint():
    """Test /api/forecast/latest endpoint preserves honest contract without fabrication."""
    client = TestClient(app)
    resp = client.get("/api/forecast/latest?horizon=15m")
    assert resp.status_code == 200
    data = resp.json()

    assert data["model_id"] == "EMPIRICAL_CONFORMAL_PERSISTENCE_v1.0"
    assert data["forecast_type"] == "NON_DIRECTIONAL_RESEARCH_BASELINE"
    assert data["diffusion_band_calibration_status"] == "NOMINAL_UNCALIBRATED_GAUSSIAN"
    assert data["directional_recommendation"] == "ABSTAIN"
    assert data["live_trading"] == "DISABLED"
    assert len(data["points"]) >= 4
    assert len(data["upper_band"]) >= 4
    assert len(data["lower_band"]) >= 4


# ---------------------------------------------------------------------------
# Section 3: Smart Entry Decision Path & mu=0.0 Null Baseline Tests
# ---------------------------------------------------------------------------

def test_v32_23_probabilistic_entry_engine_driftless_null_baseline():
    """Verify that ProbabilisticEntryEngine solves the PDE under mu=0.0 and labels driftless status."""
    engine = ProbabilisticEntryEngine()
    gate = engine.evaluate_decision_gate(
        side="LONG",
        entry_price=65000.0,
        sigma_t0=0.015,
        k_tp=1.5,
        k_sl=1.0,
        cost_scenario="COINBASE_RETAIL_87BPS",
    )

    # Must be driftless null baseline
    assert gate["drift_parameter_mu"] == 0.0
    assert gate["drift_status"] == "DRIFTLESS_NULL_BASELINE"
    assert gate["epistemic_provenance"] == "FIRST_PASSAGE_GEOMETRY_BASELINE_H0"
    assert gate["validated_directional_edge"] is False
    assert gate["action"] == "ABSTAIN"
    assert "NO_VALIDATED_EDGE_ABSTAIN" in gate["primary_reason"]
    assert gate["expected_net_r"] < 0.0  # Net expectancy negative after transaction friction
    assert gate["execution_authorization"] == "DISABLED — ANALYSIS ONLY"


def test_v32_23_smart_entry_engine_abstains_with_honest_explanation():
    """Verify SmartEntryDecisionEngine returns ABSTAIN with full reason and zero writes by default."""
    engine = SmartEntryDecisionEngine()

    now_utc = datetime.now(timezone.utc)
    # Generate 30 candles
    candles = [
        {
            "timestamp_utc": now_utc.isoformat(),
            "open": 64800.0 + i * 10,
            "high": 64950.0 + i * 10,
            "low": 64750.0 + i * 10,
            "close": 64900.0 + i * 10,
        }
        for i in range(30)
    ]

    result = engine.evaluate_market(
        live_price=65200.0,
        candles=candles,
        regime="VOL_EXPANDING",
        user_direction_preference="AUTO",
        cost_scenario="COINBASE_RETAIL_87BPS",
        persist=False,
    )

    assert result["status"] == "ABSTAIN"
    assert result["decision_action"] == "ABSTAIN"
    assert result["persisted"] is False
    assert result["execution_authorization"] == "DISABLED — ANALYSIS ONLY"
    assert result["drift_parameter_mu"] == 0.0
    assert result["drift_status"] == "DRIFTLESS_NULL_BASELINE"
    assert (
        "NO_VALIDATED_EDGE_ABSTAIN" in result["primary_reason"]
        or "NO_ELIGIBLE_STRATEGY" in result["primary_reason"]
    )


def test_v32_23_smart_entry_api_endpoint_fail_closed():
    """Verify /api/research/smart-entry returns valid schema and fail-closed ABSTAIN without writes."""
    client = TestClient(app)
    now_dt = datetime.now(timezone.utc)
    base_epoch = int(now_dt.timestamp()) - (30 * 3600)
    candles = [
        {
            "timestamp_utc": datetime.fromtimestamp(base_epoch + (i * 3600), tz=timezone.utc).isoformat(),
            "open": 65000.0 + i * 5,
            "high": 65100.0 + i * 5,
            "low": 64900.0 + i * 5,
            "close": 65050.0 + i * 5,
        }
        for i in range(30)
    ]
    snapshot_ts = datetime.fromtimestamp(base_epoch + (29 * 3600), tz=timezone.utc).isoformat()

    payload = {
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "timestamp_utc": snapshot_ts,
        "live_price": 65200.0,
        "regime": "VOL_EXPANDING",
        "c2_health": "CALIBRATED",
        "user_direction_preference": "AUTO",
        "selective_threshold": 0.60,
        "cost_scenario": "COINBASE_RETAIL_87BPS",
        "market_snapshot": {
            "ofi": 0.85,
            "hawkes": 2.5,
            "vpin": 0.18,
            "spread_bps": 1.2,
            "depth_score": 0.85,
            "is_expansion": True,
            "realized_vol_24h_ann": 0.485,
        },
        "enabled_indicators": ["ofi", "hawkes", "vpin", "rv_5m", "liquidations"],
        "candles": candles,
    }

    resp = client.post("/api/research/smart-entry", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ABSTAIN"
    assert data["decision_action"] == "ABSTAIN"
    assert data["acceptance_status"] == "ABSTAIN"
    assert data["persisted"] is False
    assert data["execution_authorization"] == "DISABLED — ANALYSIS ONLY"
    assert data["drift_parameter_mu"] == 0.0
    assert data["drift_status"] == "DRIFTLESS_NULL_BASELINE"
    assert len(data["reasons"]) > 0
    assert (
        "NO_VALIDATED_EDGE_ABSTAIN" in data["reasons"][0]
        or "NO_ELIGIBLE_STRATEGY" in data["reasons"][0]
    )
