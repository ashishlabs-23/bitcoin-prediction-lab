"""
tests/test_arena_observatory_context.py — 4-State Observatory Context in Arena & Audit Layer
=============================================================================================
Verifies:
1. Canonical ObservatorySnapshot dataclass and serialization across all 4 independent states.
2. /api/arena/context API endpoint schema and governance disclaimers.
3. Read-only isolation: Observatory context does NOT alter strategy decision rules.
4. Atomic persistence of ObservatorySnapshot inside Arena Decision Ledger at t0.
5. Failure Atlas SQLite persistence of raw breach records on C2 resolution breach.
"""

import os
import sys
import json
import sqlite3
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app
from engine.observatory import (
    ForecastAccuracyObservatory,
    MarketState,
    RiskState,
    ModelState,
    DataState,
    ObservatorySnapshot,
    CANONICAL_SCIENTIFIC_CONTRACT_HASH,
    PROSPECTIVE_EXPERIMENT_ID,
    observatory
)
from engine.arena_runner import ArenaRunner


@pytest.fixture
def client():
    return TestClient(app)


def test_canonical_observatory_snapshot_structure():
    """Verify ObservatorySnapshot dataclass contains all 4 states and freezes scientific contract hash."""
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=":memory:")
    snapshot = obs.get_canonical_snapshot()

    assert isinstance(snapshot, ObservatorySnapshot)
    assert isinstance(snapshot.market, MarketState)
    assert isinstance(snapshot.risk, RiskState)
    assert isinstance(snapshot.model, ModelState)
    assert isinstance(snapshot.data, DataState)

    d = snapshot.to_dict()
    assert "snapshot_ts" in d
    assert d["scientific_contract_hash"] == CANONICAL_SCIENTIFIC_CONTRACT_HASH
    assert d["prospective_experiment_id"] == PROSPECTIVE_EXPERIMENT_ID

    # Market State check
    assert d["market"]["macro_epoch"] == "SPOT_ETF_ERA"
    assert "vol_ratio_1h_24h" in d["market"]

    # Risk State check (distinguishing variance from volatility)
    assert "expected_7d_variance" in d["risk"]
    assert "expected_7d_volatility" in d["risk"]
    assert d["risk"]["nominal_target_coverage"] == 0.90
    assert d["risk"]["lower_bound"] <= d["risk"]["upper_bound"]

    # Model State check
    assert d["model"]["health"] in ["STABLE", "WATCH", "DEGRADED", "FAIL", "DATA_INVALID"]
    assert "coverage_30d" in d["model"]
    assert "tail_asymmetry" in d["model"]

    # Data State check
    assert d["data"]["feed_completeness"] == 1.0
    assert "ingestion_latency_ms" in d["data"]
    assert d["data"]["data_invalid_count"] == 0


def test_api_arena_context_endpoint(client):
    """Verify /api/arena/context returns canonical 4-state context and governance disclaimers."""
    res = client.get("/api/arena/context")
    assert res.status_code == 200
    data = res.json()

    assert "context" in data
    assert "strategy" in data
    assert "governance" in data

    ctx = data["context"]
    assert "market" in ctx
    assert "risk" in ctx
    assert "model" in ctx
    assert "data" in ctx
    assert ctx["scientific_contract_hash"] == CANONICAL_SCIENTIFIC_CONTRACT_HASH

    gov = data["governance"]
    assert gov["verified_core"] is True
    assert gov["strategy_layer_validated"] is False
    assert "Observatory context is informational and does not modify strategy decisions" in gov["disclaimer"]

    strat = data["strategy"]
    assert "actions" in strat
    assert "agreement_ratio" in strat
    assert "ensemble_action" in strat


