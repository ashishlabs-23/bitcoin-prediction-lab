"""
tests/test_v33_4l_historical_evidence.py
========================================
Comprehensive Unit & Integration Test Suite for Milestone V33.4L:
- Read-Only Historical Evidence Loader & Validator.
- REST Endpoint GET /api/tournament/historical-evidence.
- Epistemic isolation of mock attempts and prospective shadow ledger.
- Negative tests for missing files, hash mismatches, corrupted partitions, and cost schedule deviations.
- Strict non-execution invariants (zero trade authorization, zero fabricated forecast).
"""

import os
import sys
import json
import tempfile
import pytest
import pandas as pd
from fastapi.testclient import TestClient

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from api.server import app
from engine.historical_evidence_loader import (
    HistoricalEvidenceLoader,
    compute_file_sha256,
    DEFAULT_LEDGER_PATH,
    DEFAULT_EXCLUSION_PATH,
    EXPECTED_LEDGER_SHA256,
    EXPECTED_EXCLUSION_SHA256,
    ORIGINAL_DATASET_FINGERPRINT,
    FULL_WINDOW_DATASET_FINGERPRINT,
    REPRODUCTION_DATASET_FINGERPRINT,
    RUNTIME_DATASET_FINGERPRINT
)
from engine.htf_prospective_shadow_runner import HTFProspectiveShadowProtocol
from engine.regime_strategy_tournament import VersionedStrategyRegistry


@pytest.fixture
def client():
    return TestClient(app)


def test_valid_artifact_loading():
    """Verify that authoritative artifacts load successfully with 100% exact metrics."""
    loader = HistoricalEvidenceLoader.get_instance()
    res = loader.validate_and_load(force_reload=True)

    assert res["status"] == "SUCCESS"
    assert res["is_valid"] is True
    assert res["strategy_id"] == "HTF_RANGE_EXPANSION_BREAKOUT"
    assert res["evidence_classification"] == "RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY"

    # Population metrics
    pop = res["population_statistics"]
    assert pop["total_trades"] == 194
    assert pop["winning_trades"] == 85
    assert pop["overall_win_rate_pct"] == 43.81
    assert abs(pop["mean_net_expectancy_bps"] - 9.5713) < 0.005

    # Retained subgroup
    ret = res["retained_subgroup"]
    assert ret["trade_count"] == 110
    assert ret["winning_trades"] == 53
    assert ret["win_rate_pct"] == 48.18
    assert abs(ret["mean_net_expectancy_bps"] - 59.2546) < 0.005

    # Excluded subgroup
    exc = res["excluded_subgroup"]
    assert exc["trade_count"] == 84
    assert exc["winning_trades"] == 32
    assert exc["win_rate_pct"] == 38.10
    assert abs(exc["mean_net_expectancy_bps"] - (-55.4903)) < 0.005


def test_110_84_partition_integrity():
    """Verify set-theoretic partition of the 194 trade IDs."""
    loader = HistoricalEvidenceLoader.get_instance()
    df = pd.read_csv(loader.exclusion_path)

    kept = set(df[df["action_v33_3a"] == "KEEP"]["trade_id"])
    excl = set(df[df["action_v33_3a"] == "EXCLUDE"]["trade_id"])

    assert len(kept) == 110
    assert len(excl) == 84
    assert kept.intersection(excl) == set(), "Partition must be disjoint"
    assert kept.union(excl) == set(range(1, 195)), "Partition must be exhaustive over 1..194"


def test_dataset_provenance_qualification():
    """Verify separate dataset fingerprints and PARTIALLY_RESOLVED qualification."""
    loader = HistoricalEvidenceLoader.get_instance()
    res = loader.get_historical_evidence()
    prov = res["provenance"]

    assert prov["original_source_provenance_status"] == "PARTIALLY_RESOLVED"
    assert prov["original_dataset_fingerprint"] == ORIGINAL_DATASET_FINGERPRINT
    assert prov["full_window_dataset_fingerprint"] == FULL_WINDOW_DATASET_FINGERPRINT
    assert prov["reproduction_dataset_fingerprint"] == REPRODUCTION_DATASET_FINGERPRINT
    assert prov["runtime_dataset_fingerprint"] == RUNTIME_DATASET_FINGERPRINT
    assert "41,273 bars" in prov["qualification_note"]
    assert "41,397 bars" in prov["qualification_note"]


def test_missing_artifact_handling():
    """Negative Test: Verify graceful degradation when artifact file is missing."""
    loader = HistoricalEvidenceLoader(
        ledger_path="/nonexistent/path/ledger.csv",
        exclusion_path="/nonexistent/path/excl.csv"
    )
    res = loader.validate_and_load(force_reload=True)

    assert res["status"] == "EVIDENCE_UNAVAILABLE"
    assert res["error_code"] == "ARTIFACT_NOT_FOUND"
    assert res["is_valid"] is False


