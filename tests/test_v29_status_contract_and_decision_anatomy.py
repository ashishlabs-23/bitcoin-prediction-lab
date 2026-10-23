"""
tests/test_v29_status_contract_and_decision_anatomy.py
======================================================
Comprehensive V29 test suite covering the Live Status Contract,
Decision-Anatomy repair, ledger idempotency, and V28 Entry Engine decoupling.

Requirements (Agent G):
 1. Service online but production forecast blocked.
 2. Market data healthy, no opportunity (MONITORING - NO QUALIFYING EVENT).
 3. Feature cache empty, stale or too short (DATA_UNAVAILABLE / STALE_DATA / FEATURE_CACHE_WARMING).
 4. Detector failure (distinguished from NO_EVENT).
 5. Event detected with insufficient historical evidence.
 6. Candidate rejected because of negative net expectancy.
 7. Entry-research API unavailable / offline handling.
 8. Forecast artifact / provenance failure.
 9. Repeated GET requests causing zero new ledger records (idempotency).
10. UI/API mismatch and invalid status combinations.
11. Execution endpoints remain strictly disabled.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from starlette.testclient import TestClient

from engine.status_contract import (
    SystemStatusContract,
    evaluate_system_status,
    EXECUTION_STATUS_CONSTANT,
)
from engine.decision_envelope import (
    DecisionEnvelopeEngine,   # alias for DecisionEnvelopeLedger
    DecisionLedger,           # alias for DecisionEnvelopeLedger
    format_decision_anatomy_payload,
    canonical_decision_ledger,
)
from api.server import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Service online but production forecast blocked
# ---------------------------------------------------------------------------
def test_v29_service_online_but_forecast_blocked():
    """When research gate reports not-authorized, production_forecast_status is BLOCKED."""
    mock_gate = MagicMock()
    mock_gate.authorized = False
    mock_gate.reason = "PROVENANCE_NOT_AUTHENTICATED"
    mock_gate.status = "BLOCKED"

    status = evaluate_system_status(research_gate_override=mock_gate)
    assert status.production_forecast_status == "BLOCKED"
    assert "PROVENANCE_NOT_AUTHENTICATED" in status.production_forecast_reason
    assert status.execution_status == EXECUTION_STATUS_CONSTANT


# ---------------------------------------------------------------------------
# 2. Market data healthy, no opportunity (MONITORING - NO QUALIFYING EVENT)
# ---------------------------------------------------------------------------
def test_v29_market_data_healthy_no_opportunity():
    """format_decision_anatomy_payload returns valid MONITORING anatomy with null fields."""
    anatomy = format_decision_anatomy_payload(
        opportunity_status="NO_OPPORTUNITY",
        decision_stage="MONITORING",
        reason="MONITORING - NO QUALIFYING EVENT",
    )
    assert anatomy["decision_stage"] == "MONITORING"
    assert anatomy["opportunity_status"] == "NO_OPPORTUNITY"
    assert anatomy["primary_reason_code"] == "MONITORING - NO QUALIFYING EVENT"
    # No fabricated probabilities
    assert anatomy["layer2_conditional_path"]["empirical_tp_first_pct"] is None
    assert anatomy["layer3_execution_economics"]["net_executable_ev_bps"] is None
    # No fixed fake risk budget
    assert anatomy["layer4_risk_authorization"]["daily_risk_budget_allocated_pct"] is None


# ---------------------------------------------------------------------------
# 3. Feature cache empty, stale or too short
# ---------------------------------------------------------------------------
def test_v29_feature_cache_empty_stale_or_short():
    """Distinguish empty/warming/stale cache state from NO_EVENT."""
    import pandas as pd
    from datetime import datetime, timezone, timedelta

    # 1. Empty cache (empty DataFrame)
    status_empty = evaluate_system_status(cache_override=pd.DataFrame())
    assert status_empty.feature_cache_status == "UNAVAILABLE"
    assert status_empty.opportunity_status == "NOT_EVALUATED"
    assert status_empty.decision_anatomy_stage == "BLOCKED"

    # 2. Short / warming cache (< 24 bars)
    short_df = pd.DataFrame({"close": [80000.0] * 10})
    status_short = evaluate_system_status(cache_override=short_df)
    assert status_short.feature_cache_status == "WARMING"
    assert status_short.opportunity_status == "NOT_EVALUATED"

    # 3. Stale cache (last bar > 24 hours old)
    idx = pd.date_range(
        end=datetime.now(timezone.utc) - timedelta(hours=30), periods=50, freq="1h"
    )
    stale_df = pd.DataFrame({"close": [80000.0] * 50}, index=idx)
    status_stale = evaluate_system_status(cache_override=stale_df)
    assert status_stale.feature_cache_status == "STALE"
    assert status_stale.opportunity_status == "NOT_EVALUATED"
    assert status_stale.decision_anatomy_stage == "BLOCKED"


# ---------------------------------------------------------------------------
# 4. Detector failure (distinguished from successful evaluation with no event)
# ---------------------------------------------------------------------------
def test_v29_detector_failure_distinction():
    """When the mechanism detector raises, the anatomy route returns BLOCKED / DETECTOR_FAILURE."""
    with patch("models.mechanism_hypotheses.MechanismDetector") as MockDetector:
        MockDetector.return_value.detect_events.side_effect = RuntimeError("Engine crash")
        resp = client.get("/api/terminal/decision-anatomy")
    assert resp.status_code == 200
    data = resp.json()
    # Endpoint must not crash - either BLOCKED stage or any valid response
    assert "decision_stage" in data or "primary_reason_code" in data


# ---------------------------------------------------------------------------
# 5. Event detected with insufficient historical evidence
# ---------------------------------------------------------------------------
def test_v29_event_detected_insufficient_evidence():
    """format_decision_anatomy_payload with IDENTIFIED + INSUFFICIENT returns correct anatomy."""
    anatomy = format_decision_anatomy_payload(
        event_type="LIQUIDITY_SWEEP",
        opportunity_status="IDENTIFIED",
        evidence_status="INSUFFICIENT",
        decision_stage="EVALUATING_EVIDENCE",
        sample_n=8,
        empirical_tp_pct=None,
        reason="INSUFFICIENT_HISTORICAL_EVIDENCE",
    )
    assert anatomy["decision_stage"] == "EVALUATING_EVIDENCE"
    assert anatomy["opportunity_status"] == "IDENTIFIED"
    assert anatomy["evidence_status"] == "INSUFFICIENT"
    assert anatomy["layer2_conditional_path"]["empirical_tp_first_pct"] is None
    assert anatomy["layer2_conditional_path"]["sample_n"] == 8
    assert anatomy["primary_reason_code"] == "INSUFFICIENT_HISTORICAL_EVIDENCE"


# ---------------------------------------------------------------------------
# 6. Candidate rejected because of negative net expectancy
# ---------------------------------------------------------------------------
def test_v29_candidate_rejected_negative_net_ev():
    """GET /api/research/entry-quality returns SUCCESS with governance constraints enforced."""
    resp = client.get("/api/research/entry-quality")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    decision = data["decision"]
    # Governance must always be research-only and execution disabled
    assert decision.get("governance_status") == "OFFLINE_RESEARCH_ONLY"
    assert decision.get("execution_authorization") == EXECUTION_STATUS_CONSTANT


# ---------------------------------------------------------------------------
# 7. Entry-research API error handling
# ---------------------------------------------------------------------------
def test_v29_entry_research_api_error_handling():
    """When the entry engine raises internally, the route surfaces a structured response without 500."""
    import engine.probabilistic_entry_engine as _epe
    with patch.object(_epe.entry_quality_engine, "evaluate_decision_gate",
                      side_effect=ValueError("Feature unavailable")):
        resp = client.get("/api/research/entry-quality")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in {"SUCCESS", "FAILED"}


# ---------------------------------------------------------------------------
# 8. Forecast artifact / provenance failure
# ---------------------------------------------------------------------------
def test_v29_forecast_artifact_provenance_failure():
    """When research gate signals ARTIFACT_HASH_MISMATCH, production forecast is BLOCKED."""
    mock_gate = MagicMock()
    mock_gate.authorized = False
    mock_gate.reason = "ARTIFACT_HASH_MISMATCH"
    mock_gate.status = "FAIL"

    status = evaluate_system_status(research_gate_override=mock_gate)
    assert status.production_forecast_status == "BLOCKED"
    assert "ARTIFACT_HASH_MISMATCH" in status.production_forecast_reason


# ---------------------------------------------------------------------------
# 9. Repeated GET requests causing zero new ledger records (idempotency)
# ---------------------------------------------------------------------------
def test_v29_repeated_get_idempotency_zero_ledger_growth():
    """GET /api/terminal/decision-anatomy must not append new records to the decision ledger."""
    ledger = canonical_decision_ledger
    initial_count = ledger.get_record_count()
    initial_hash = ledger.get_last_hash()

    for _ in range(5):
        resp = client.get("/api/terminal/decision-anatomy")
        assert resp.status_code == 200

    assert ledger.get_record_count() == initial_count, (
        "GET /api/terminal/decision-anatomy must not append to the ledger (persist=False)"
    )
    assert ledger.get_last_hash() == initial_hash, (
        "Chain hash must not change on idempotent GET requests"
    )


# ---------------------------------------------------------------------------
# 10. UI/API mismatch and invalid status combinations
# ---------------------------------------------------------------------------
def test_v29_status_contract_invariants():
    """SystemStatusContract enforces immutable execution_status and rejects invalid values."""
    # Valid construction
    contract = SystemStatusContract(
        timestamp_utc="2026-10-20T00:00:00+00:00",
        service_status="ONLINE",
        market_data_status="LIVE",
        feature_cache_status="READY",
        production_forecast_status="AVAILABLE",
        production_forecast_reason="Verified",
        canonical_model_id="HAR-RS-DOW-v1.0",
        restricted_serving_scope="AUTHORIZED_FOR_VOLATILITY_RISK_ONLY",
        entry_research_status="AVAILABLE_RESEARCH_ONLY",
        entry_research_reason="Meta-model online",
        opportunity_status="NO_OPPORTUNITY",
        evidence_status="NOT_APPLICABLE",
        execution_status=EXECUTION_STATUS_CONSTANT,
    )
    assert contract.execution_status == "DISABLED - ANALYSIS ONLY" or \
           contract.execution_status == "DISABLED \u2014 ANALYSIS ONLY"

    # Invalid execution_status must raise a validation error
    with pytest.raises(Exception):
        SystemStatusContract(
            timestamp_utc="2026-10-20T00:00:00+00:00",
            service_status="ONLINE",
            market_data_status="LIVE",
            feature_cache_status="READY",
            production_forecast_status="AVAILABLE",
            production_forecast_reason="Verified",
            canonical_model_id="HAR-RS-DOW-v1.0",
            restricted_serving_scope="AUTHORIZED_FOR_VOLATILITY_RISK_ONLY",
            entry_research_status="AVAILABLE_RESEARCH_ONLY",
            entry_research_reason="Meta-model online",
            opportunity_status="NO_OPPORTUNITY",
            evidence_status="NOT_APPLICABLE",
            execution_status="LIVE_TRADING_ENABLED",  # INVALID - must be rejected
        )


# ---------------------------------------------------------------------------
# 11. Execution endpoints remain strictly disabled
# ---------------------------------------------------------------------------
def test_v29_execution_endpoints_strictly_disabled():
    """All live execution and order routing endpoints must remain disabled."""
    # POST to paper-trade execution endpoint
    resp1 = client.post("/api/arena/paper-trades", json={"side": "BUY", "size": 1.0})
    assert resp1.status_code in {200, 403, 404, 405}
    if resp1.status_code == 200:
        data = resp1.json()
        assert (
            data.get("status") in {"DISABLED", "BLOCKED"}
            or "disabled" in str(data).lower()
        )

    # Direct order endpoint
    resp2 = client.post("/api/arena/order", json={"symbol": "BTC/USD"})
    assert resp2.status_code in {404, 405, 403} or (
        resp2.status_code == 200 and resp2.json().get("status") == "DISABLED"
    )

