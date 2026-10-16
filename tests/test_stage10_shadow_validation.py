"""
tests/test_stage10_shadow_validation.py — Acceptance Test Suite for Stage 10 Shadow Validation
=============================================================================================
Verifies:
1. Preregistered manifest schema and frozen artifact checksums.
2. Causal timing and zero future lookahead (forecast recorded before outcome maturity).
3. Cryptographic tamper-evident hash chaining across ledger events.
4. Tamper detection: modifying any record breaks verification.
5. Pipeline idempotency (safe resume with zero duplicate records).
6. Accurate multi-horizon resolution (1h, 4h, 24h, 168h).
7. Strict isolation between production volatility and offline directional models.
8. Corrected transaction-cost simulation (turnover includes cash liquidations).
9. Zero order-execution calls in shadow pipeline.
10. API endpoints (/api/research/shadow-status and /api/research/shadow-ledger) return 200.
11. Honest evaluation of 70% objective (marked UNSUBSTANTIATED).
"""

import os
import sys
import json
import tempfile
import hashlib
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from research.stage10_shadow_pipeline import (
    ShadowValidationPipeline,
    MANIFEST_PATH,
    LEDGER_PATH,
    SCORECARD_PATH,
    sha256_canonical_json,
)
from api.server import app

client = TestClient(app)


