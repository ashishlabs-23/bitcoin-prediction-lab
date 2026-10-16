"""
tests/test_stage11_forward_validation.py — Stage 11 Shadow Validation Integrity & Forward Evaluation Tests
========================================================================================================
Verifies:
1. Stage 11 forward manifest schema, audit classification, and 2026-09-01T06:00:00Z evaluation frontier.
2. Directional model provenance: training strictly prior to 2026-01-01 00:00:00 UTC with zero 2026 leakage.
3. Corrected Stage 10 scorecard: true C2 conformal coverage (92.36%) and interval sharpness metrics.
4. Explains root cause of the previous 99.79% coverage discrepancy.
5. ForwardOnlyCollector: zero backdating into historical data; pristine forward ledger.
6. ForwardOnlyCollector streaming simulation: causal record, delayed resolve, and SHA-256 hash chaining.
7. Production model registry immutability: HAR-RS-DOW-v1.0 preserved; directional models offline.
8. Live trading disabled: zero order execution integrations.
9. FastAPI endpoint GET /api/research/forward-status returns 200 with complete audit metadata.
10. Honest assessment: 70% directional accuracy objective marked UNSUBSTANTIATED with empirical upper bound.
"""

import os
import sys
import json
import tempfile
import hashlib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from research.stage11_forward_only_collector import (
    ForwardOnlyCollector,
    FORWARD_MANIFEST_PATH,
    FORWARD_LEDGER_PATH,
    FORWARD_SCORECARD_PATH,
)
from api.server import app

client = TestClient(app)

STAGE10_CORRECTED_SCORECARD = os.path.join(
    REPO_ROOT, "experiments", "results", "stage10_shadow_validation", "stage10_shadow_scorecard_corrected.json"
)


