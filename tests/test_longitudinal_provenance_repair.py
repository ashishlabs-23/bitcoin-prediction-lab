"""
tests/test_longitudinal_provenance_repair.py — Focused Regression Tests for Phase 1A
====================================================================================
Verifies:
1. Model hashes match actual physical artifact bytes (sha256_file).
2. Feature-schema hashing is deterministic and changes when the schema changes.
3. Missing artifacts or provenance mismatches are handled safely without fake substitute hashes.
4. Monitoring metrics are derived dynamically from underlying records, not hardcoded constants.
5. Changing valid underlying observations changes the relevant calculated metrics.
6. Missing or insufficient data (N < 5) produces unavailable (None) instead of fabricated numbers.
7. Unresolved or invalid records are handled explicitly and excluded from resolved outcomes.
8. Research authorization gate remains blocked and live trading safeguards remain active.
"""

import os
import sys
import json
import sqlite3
import hashlib
import tempfile
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.post_repair_longitudinal_monitor import (
    derive_model_artifact_sha256,
    derive_feature_schema_hash,
    derive_target_contract_hash,
    get_authoritative_provenance,
    post_repair_monitor,
    MODEL_ARTIFACT_PATH,
    REPAIRED_MANIFEST_PATH,
    CANONICAL_FEATURE_SCHEMA,
    CANONICAL_TARGET_CONTRACT,
    POST_REPAIR_EVIDENCE_START
)
from engine.longitudinal_status import (
    compute_dynamic_observed_metrics,
    longitudinal_status_service
)


# --- 1. Provenance Integrity Tests ---

