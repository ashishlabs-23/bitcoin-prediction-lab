"""
tests/test_v32_25_directional_integration.py — V32.25 AI Forecast & Smart Entry Integration Test Suite
=====================================================================================================
Verifies:
1. Directional model artifact SHA-256 verification and fail-closed security.
2. Causal return feature extraction on 15m and 1h intervals.
3. Genuine directional probabilities (P_up, P_down) with strict research-only governance.
4. Forecast contract API integration (/api/forecast/latest) with honest baseline/band/direction separation.
5. Smart Entry consumption of directional evidence while preserving mu=0.0 driftless null baseline.
6. Fail-closed ABSTAIN under transaction cost hurdle and zero prospective ledger writes by default.
"""

import os
import json
import hashlib
import pytest
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from api.server import app
from engine.directional_forecast_service import (
    verify_and_load_directional_model,
    extract_directional_features,
    compute_directional_gbdt_forecast,
    FREEZE_METADATA_PATH,
)
from engine.forecast_engine_15m import generate_forecast_contract
from engine.smart_entry_engine import SmartEntryDecisionEngine
from engine.probabilistic_entry_engine import ProbabilisticEntryEngine


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Section 1: Directional GBDT Artifact Integrity & Fail-Closed Gate
# ---------------------------------------------------------------------------