@pytest.fixture(scope="module")
def forward_manifest():
    assert os.path.exists(FORWARD_MANIFEST_PATH), f"Missing manifest: {FORWARD_MANIFEST_PATH}"
    with open(FORWARD_MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def corrected_scorecard():
    assert os.path.exists(STAGE10_CORRECTED_SCORECARD), f"Missing corrected scorecard: {STAGE10_CORRECTED_SCORECARD}"
    with open(STAGE10_CORRECTED_SCORECARD, "r", encoding="utf-8") as f:
        return json.load(f)


def test_forward_manifest_schema_and_classification(forward_manifest):
    """Verify Stage 11 manifest schema, audit classification, and forward frontier."""
    assert forward_manifest["manifest_version"] == "STAGE11-FORWARD-VAL-v1.0"
    audit = forward_manifest["audit_classification"]
    assert audit["stage10_classification"] == "VALID_HISTORICAL_OUT_OF_SAMPLE_REPLAY"
    assert audit["stage11_classification"] == "GENUINE_FORWARD_ONLY_EVALUATION"
    assert audit["forward_evaluation_frontier"] == "2026-09-01T06:00:00Z"
    assert "hash_chain_limitation_statement" in audit

    gov = forward_manifest["governance"]
    assert gov["production_model"] == "HAR-RS-DOW-v1.0"
    assert gov["directional_model"] == "directional-gbm-4lag-v1"
    assert gov["live_trading_status"] == "DISABLED"


def test_directional_model_provenance_strictly_pre_2026(forward_manifest):
    """Verify all frozen directional models were trained strictly before 2026-01-01."""
    models_meta = forward_manifest["model_provenance_and_freeze"]
    for m_id, meta in models_meta.items():
        if "directional" in m_id:
            max_maturity = meta["max_target_maturity"]
            assert max_maturity <= "2025-12-31T23:00:00Z", f"Target leakage in {m_id}: max maturity {max_maturity}"
            # Verify artifact exists and checksum matches
            abs_path = os.path.join(REPO_ROOT, meta["artifact_path"])
            assert os.path.exists(abs_path)
            with open(abs_path, "rb") as f:
                sha = hashlib.sha256(f.read()).hexdigest()
            assert sha == meta["artifact_sha256"], f"Checksum mismatch for {m_id}"


def test_stage10_scorecard_corrected_metrics(corrected_scorecard):
    """
    Verify corrected Stage 10 scorecard:
    - 1h accuracy: 52.14% (95% CI: [51.16%, 53.36%])
    - 4h accuracy: 52.00% (95% CI: [50.35%, 53.49%])
    - 24h accuracy: 48.65% (inconclusive, Neff=242)
    - 168h volatility: true C2 coverage is 92.36% (not 99.79%), with interval sharpness reported.
    """
    assert corrected_scorecard["audit_classification"] == "VALID_HISTORICAL_OUT_OF_SAMPLE_REPLAY"
    h1 = corrected_scorecard["horizons"]["1h"]
    assert h1["accuracy_pct"] == 52.14
    assert h1["nominal_sample_size"] == 5838

    h4 = corrected_scorecard["horizons"]["4h"]
    assert h4["accuracy_pct"] == 52.00
    assert h4["effective_sample_size"] == 1458

    h24 = corrected_scorecard["horizons"]["24h"]
    assert h24["accuracy_pct"] == 48.65
    assert "INCONCLUSIVE" in h24["status"]

    vol = corrected_scorecard["horizons"]["168h_volatility"]
    assert vol["audited_correct_empirical_coverage_pct"] == 92.36
    assert vol["reported_stage10_coverage_pct"] == 99.79
    assert "discrepancy_explanation" in vol
    sharpness = vol["interval_sharpness"]
    assert sharpness["mean_interval_width"] == 0.4513
    assert sharpness["mean_relative_width_ratio"] == 2.45
    assert sharpness["mean_winkler_score"] == 0.5420


def test_forward_collector_zero_backdated_records():
    """Verify that forward collector against historical data creates 0 forward records."""
    collector = ForwardOnlyCollector()
    df_raw = pd.read_parquet(os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet"))
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=True)

    # All candles in ohlcv.parquet are on or before the frontier (2026-09-01T06:00:00Z)
    new_f = collector.record_forward_forecasts(df_raw, frontier_time=pd.to_datetime("2026-09-01T06:00:01Z"))
    assert new_f == 0, f"Forward collector should not record any historical bars, got {new_f}"


def test_forward_collector_simulated_stream_and_tamper_evidence():
    """Simulate streaming arrival of future candles, delayed outcome resolution, and hash chaining."""
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl") as tmp_ledger:
        tmp_ledger_path = tmp_ledger.name

    try:
        collector = ForwardOnlyCollector(ledger_path=tmp_ledger_path)

        # Create 3 synthetic forward candles starting after frontier
        t0 = pd.to_datetime("2026-09-01 07:00:00+00:00")
        t1 = pd.to_datetime("2026-09-01 08:00:00+00:00")
        t2 = pd.to_datetime("2026-09-01 09:00:00+00:00")

        # Include historical lookback so features can be calculated
        df_hist = pd.read_parquet(os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")).tail(200).copy()
        df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"], utc=True)

        new_rows = pd.DataFrame([
            {"timestamp": t0, "open": 79000.0, "high": 79200.0, "low": 78900.0, "close": 79100.0, "volume": 100.0},
            {"timestamp": t1, "open": 79100.0, "high": 79500.0, "low": 79050.0, "close": 79400.0, "volume": 120.0},
            {"timestamp": t2, "open": 79400.0, "high": 79600.0, "low": 79300.0, "close": 79550.0, "volume": 110.0},
        ])
        df_stream = pd.concat([df_hist, new_rows], ignore_index=True)

        # 1. Record forecasts for t0 and t1
        n_recorded = collector.record_forward_forecasts(df_stream, frontier_time=t0)
        assert n_recorded > 0

        # Verify tamper-evident hash chaining on ledger
        valid, msg, count = collector.verify_ledger_integrity()
        assert valid is True, f"Tamper evident verification failed: {msg}"
        assert count == n_recorded

        # 2. Resolve outcomes at time t2 (allows 1h forecast for t0 to resolve at t1, and t1 to resolve at t2)
        n_resolved = collector.resolve_forward_outcomes(df_stream, as_of_time=t2)
        assert n_resolved > 0

        # Verify integrity again after resolution events appended
        valid, msg, count_total = collector.verify_ledger_integrity()
        assert valid is True, f"Integrity failed after resolution: {msg}"
        assert count_total == n_recorded + n_resolved

    finally:
        if os.path.exists(tmp_ledger_path):
            os.remove(tmp_ledger_path)


def test_production_model_registry_immutability():
    """Verify HAR-RS-DOW-v1.0 remains the sole authorized production model."""
    from models.authoritative_model_registry import (
        get_active_production_model,
        get_directional_research_baseline,
        ModelClassification,
        AuthorizationStatus,
    )
    prod = get_active_production_model()
    assert prod.canonical_id == "HAR-RS-DOW-v1.0"
    assert prod.classification == ModelClassification.PRODUCTION_VOLATILITY
    assert prod.authorization_status == AuthorizationStatus.AUTHORIZED_FOR_PRODUCTION

    dir_model = get_directional_research_baseline()
    assert dir_model.canonical_id == "directional-gbm-4lag-v1"
    assert dir_model.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY


def test_api_forward_status_endpoint():
    """Test GET /api/research/forward-status returns 200 with complete Stage 11 metadata."""
    response = client.get("/api/research/forward-status")
    assert response.status_code == 200
    data = response.json()

    assert data["pipeline_version"] == "STAGE11-FORWARD-VAL-v1.0"
    assert data["evaluation_mode"] == "GENUINE_FORWARD_ONLY_EVALUATION"
    assert data["forward_frontier"] == "2026-09-01T06:00:00Z"
    assert data["stage10_classification"] == "VALID_HISTORICAL_OUT_OF_SAMPLE_REPLAY"
    assert "scorecard" in data
    assert "epistemic_notice" in data


def test_seventy_percent_objective_honest_evaluation(corrected_scorecard, forward_manifest):
    """Verify that 70% accuracy objective is explicitly evaluated and marked unsubstantiated."""
    scorecard_assessment = corrected_scorecard["seventy_percent_objective_assessment"]
    assert scorecard_assessment["substantiated_on_holdout_data"] is False
    assert scorecard_assessment["scientific_status"] == "UNSUBSTANTIATED"

    # Directional upper bound on 2026 holdout is 53.36% (16.64% below 70%)
    h1 = corrected_scorecard["horizons"]["1h"]
    assert h1["accuracy_95_ci"][1] < 55.0

    stopping = forward_manifest["stopping_and_rejection_criteria"]
    assert "70% accuracy is NOT substantiated" in stopping["seventy_percent_objective_rule"]