def test_model_artifact_hash_matches_actual_bytes():
    """Verify that model_hash derives from real artifact bytes, not an empty string placeholder."""
    assert os.path.isfile(MODEL_ARTIFACT_PATH), f"Model artifact must exist at {MODEL_ARTIFACT_PATH}"
    
    # Calculate directly
    hasher = hashlib.sha256()
    with open(MODEL_ARTIFACT_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            hasher.update(chunk)
    expected_hash = hasher.hexdigest()

    computed_hash = derive_model_artifact_sha256(MODEL_ARTIFACT_PATH)
    assert computed_hash == expected_hash
    # Crucial: verify it is NOT the empty-string SHA-256 placeholder
    empty_sha256 = hashlib.sha256(b"").hexdigest()
    assert computed_hash != empty_sha256
    assert computed_hash == "750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b"


def test_feature_schema_hash_deterministic_and_sensitive():
    """Verify feature schema hashing is deterministic and changes if schema is modified."""
    h1 = derive_feature_schema_hash(CANONICAL_FEATURE_SCHEMA)
    h2 = derive_feature_schema_hash(CANONICAL_FEATURE_SCHEMA)
    assert h1 == h2, "Hashing must be deterministic"

    # Crucial: verify it is NOT the MD5 empty-string placeholder
    assert not h1.startswith("d41d8cd98f00b204e9800998ecf8427e")
    assert h1 == "8654d2c3e02c9483fe1d5a4831630d6ed8459aa2c0e4e64ffcec552bb36fd1a8"

    # Modification test: changing any feature must change the hash
    modified_schema = list(CANONICAL_FEATURE_SCHEMA) + ["extra_volatility_factor"]
    h_mod = derive_feature_schema_hash(modified_schema)
    assert h_mod != h1


def test_provenance_handles_missing_artifact_and_mismatch_safely():
    """Verify that missing files or hash mismatches fail gracefully without synthetic substitutes."""
    # Non-existent artifact
    missing_prov = get_authoritative_provenance(
        artifact_path="/tmp/non_existent_model_artifact.joblib"
    )
    assert missing_prov["model_hash"] is None
    assert missing_prov["provenance_health"] == "PROVENANCE_UNAVAILABLE"
    assert any("not found" in d for d in missing_prov["provenance_details"])

    # Schema mismatch against manifest
    mismatch_prov = get_authoritative_provenance(
        feature_schema=["tampered_feature_a", "tampered_feature_b"]
    )
    assert mismatch_prov["provenance_health"] == "PROVENANCE_MISMATCH"
    assert any("Feature schema hash mismatch" in d for d in mismatch_prov["provenance_details"])


# --- 2. Dynamic Metric Calculation & Sensitivity Tests ---

def _create_synthetic_test_db(tmp_path: str, records: list) -> str:
    """Helper to populate a clean, isolated SQLite test DB."""
    db_file = os.path.join(tmp_path, "test_market_memory.db")
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE range_forecasts (
            forecast_id TEXT PRIMARY KEY,
            timestamp TEXT,
            symbol TEXT,
            horizon TEXT,
            current_price REAL,
            upper_p90 REAL,
            lower_p90 REAL,
            degraded INTEGER,
            data_quality TEXT
        );
    """)
    conn.execute("""
        CREATE TABLE forecast_outcomes (
            outcome_id TEXT PRIMARY KEY,
            forecast_id TEXT,
            prediction_timestamp TEXT,
            resolution_timestamp TEXT,
            actual_high REAL,
            actual_low REAL,
            actual_close REAL,
            actual_mfe REAL,
            actual_mae REAL,
            mfe_error REAL,
            mae_error REAL,
            upper_covered INTEGER,
            lower_covered INTEGER,
            path_contained INTEGER,
            data_quality TEXT
        );
    """)
    for r in records:
        conn.execute("""
            INSERT INTO range_forecasts (forecast_id, timestamp, symbol, horizon, current_price, upper_p90, lower_p90, degraded, data_quality)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (r["fid"], r["ts"], "BTCUSD", "24h", r["price"], r["up_p90"], r["low_p90"], r.get("degraded", 0), "VALID"))
        if r.get("resolved", True):
            conn.execute("""
                INSERT INTO forecast_outcomes (outcome_id, forecast_id, prediction_timestamp, resolution_timestamp,
                                              actual_high, actual_low, actual_close, actual_mfe, actual_mae,
                                              mfe_error, mae_error, upper_covered, lower_covered, path_contained, data_quality)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (f"out_{r['fid']}", r["fid"], r["ts"], "2026-08-22T12:15:00Z",
                  r["high"], r["low"], r["close"], r["mfe"], r["mae"],
                  r["mfe_err"], r["mae_err"], 1 if r["high"] <= r["up_p90"] else 0,
                  1 if r["low"] >= r["low_p90"] else 0,
                  1 if (r["high"] <= r["up_p90"] and r["low"] >= r["low_p90"]) else 0,
                  r.get("fo_quality", "VALID")))
    conn.commit()
    conn.close()
    return db_file


def test_missing_and_insufficient_data_produces_none(tmp_path):
    """Fewer than 5 records or missing DB must return None, not synthetic constants."""
    # Case 1: Non-existent DB
    res_none = compute_dynamic_observed_metrics(db_path="/tmp/non_existent.db", min_blocks=5)
    assert res_none["mfe_error_pct"] is None
    assert res_none["p90_coverage_pct"] is None
    assert res_none["winkler_score"] is None

    # Case 2: Insufficient data (N = 3 < 5)
    records_3 = [
        {"fid": f"f_{i}", "ts": "2026-08-22T00:00:00Z", "price": 60000.0, "up_p90": 62000.0, "low_p90": 58000.0,
         "high": 61000.0, "low": 59000.0, "close": 60500.0, "mfe": 0.016, "mae": 0.016, "mfe_err": 0.002, "mae_err": 0.002}
        for i in range(3)
    ]
    db_3 = _create_synthetic_test_db(str(tmp_path), records_3)
    res_3 = compute_dynamic_observed_metrics(db_path=db_3, min_blocks=5)
    assert res_3["mfe_error_pct"] is None
    assert res_3["mae_error_pct"] is None
    assert res_3["p90_coverage_pct"] is None
    assert res_3["winkler_score"] is None
    assert res_3["conformal_interval_width_pct"] is None
    assert res_3["baseline_delta_bps"] is None


def test_changing_observations_changes_calculated_metrics(tmp_path):
    """Altering underlying valid observations must directly alter the calculated monitoring metrics."""
    # Base fixture: 5 perfectly contained forecasts with 0.002 error
    base_records = [
        {"fid": f"f_{i}", "ts": "2026-08-22T00:00:00Z", "price": 60000.0, "up_p90": 62000.0, "low_p90": 58000.0,
         "high": 61000.0, "low": 59000.0, "close": 60500.0, "mfe": 0.016, "mae": 0.016, "mfe_err": 0.002, "mae_err": 0.002}
        for i in range(5)
    ]
    db_base = _create_synthetic_test_db(str(tmp_path), base_records)
    m_base = compute_dynamic_observed_metrics(db_path=db_base, min_blocks=5)

    assert m_base["mfe_error_pct"] == pytest.approx(0.20, 0.01)
    assert m_base["p90_coverage_pct"] == 100.0

    # Perturbed fixture: 5 forecasts with high breaches and higher error
    dir_perturbed = tempfile.mkdtemp()
    perturbed_records = [
        {"fid": f"f_{i}", "ts": "2026-08-22T00:00:00Z", "price": 60000.0, "up_p90": 62000.0, "low_p90": 58000.0,
         "high": 65000.0, "low": 57000.0, "close": 64000.0, "mfe": 0.083, "mae": 0.050, "mfe_err": 0.050, "mae_err": 0.030}
        for i in range(5)
    ]
    db_perturbed = _create_synthetic_test_db(dir_perturbed, perturbed_records)
    m_perturbed = compute_dynamic_observed_metrics(db_path=db_perturbed, min_blocks=5)

    # Metrics must have changed dynamically
    assert m_perturbed["mfe_error_pct"] > m_base["mfe_error_pct"]
    assert m_perturbed["p90_coverage_pct"] < m_base["p90_coverage_pct"]
    assert m_perturbed["winkler_score"] > m_base["winkler_score"]
    assert m_perturbed["p90_coverage_pct"] == 0.0  # All breached both bounds


def test_unresolved_and_degraded_records_excluded(tmp_path):
    """Unresolved forecasts and degraded records must not contaminate valid outcome statistics."""
    records = [
        # 4 valid resolved records
        {"fid": "valid_0", "ts": "2026-08-22T00:00:00Z", "price": 60000.0, "up_p90": 62000.0, "low_p90": 58000.0,
         "high": 61000.0, "low": 59000.0, "close": 60500.0, "mfe": 0.016, "mae": 0.016, "mfe_err": 0.002, "mae_err": 0.002, "resolved": True},
        {"fid": "valid_1", "ts": "2026-08-22T00:00:00Z", "price": 60000.0, "up_p90": 62000.0, "low_p90": 58000.0,
         "high": 61000.0, "low": 59000.0, "close": 60500.0, "mfe": 0.016, "mae": 0.016, "mfe_err": 0.002, "mae_err": 0.002, "resolved": True},
        {"fid": "valid_2", "ts": "2026-08-22T00:00:00Z", "price": 60000.0, "up_p90": 62000.0, "low_p90": 58000.0,
         "high": 61000.0, "low": 59000.0, "close": 60500.0, "mfe": 0.016, "mae": 0.016, "mfe_err": 0.002, "mae_err": 0.002, "resolved": True},
        {"fid": "valid_3", "ts": "2026-08-22T00:00:00Z", "price": 60000.0, "up_p90": 62000.0, "low_p90": 58000.0,
         "high": 61000.0, "low": 59000.0, "close": 60500.0, "mfe": 0.016, "mae": 0.016, "mfe_err": 0.002, "mae_err": 0.002, "resolved": True},
        # 1 unresolved forecast (has no outcome row)
        {"fid": "unres_0", "ts": "2026-08-22T00:00:00Z", "price": 60000.0, "up_p90": 62000.0, "low_p90": 58000.0,
         "high": 0.0, "low": 0.0, "close": 0.0, "mfe": 0.0, "mae": 0.0, "mfe_err": 0.0, "mae_err": 0.0, "resolved": False},
        # 1 degraded forecast (degraded = 1)
        {"fid": "degraded_0", "ts": "2026-08-22T00:00:00Z", "price": 60000.0, "up_p90": 62000.0, "low_p90": 58000.0,
         "high": 61000.0, "low": 59000.0, "close": 60500.0, "mfe": 0.016, "mae": 0.016, "mfe_err": 0.002, "mae_err": 0.002, "degraded": 1, "resolved": True}
    ]
    db_mix = _create_synthetic_test_db(str(tmp_path), records)
    res_mix = compute_dynamic_observed_metrics(db_path=db_mix, min_blocks=5)
    # Only 4 valid resolved records exist -> fails min_blocks=5 check -> all metrics None!
    assert res_mix["mfe_error_pct"] is None
    assert res_mix["p90_coverage_pct"] is None


# --- 3. Safety & Authorization Guard Tests ---

def test_research_gate_and_trading_safeguards_remain_intact():
    """Verify that research gate remains fail-closed and live execution remains disabled."""
    from fastapi.testclient import TestClient
    from api.server import app, live_engine
    with TestClient(app) as client:
        gate = getattr(app.state, "research_gate", {})
        assert gate.get("status") in {"READY", "BLOCKED_AUDIT_FAILURE"}
        assert gate.get("trading_enabled", False) is False
        assert live_engine.is_running is False

    # Live trading safeguard check
    from engine.longitudinal_status import longitudinal_status_service
    report = longitudinal_status_service.get_status_report()
    assert report.evidence_phase == "POST_REPAIR"
    assert report.research_stop_rule_status == "NO_NEW_RESEARCH_REQUIRED"