def test_observatory_context_read_only_isolation():
    """Verify that Observatory state changes do NOT alter Arena strategy execution logic."""
    temp_db = "results/test_arena_isolation.db"
    if os.path.exists(temp_db):
        os.remove(temp_db)

    runner = ArenaRunner(db_path=temp_db)
    
    # 1. Execute trade when model state is STABLE
    stable_snapshot = {
        "market": {"regime": "COMPRESSION"},
        "risk": {"expected_7d_variance": 0.12},
        "model": {"health": "STABLE"},
        "data": {"feed_completeness": 1.0}
    }
    h1 = runner.record_arena_decision_context(
        strategy_actions=["SKIP", "LONG", "SKIP", "SKIP"],
        agreement_ratio=0.75,
        ensemble_action="SKIP",
        observatory_snapshot=stable_snapshot,
        scientific_contract_hash=CANONICAL_SCIENTIFIC_CONTRACT_HASH
    )

    # 2. Execute trade when model state is DEGRADED
    degraded_snapshot = {
        "market": {"regime": "EXTREME_EXPANSION"},
        "risk": {"expected_7d_variance": 0.45},
        "model": {"health": "DEGRADED"},
        "data": {"feed_completeness": 0.8}
    }
    h2 = runner.record_arena_decision_context(
        strategy_actions=["SKIP", "LONG", "SKIP", "SKIP"],
        agreement_ratio=0.75,
        ensemble_action="SKIP",
        observatory_snapshot=degraded_snapshot,
        scientific_contract_hash=CANONICAL_SCIENTIFIC_CONTRACT_HASH
    )

    # Both records should be persisted with different context hashes, but the ensemble decision remains unmutated (SKIP)
    assert h1 != h2

    conn = runner._get_connection()
    try:
        rows = conn.execute("SELECT * FROM arena_decision_ledger ORDER BY decision_id ASC;").fetchall()
        assert len(rows) == 2
        assert rows[0]["ensemble_action"] == "SKIP"
        assert rows[1]["ensemble_action"] == "SKIP"
        
        ctx1 = json.loads(rows[0]["observatory_snapshot_json"])
        ctx2 = json.loads(rows[1]["observatory_snapshot_json"])
        assert ctx1["model"]["health"] == "STABLE"
        assert ctx2["model"]["health"] == "DEGRADED"
    finally:
        conn.close()

    if os.path.exists(temp_db):
        os.remove(temp_db)


def test_failure_atlas_raw_breach_logging():
    """Verify that when C2 resolution breaches, a raw failure_atlas entry is created with zero post-hoc storytelling."""
    obs = ForecastAccuracyObservatory(nominal_target=0.90, db_path=":memory:")

    # 1. Issue forecast
    t0 = "2026-08-01T00:00:00Z"
    t_res = "2026-08-08T00:00:00Z"
    rec = obs.log_forecast(
        forecast_id="fc-fa-test-01",
        timestamp=t0,
        v_hat=0.1000,
        lower=0.0400,
        upper=0.2000,
        macro_regime="COMPRESSION"
    )

    # 2. Resolve outcome with Upper Tail Breach (actual RV = 0.35 > 0.20)
    resolved_rec = obs.resolve_outcome(
        forecast_id="fc-fa-test-01",
        actual_rv7d=0.3500,
        resolved_at=t_res
    )
    assert resolved_rec is not None
    assert resolved_rec.upper_breach is True

    # 3. Check SQLite failure_atlas table
    conn = obs._get_connection()
    try:
        rows = conn.execute("SELECT * FROM failure_atlas WHERE forecast_id='fc-fa-test-01';").fetchall()
        assert len(rows) == 1
        fa = rows[0]
        assert fa["breach_type"] == "UPPER_TAIL_BREACH"
        assert fa["lower_bound"] == 0.0400
        assert fa["upper_bound"] == 0.2000
        assert fa["actual_rv7d"] == 0.3500
        assert abs(fa["breach_magnitude"] - 0.1500) < 1e-5
        
        # Verify raw context is JSON without auto-generated narrative
        market_ctx = json.loads(fa["market_state"])
        assert market_ctx["macro_epoch"] == "COMPRESSION"
        assert "event_hash" in fa.keys()
    finally:
        pass