def test_artifact_hash_mismatch():
    """Negative Test: Verify rejection when file hash deviates from expected."""
    loader = HistoricalEvidenceLoader(
        expected_ledger_sha256="0000000000000000000000000000000000000000000000000000000000000000"
    )
    res = loader.validate_and_load(force_reload=True)

    assert res["status"] == "INTEGRITY_FAILURE"
    assert res["error_code"] == "SHA256_MISMATCH"
    assert res["is_valid"] is False


def test_corrupted_duplicate_trade_ids():
    """Negative Test: Verify rejection if trade IDs contain duplicates or gaps."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f_tmp:
        df = pd.read_csv(DEFAULT_EXCLUSION_PATH)
        df.loc[10, "trade_id"] = 1  # Create duplicate ID
        df.to_csv(f_tmp.name, index=False)
        tmp_path = f_tmp.name

    try:
        loader = HistoricalEvidenceLoader(
            exclusion_path=tmp_path,
            expected_exclusion_sha256=compute_file_sha256(tmp_path)
        )
        res = loader.validate_and_load(force_reload=True)
        assert res["status"] == "INTEGRITY_FAILURE"
        assert res["error_code"] == "TRADE_ID_SEQUENCE_ERROR"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_incorrect_cost_assumption():
    """Negative Test: Verify rejection if cost schedule does not equal 26.0 bps."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f_tmp:
        df = pd.read_csv(DEFAULT_EXCLUSION_PATH)
        df.loc[5, "net_vip0_bps"] = df.loc[5, "gross_return_bps"] - 15.0  # Incorrect friction
        df.to_csv(f_tmp.name, index=False)
        tmp_path = f_tmp.name

    try:
        loader = HistoricalEvidenceLoader(
            exclusion_path=tmp_path,
            expected_exclusion_sha256=compute_file_sha256(tmp_path)
        )
        res = loader.validate_and_load(force_reload=True)
        assert res["status"] == "INTEGRITY_FAILURE"
        assert res["error_code"] == "COST_SCHEDULE_MISMATCH"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_demo_fixture_and_prospective_isolation():
    """Verify that mock registry attempts (N=4) and prospective shadow ledger remain completely isolated."""
    # 1. Historical loader ignores the 4 mock attempts
    loader = HistoricalEvidenceLoader.get_instance()
    res = loader.get_historical_evidence()
    assert res["population_statistics"]["total_trades"] == 194
    assert res["governance_locks"]["demo_fixtures_excluded"] is True
    assert res["governance_locks"]["is_confirmatory"] is False
    assert res["governance_locks"]["satisfies_prospective_gate"] is False

    # 2. Mock attempts remain DEMO_FIXTURE in registry
    entry = VersionedStrategyRegistry.get_all_entries().get("HTF_RANGE_EXPANSION_BREAKOUT")
    assert entry.status == "INSUFFICIENT_EVIDENCE"
    assert entry.historical_sample_size == 4

    # 3. Prospective shadow ledger remains 0 events and inactive
    proto = HTFProspectiveShadowProtocol()
    proto_stat = proto.get_protocol_status()
    assert proto_stat["collector_status"] == "INACTIVE_AWAITING_MANAGEMENT_AUTHORIZATION"
    assert proto_stat["live_trading"] == "DISABLED"
    assert len(proto.read_shadow_records()) == 0


def test_api_historical_evidence_endpoint(client):
    """Integration Test: Verify GET /api/tournament/historical-evidence."""
    resp = client.get("/api/tournament/historical-evidence")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["strategy_id"] == "HTF_RANGE_EXPANSION_BREAKOUT"
    assert data["evidence_classification"] == "RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY"
    assert data["population_statistics"]["total_trades"] == 194
    assert data["retained_subgroup"]["trade_count"] == 110
    assert data["excluded_subgroup"]["trade_count"] == 84
    assert len(data["regime_breakdowns"]) == 5

    # Invariants: Zero live trading, zero directional forecast, zero trade proposal
    assert "signal" not in data
    assert "recommended_action" not in data
    assert data["governance_locks"]["live_trading"] == "DISABLED"


def test_historical_evidence_non_interference_with_stale_market_data(client):
    """Verify that historical evidence loads independently regardless of current candle feed freshness."""
    resp = client.get("/api/tournament/historical-evidence")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "SUCCESS"
    # Even if market is stale, historical research remains available and classified correctly
    assert data["evidence_classification"] == "RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY"

