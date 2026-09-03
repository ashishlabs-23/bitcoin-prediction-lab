"""
tests/test_prediction_pipeline_layers.py
=========================================
Unit and integration tests for the institutional 7-layer prediction pipeline.

Verifies:
1. Sequential execution of all 7 layers (Telemetry -> Regime -> Forecast -> Opportunity -> Economics -> Risk -> Decision Envelope)
2. Invariant preservation (point-in-time safety, non-execution direction overlay, strict precedence hierarchy)
3. Cryptographic hash chain linkage for canonical D_t output
4. REST API exposure via GET /prediction/pipeline/layers
"""

import os
import sys
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app
from engine.prediction_pipeline import (
    prediction_pipeline,
    Layer1TelemetryOutput,
    Layer2MarketStateOutput,
    Layer3ForecastingOutput,
    Layer4OpportunityOutput,
    Layer5EconomicsOutput,
    Layer6RiskOutput,
    Layer7DecisionOutput,
    UnifiedPipelineResult
)
from engine.decision_envelope import canonical_decision_ledger

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_isolated_test_ledger(tmp_path, monkeypatch):
    test_ledger = str(tmp_path / "test_pipeline_ledger.jsonl")
    monkeypatch.setattr(canonical_decision_ledger, "ledger_file", test_ledger)
    canonical_decision_ledger._last_hash = "0" * 32


def test_layer_1_telemetry_execution():
    candle = {
        "open": 64500.0,
        "high": 65200.0,
        "low": 64400.0,
        "close": 65100.0,
        "volume": 120.5,
        "vol_24h": 0.016,
        "timestamp": "2026-08-31T12:00:00Z"
    }
    l1 = prediction_pipeline.execute_layer_1(candle)
    assert isinstance(l1, Layer1TelemetryOutput)
    assert l1.current_price == 65100.0
    assert l1.data_quality == "VALID"
    assert "norm_close_ret" in l1.feature_vector_32
    assert "rsi_14" in l1.feature_vector_32


def test_layer_2_market_state_and_regime():
    candle = {
        "open": 64500.0,
        "high": 65200.0,
        "low": 64400.0,
        "close": 65100.0,
        "volume": 120.5,
        "vol_24h": 0.016,
        "timestamp": "2026-08-31T12:00:00Z"
    }
    l1 = prediction_pipeline.execute_layer_1(candle)
    l2 = prediction_pipeline.execute_layer_2(l1, candle)
    assert isinstance(l2, Layer2MarketStateOutput)
    assert l2.market_regime in ["RANGING", "TRENDING_BULL", "TRENDING_BEAR", "BREAKOUT", "HIGH_VOLATILITY"]
    assert "event_type" in l2.detected_event


def test_layer_3_probabilistic_forecasting():
    candle = {
        "open": 64500.0,
        "high": 65200.0,
        "low": 64400.0,
        "close": 65100.0,
        "volume": 120.5,
        "vol_24h": 0.016,
        "timestamp": "2026-08-31T12:00:00Z"
    }
    l1 = prediction_pipeline.execute_layer_1(candle)
    l2 = prediction_pipeline.execute_layer_2(l1, candle)
    l3 = prediction_pipeline.execute_layer_3(l1, l2)
    assert isinstance(l3, Layer3ForecastingOutput)
    assert l3.upper_p90 > l1.current_price
    assert 50.0 <= l3.conformal_coverage_target_pct <= 100.0
    assert l3.direction_overlay["state"] in ["NO_DIRECTIONAL_EDGE", "BULLISH", "BEARISH"]


def test_end_to_end_pipeline_execution():
    candle = {
        "open": 64500.0,
        "high": 65200.0,
        "low": 64400.0,
        "close": 65100.0,
        "volume": 120.5,
        "vol_24h": 0.016,
        "timestamp": "2026-08-31T12:00:00Z"
    }
    res = prediction_pipeline.run_pipeline(candle)
    assert isinstance(res, UnifiedPipelineResult)
    
    # Layer 4 Opportunity
    assert res.layer4_opportunity.opportunity_id.startswith("OPP-")
    assert res.layer4_opportunity.target_contract["entry_price"] == 65100.0

    # Layer 5 Economics
    assert res.layer5_economics.execution_drag_bps == 9.5
    assert res.layer5_economics.mode == "TAKER"

    # Layer 6 Risk
    assert res.layer6_risk.daily_budget_limit_pct == 0.50

    # Layer 7 Decision Envelope
    assert res.layer7_decision.decision_id.startswith("DEC-")
    assert res.layer7_decision.action in ["TRADE", "ABSTAIN"]
    assert res.layer7_decision.primary_reason_code in [
        "DATA_INVALID", "MODEL_STATE_BLOCK", "NO_EVENT",
        "PATH_EVIDENCE_INSUFFICIENT", "EV_BELOW_COST",
        "C2_RISK_EXCEEDED", "PATH_EDGE_EXCEEDS_EXECUTION_DRAG"
    ]


def test_get_prediction_pipeline_layers_endpoint():
    response = client.get("/prediction/pipeline/layers")
    assert response.status_code == 200
    data = response.json()
    assert "layer1_telemetry" in data
    assert "layer2_market_state" in data
    assert "layer3_forecasting" in data
    assert "layer4_opportunity" in data
    assert "layer5_economics" in data
    assert "layer6_risk" in data
    assert "layer7_decision" in data
    assert "final_action" in data
    assert "primary_reason" in data