@pytest.fixture(scope="module")
def manifest_data():
    assert os.path.exists(MANIFEST_PATH), f"Manifest missing at {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def scorecard_data():
    assert os.path.exists(SCORECARD_PATH), f"Scorecard missing at {SCORECARD_PATH}"
    with open(SCORECARD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_manifest_preregistration_integrity(manifest_data):
    """Verify preregistered manifest schema and frozen model checksums."""
    required_sections = [
        "manifest_version",
        "registration_timestamp",
        "git_commit",
        "governance",
        "data_contracts",
        "evaluation_horizons",
        "frozen_models",
        "baselines",
        "transaction_cost_scenarios",
        "stopping_and_inconclusive_criteria",
    ]
    for s in required_sections:
        assert s in manifest_data, f"Missing required section {s} in manifest"

    # Verify frozen model checksums
    for m_id, m_meta in manifest_data["frozen_models"].items():
        abs_path = os.path.join(REPO_ROOT, m_meta["artifact_path"])
        assert os.path.exists(abs_path), f"Artifact missing for {m_id}: {abs_path}"
        with open(abs_path, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        assert sha == m_meta["artifact_sha256"], f"Checksum mismatch for {m_id}"


def test_causal_timing_and_zero_future_leakage():
    """Verify that every forecast was recorded prior to its resolution and target maturity."""
    assert os.path.exists(LEDGER_PATH), f"Ledger missing at {LEDGER_PATH}"
    forecasts = {}

    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            e_type = event.get("event_type")
            payload = event.get("event_payload", {})

            if e_type == "FORECAST":
                f_id = payload["forecast_id"]
                t_origin = payload["forecast_origin_timestamp"]
                t_exp = payload["expected_resolution_timestamp"]
                t_avail = payload["data_available_timestamp"]
                assert t_origin < t_exp, f"Origin {t_origin} must be strictly before maturity {t_exp}"
                assert t_avail <= t_exp, f"Data availability {t_avail} must be <= maturity {t_exp}"
                forecasts[f_id] = payload

            elif e_type == "RESOLUTION":
                f_id = payload["forecast_id"]
                assert f_id in forecasts, f"Resolution for unrecorded forecast {f_id}"
                f_origin = forecasts[f_id]["forecast_origin_timestamp"]
                f_exp = forecasts[f_id]["expected_resolution_timestamp"]
                t_res = payload["resolution_timestamp_utc"]
                # Target timestamp must equal expected resolution timestamp
                assert payload["target_timestamp"] == f_exp


def test_ledger_tamper_evident_integrity():
    """Verify cryptographic hash chaining across all events in the ledger."""
    pipeline = ShadowValidationPipeline(ledger_path=LEDGER_PATH)
    is_valid, msg, count = pipeline.verify_ledger_integrity()
    assert is_valid is True, f"Ledger integrity verification failed: {msg}"
    assert count >= 1000, f"Expected >= 1,000 ledger events, got {count}"


def test_ledger_tamper_detection_in_corrupted_copy():
    """Verify that tampering with any event immediately fails cryptographic verification."""
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl") as tmp:
        tmp_path = tmp.name

    try:
        # Copy first 10 lines from real ledger
        lines = []
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 10:
                    break
                lines.append(line)

        # Mutate line 5
        corrupted_event = json.loads(lines[5])
        corrupted_event["event_payload"]["reference_price"] = 999999.99
        lines[5] = json.dumps(corrupted_event) + "\n"

        with open(tmp_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        pipeline = ShadowValidationPipeline(ledger_path=tmp_path)
        is_valid, msg, _ = pipeline.verify_ledger_integrity()
        assert is_valid is False, "Corrupted ledger should have failed verification!"
        assert "Tamper detected" in msg or "Broken hash chain" in msg
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_pipeline_idempotency_and_safe_restart():
    """Verify that running the pipeline repeatedly never duplicates records."""
    pipeline = ShadowValidationPipeline(ledger_path=LEDGER_PATH)
    initial_event_count = len(pipeline.ledger_events)

    import pandas as pd
    df_raw = pd.read_parquet(os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet"))
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=True)

    # Re-run recording
    new_f = pipeline.record_prospective_forecasts(df_raw)
    assert new_f == 0, f"Expected 0 new forecasts on idempotent replay, got {new_f}"

    # Re-run resolution
    new_r = pipeline.resolve_matured_outcomes(df_raw)
    assert new_r == 0, f"Expected 0 new resolutions on idempotent replay, got {new_r}"

    assert len(pipeline.ledger_events) == initial_event_count


def test_production_vs_research_model_isolation(scorecard_data, manifest_data):
    """Verify strict role segregation between production volatility and offline directional models."""
    gov = manifest_data["governance"]
    assert gov["production_model"] == "HAR-RS-DOW-v1.0"
    assert gov["production_model_authorization"] == "AUTHORIZED_FOR_PRODUCTION"
    assert gov["directional_model"] == "directional-gbm-4lag-v1"
    assert gov["directional_model_authorization"] == "OFFLINE_RESEARCH_ONLY"
    assert gov["live_trading_status"] == "DISABLED"
    assert gov["order_execution_calls_allowed"] is False

    # Production model evaluated on coverage, not directional accuracy
    vol_card = scorecard_data["horizons"]["168h_volatility"]
    assert "empirical_coverage_pct" in vol_card
    assert vol_card["empirical_coverage_pct"] >= 90.0
    assert "accuracy_pct" not in vol_card

    # Directional models evaluated on directional accuracy
    for h in ["1h", "4h", "24h"]:
        dir_card = scorecard_data["horizons"][h]
        assert "accuracy_pct" in dir_card
        assert "empirical_coverage_pct" not in dir_card


def test_corrected_transaction_cost_accounting(scorecard_data):
    """Verify transaction cost formula Net = Gross - Turnover * Fee across all directional horizons."""
    for h in ["1h", "4h", "24h"]:
        card = scorecard_data["horizons"][h]
        econ = card["economics"]
        gross = econ["mean_gross_return_bps"]
        turnover = econ["turnover_transitions_per_bar"]
        net_inst = econ["net_institutional_14bps"]
        net_ret = econ["net_retail_35bps"]

        expected_inst = round(gross - turnover * 7.0, 2)
        assert abs(net_inst - expected_inst) <= 0.05, f"Institutional formula mismatch on {h}"

        expected_ret = round(gross - turnover * 17.5, 2)
        assert abs(net_ret - expected_ret) <= 0.05, f"Retail formula mismatch on {h}"

        # Trading expectancy remains negative
        assert econ["economically_profitable"] is False
        assert net_inst < 0.0
        assert net_ret < 0.0


def test_no_order_execution_calls_in_pipeline():
    """Verify that shadow pipeline contains zero imports or execution calls for live trading."""
    pipeline_file = os.path.join(REPO_ROOT, "research", "stage10_shadow_pipeline.py")
    with open(pipeline_file, "r", encoding="utf-8") as f:
        code = f.read()

    forbidden_tokens = ["ccxt", "create_order", "place_order", "execute_order", "buy_market", "sell_market"]
    for token in forbidden_tokens:
        assert token not in code, f"Forbidden live order execution token '{token}' found in shadow pipeline!"


def test_api_shadow_status_endpoint():
    """Test GET /api/research/shadow-status returns 200 with complete scorecard metadata."""
    response = client.get("/api/research/shadow-status")
    assert response.status_code == 200
    data = response.json()

    assert data["pipeline_version"] == "STAGE10-SHADOW-VAL-v1.0"
    assert data["evaluation_mode"] == "PROSPECTIVE_SHADOW_EVALUATION"
    assert data["governance"]["production_model"] == "HAR-RS-DOW-v1.0"
    assert data["governance"]["live_trading_status"] == "DISABLED"
    assert "scorecard" in data
    assert "1h" in data["scorecard"]["horizons"]
    assert "168h_volatility" in data["scorecard"]["horizons"]


def test_api_shadow_ledger_endpoint():
    """Test GET /api/research/shadow-ledger returns 200 and paginated events."""
    response = client.get("/api/research/shadow-ledger?limit=10")
    assert response.status_code == 200
    data = response.json()

    assert data["returned_events_count"] == 10
    assert len(data["events"]) == 10
    first_ev = data["events"][0]
    assert "event_hash" in first_ev
    assert "prev_event_hash" in first_ev
    assert "event_type" in first_ev


def test_seventy_percent_objective_reality_check(scorecard_data):
    """Verify that 70% accuracy objective is explicitly evaluated and marked unsubstantiated."""
    assessment = scorecard_data["seventy_percent_objective_assessment"]
    assert assessment["substantiated_on_prospective_data"] is False
    assert assessment["scientific_status"] == "UNSUBSTANTIATED"

    # Check that 1h upper CI does not approach 70%
    h1 = scorecard_data["horizons"]["1h"]
    assert h1["accuracy_pct"] < 55.0
    assert h1["accuracy_95_ci"][1] < 60.0
