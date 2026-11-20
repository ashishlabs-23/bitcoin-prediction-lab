"""
tests/test_authorization_consistency.py — Cross-System Consistency for Authorization & Gating
=============================================================================================
Workstream D: One Truthful Authorization and Health State.

Verifies:
1. Single authoritative runtime status: Production inference is gated (BLOCKED_AUDIT_FAILURE).
2. Live trading is strictly disabled across all endpoints.
3. Model classification: HAR-RS-DOW is a volatility/variance model (directional_prediction_capability = False).
4. Historical baseline separation: Empirical quantile outputs are identified as baselines, not ML predictions.
5. Startup gate verification: Startup checks pass while fail-closed security remains intact.
"""

import pytest
from fastapi.testclient import TestClient

from api.server import app
from models.authoritative_model_registry import (
    get_active_production_model,
    AuthorizationStatus,
    ModelClassification,
    is_production_authorized,
)
from validation.startup_gate import verify_scientific_contract


def test_authoritative_model_registry_state():
    """Verified model identity remains offline-only until a governance decision."""
    model = get_active_production_model()

    assert model.canonical_id == "Standard-HAR-v1.0"
    assert model.classification in [ModelClassification.BASELINE_VOLATILITY, ModelClassification.PRODUCTION_VOLATILITY]
    assert model.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
    assert model.directional_prediction_capability is False
    assert "rv7d_var_ann" in model.forecast_target
    assert "disabled" in model.applicable_limitations.lower()


def test_api_lifespan_research_gate_consistency():
    """Verifies that app.state.research_gate is authoritative and synchronized during lifespan."""
    with TestClient(app) as client:
        assert hasattr(app.state, "research_gate")
        gate = app.state.research_gate
        assert gate["status"] == "OFFLINE_RESEARCH_ONLY"
        assert gate["authorized"] is False
        assert gate["authorization_status"] == "OFFLINE_RESEARCH_ONLY"
        assert gate["reason_code"] == "MODEL_UNAUTHORIZED"
        assert gate["research_edge_status"] == "NO_GO_NO_VALIDATED_EDGE"
        assert gate["trading_enabled"] is False


def test_terminal_model_identity_endpoint():
    """Verifies GET /api/terminal/model-identity reports truthful non-directional authorized identity."""
    with TestClient(app) as client:
        res = client.get("/api/terminal/model-identity")
        assert res.status_code == 200

        data = res.json()
        assert data["canonical_id"] == "Standard-HAR-v1.0"
        assert data["classification"] in ["BASELINE_VOLATILITY", "PRODUCTION_VOLATILITY"]
        assert data["authorization_status"] == "OFFLINE_RESEARCH_ONLY"
        assert data["directional_prediction_capability"] is False


def test_prediction_endpoints_fail_closed_as_baselines():
    """Verifies that prediction endpoints identify outputs as experimental baselines, not ML models."""
    with TestClient(app) as client:
        # /prediction/latest returns baseline with production_forecast_available=False
        res_latest = client.get("/prediction/latest")
        assert res_latest.status_code == 200
        latest_data = res_latest.json()
        assert latest_data["status"] in ["DATA_UNAVAILABLE", "EXPERIMENTAL_BASELINE"]
        assert latest_data["production_forecast_available"] is False
        assert latest_data["trading_enabled"] is False
        assert "NOT VALIDATED FOR PREDICTIVE" in latest_data["validation_status"]

        # /prediction/range returns baseline range
        res_range = client.get("/prediction/range")
        assert res_range.status_code == 200
        range_data = res_range.json()
        assert range_data["status"] in ["DATA_UNAVAILABLE", "EXPERIMENTAL_BASELINE"]
        assert range_data["production_forecast_available"] is False
        assert range_data["trading_enabled"] is False


def test_production_model_alignment_fails_closed_for_offline_model():
    from models.authoritative_model_registry import verify_production_model_alignment

    assert (
        verify_production_model_alignment(
            "/api/terminal/live", "HAR-RS-DOW-v1.0"
        )
        is False
    )


def test_runtime_readiness_cannot_override_registry_authorization():
    """A positive runtime flag cannot supersede the registry's offline-only policy."""
    runtime_readiness = {
        "authorized": True,
        "authorization_status": "AUTHORIZED_FOR_PRODUCTION",
    }

    assert is_production_authorized(runtime_readiness) is False


def test_status_contract_does_not_grant_runtime_only_authorization():
    """System status remains blocked when only the runtime gate claims authorization."""
    from engine.status_contract import evaluate_system_status

    status = evaluate_system_status(readiness_override={
        "authorized": True,
        "authorization_status": "AUTHORIZED_FOR_PRODUCTION",
        "status": "READY",
        "reason": "Integrity checks passed",
        "restricted_serving_scope": "VOLATILITY_ONLY",
    })

    assert status.production_forecast_status == "BLOCKED"
    assert status.restricted_serving_scope == "NONE"
    assert "model registry" in status.production_forecast_reason
    assert status.execution_status == "DISABLED — ANALYSIS ONLY"


def test_trading_safeguards_disabled_everywhere():
    """Verifies that trading is disabled and live capital execution is unauthorized."""
    with TestClient(app) as client:
        res_entry = client.get("/api/research/entry-tp-sl")
        assert res_entry.status_code == 200
        entry_data = res_entry.json()
        assert entry_data["status"] == "BLOCKED"
        assert entry_data["live_capital_authorized"] is False
        assert entry_data["trading_enabled"] is False

        res_range_health = client.get("/prediction/range/health")
        assert res_range_health.status_code == 200
        assert res_range_health.json()["status"] == "BLOCKED_PROVENANCE_UNVERIFIED"
        assert res_range_health.json()["trading_enabled"] is False


def test_scientific_freeze_contract_verification():
    """Verifies that the scientific contract verification passes."""
    success = verify_scientific_contract()
    assert success is True