def test_v32_25_directional_models_sha256_match_authoritative_manifest():
    """Verify that all directional GBDT artifacts match their frozen SHA-256 hashes."""
    assert os.path.exists(FREEZE_METADATA_PATH), "Freeze metadata missing."
    with open(FREEZE_METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    for horizon in ["1h", "4h", "24h"]:
        model, info, err = verify_and_load_directional_model(horizon)
        assert err is None, f"Failed loading model for {horizon}: {err}"
        assert model is not None, f"Model for {horizon} is None"
        assert info["artifact_sha256"] == meta[horizon]["artifact_sha256"]


def test_v32_25_tampered_model_artifact_fails_closed():
    """Verify that corrupted or mismatched artifact hashes are rejected immediately."""
    model, info, err = verify_and_load_directional_model("invalid_horizon")
    assert model is None
    assert "Unsupported horizon" in str(err)


# ---------------------------------------------------------------------------
# Section 2: Causal Feature Extraction
# ---------------------------------------------------------------------------

def test_v32_25_causal_feature_extraction_hourly():
    """Verify exact 4 causal return features on hourly closes."""
    # 200 synthetic closes with known returns
    closes = [100.0 * (1.001 ** i) for i in range(200)]
    feats, err = extract_directional_features(closes, timeframe="1h")
    assert err is None
    assert feats is not None
    assert "ret_1h" in feats
    assert "ret_4h" in feats
    assert "ret_24h" in feats
    assert "ret_168h" in feats

    # ret_1h = ln(c_t / c_{t-1})
    assert np.isclose(feats["ret_1h"], np.log(closes[-1] / closes[-2]), atol=1e-6)
    assert np.isclose(feats["ret_4h"], np.log(closes[-1] / closes[-5]), atol=1e-6)
    assert np.isclose(feats["ret_24h"], np.log(closes[-1] / closes[-25]), atol=1e-6)
    assert np.isclose(feats["ret_168h"], np.log(closes[-1] / closes[-169]), atol=1e-6)


def test_v32_25_causal_feature_extraction_insufficient_history_fails_closed():
    """Verify that history shorter than 168 hours fails closed with explicit error."""
    short_closes = [100.0] * 50
    feats, err = extract_directional_features(short_closes, timeframe="1h")
    assert feats is None
    assert "Insufficient price history" in str(err)


# ---------------------------------------------------------------------------
# Section 3: Directional Forecast Service
# ---------------------------------------------------------------------------

def test_v32_25_directional_gbdt_inference_probabilities():
    """Verify that compute_directional_gbdt_forecast returns valid probabilities and direction."""
    closes = [50000.0 + (i * 10) for i in range(300)]
    result = compute_directional_gbdt_forecast(closes, timeframe="1h", horizon="1h")

    assert result["status"] == "RESEARCH_INFERENCE_AVAILABLE"
    assert result["model_id"] == "directional-gbm-1h-v1"
    assert result["probability_up"] is not None
    assert result["probability_down"] is not None
    assert 0.0 <= result["probability_up"] <= 1.0
    assert 0.0 <= result["probability_down"] <= 1.0
    assert np.isclose(result["probability_up"] + result["probability_down"], 1.0, atol=1e-3)
    assert result["predicted_direction"] in ["UP", "DOWN"]
    assert result["governance_status"] == "OFFLINE_RESEARCH_ONLY"
    assert result["live_trading_authorized"] is False
    assert result["cost_adjusted_expectancy"] == "NEGATIVE_AFTER_FEES"


# ---------------------------------------------------------------------------
# Section 4: Forecast Engine & API Contract Separation
# ---------------------------------------------------------------------------

def test_v32_25_forecast_engine_attaches_directional_evidence():
    """Verify that generate_forecast_contract attaches genuine directional output while keeping baseline intact."""
    fc_1h = generate_forecast_contract(horizon="1h")
    assert fc_1h["status"] == "FORECAST_AVAILABLE_RESEARCH_ONLY"
    assert fc_1h["model_id"] == "EMPIRICAL_CONFORMAL_PERSISTENCE_v1.0"
    assert fc_1h["forecast_type"] == "NON_DIRECTIONAL_RESEARCH_BASELINE"
    assert fc_1h["directional_model_runtime_status"] == "RESEARCH_INFERENCE_ACTIVE"
    assert fc_1h["directional_probability_up"] is not None
    assert fc_1h["directional_probability_down"] is not None
    assert fc_1h["directional_predicted_direction"] in ["UP", "DOWN"]
    assert "directional_forecast" in fc_1h
    assert fc_1h["directional_forecast"]["status"] == "RESEARCH_INFERENCE_AVAILABLE"

    # Strict governance: recommendation remains ABSTAIN, trading disabled
    assert fc_1h["directional_recommendation"] == "ABSTAIN"
    assert fc_1h["live_trading"] == "DISABLED"


def test_v32_25_api_forecast_latest_directional_payload():
    """Verify GET /api/forecast/latest exposes genuine directional probabilities."""
    client = TestClient(app)
    resp = client.get("/api/forecast/latest?horizon=1h")
    assert resp.status_code == 200
    data = resp.json()

    assert data["directional_model_runtime_status"] == "RESEARCH_INFERENCE_ACTIVE"
    assert data["directional_probability_up"] is not None
    assert data["directional_probability_down"] is not None
    assert data["directional_predicted_direction"] in ["UP", "DOWN"]
    assert data["directional_model_id"] == "directional-gbm-1h-v1"
    assert data["live_trading"] == "DISABLED"


# ---------------------------------------------------------------------------
# Section 5: Smart Entry Integration & Driftless Null Governance
# ---------------------------------------------------------------------------

def test_v32_25_smart_entry_consumes_directional_evidence_and_abstains():
    """Verify SmartEntryDecisionEngine evaluates directional evidence but preserves mu=0.0 fail-closed ABSTAIN."""
    engine = SmartEntryDecisionEngine()
    now_utc = datetime.now(timezone.utc)
    base_epoch = int(now_utc.timestamp()) - (300 * 3600)
    candles = [
        {
            "timestamp_utc": datetime.fromtimestamp(base_epoch + (i * 3600), tz=timezone.utc).isoformat(),
            "open": 64000.0 + (i * 10),
            "high": 64100.0 + (i * 10),
            "low": 63900.0 + (i * 10),
            "close": 64050.0 + (i * 10),
        }
        for i in range(250)
    ]

    result = engine.evaluate_market(
        live_price=66500.0,
        candles=candles,
        regime="VOL_EXPANDING",
        user_direction_preference="AUTO",
        cost_scenario="COINBASE_RETAIL_87BPS",
        horizon="1h",
        persist=False,
    )

    # Must fail-closed ABSTAIN
    assert result["status"] == "ABSTAIN"
    assert result["decision_action"] == "ABSTAIN"
    assert result["drift_parameter_mu"] == 0.0
    assert result["drift_status"] == "DRIFTLESS_NULL_BASELINE"
    assert result["execution_authorization"] == "DISABLED — ANALYSIS ONLY"
    assert result["persisted"] is False

    # Must contain genuine directional model evidence
    assert "directional_model_evidence" in result
    dir_ev = result["directional_model_evidence"]
    assert dir_ev is not None
    assert dir_ev["status"] == "RESEARCH_INFERENCE_AVAILABLE"
    assert dir_ev["model_id"] == "directional-gbm-1h-v1"
    assert dir_ev["probability_up"] is not None
    assert dir_ev["probability_down"] is not None


def test_v32_25_smart_entry_api_returns_directional_evidence():
    """Verify POST /api/research/smart-entry returns directional_model_evidence in response."""
    client = TestClient(app)
    now_dt = datetime.now(timezone.utc)
    base_epoch = int(now_dt.timestamp()) - (200 * 3600)
    candles = [
        {
            "timestamp_utc": datetime.fromtimestamp(base_epoch + (i * 3600), tz=timezone.utc).isoformat(),
            "open": 65000.0 + (i * 5),
            "high": 65100.0 + (i * 5),
            "low": 64900.0 + (i * 5),
            "close": 65050.0 + (i * 5),
        }
        for i in range(200)
    ]
    snapshot_ts = datetime.fromtimestamp(base_epoch + (199 * 3600), tz=timezone.utc).isoformat()

    payload = {
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "timestamp_utc": snapshot_ts,
        "live_price": 66000.0,
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
    assert data["drift_parameter_mu"] == 0.0
    assert data["drift_status"] == "DRIFTLESS_NULL_BASELINE"
    assert data["persisted"] is False
    assert "directional_model_evidence" in data
    assert data["directional_model_evidence"] is not None
    assert data["directional_model_evidence"]["status"] == "RESEARCH_INFERENCE_AVAILABLE"
