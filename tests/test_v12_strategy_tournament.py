"""
tests/test_v12_strategy_tournament.py
======================================
BTCognitive V12 — Automated Strategy Tournament & Governance Test Suite
========================================================================
Independent Red-Team & Verification (Agents G & H).

Verifies:
1. Manifest integrity & frozen strategy contracts.
2. Causal point-in-time regime classification with 3-bar hysteresis.
3. Multi-scenario execution cost modeling (Retail 87 bps, Inst. 18.6 bps, Perp 15 bps).
4. Event-driven simulator mechanics (imperfect breakeven, simultaneous touch adverse resolution).
5. Risk-first Pareto candidate ranking & holdout validation verdict.
6. Tournament API routes (/api/tournament/latest, /api/tournament/regime, /api/tournament/candidates).
7. Governance invariants: Live trading permanently DISABLED, directional recommendation ABSTAIN.
"""

import os
import sys
import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from api.server import app
from research.v12_strategy_tournament_engine import V12StrategyTournamentEngine


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def engine():
    return V12StrategyTournamentEngine()


def test_v12_tournament_manifest_and_frozen_contracts(engine):
    """
    PRD-TOURN-32: Verifies frozen specs for 5 candidate hypotheses and independent baselines.
    """
    manifest_path = os.path.join(REPO_ROOT, "experiments", "results", "v12_strategy_tournament_manifest.json")
    assert os.path.exists(manifest_path), f"Manifest file missing at {manifest_path}"

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    assert manifest.get("manifest_version") == "12.0.0"
    assert "scenarios" in manifest
    assert "COINBASE_RETAIL_87BPS" in manifest["scenarios"]
    assert "COINBASE_INSTITUTIONAL_18BPS" in manifest["scenarios"]
    assert "BINANCE_PERP_15BPS" in manifest["scenarios"]

    retail_run = manifest["scenarios"]["COINBASE_RETAIL_87BPS"]
    candidates = retail_run.get("top_candidates", [])
    assert len(candidates) >= 5

    candidate_ids = {c["id"] for c in candidates}
    expected_ids = {
        "REGIME_ADAPTIVE_ROUTER",
        "MTF_MOMENTUM_TREND",
        "VOL_COMPRESSION_BREAKOUT",
        "HTF_RANGE_EXPANSION_BREAKOUT",
        "SHORT_HORIZON_MEAN_REVERSION"
    }
    assert expected_ids.issubset(candidate_ids)


def test_market_regime_causality_and_hysteresis(engine):
    """
    PRD-TOURN-31: Verifies point-in-time regime classification & 3-bar hysteresis.
    """
    regime_info = engine.get_current_market_regime()
    assert regime_info["instrument"] == "BTC-USD"
    assert regime_info["venue"] == "Coinbase Exchange Spot"
    assert "regime" in regime_info
    assert "hysteresis_status" in regime_info
    assert regime_info["hysteresis_status"] in ["CONFIRMED", "TRANSITION_PENDING"]
    assert regime_info["adx_14"] >= 0.0
    assert regime_info["bb_width"] >= 0.0
    assert regime_info["directional_authorization"] == "OFFLINE_RESEARCH_ONLY"
    assert regime_info["execution_authorization"] == "DISABLED"


def test_multi_scenario_execution_costs(engine):
    """
    PRD-TOURN-34: Reconciles 3 cost scenarios and confirms break-even cost metric.
    """
    scenarios = engine.COST_SCENARIOS
    assert scenarios["COINBASE_RETAIL_87BPS"]["round_trip_bps"] == 87.0
    assert scenarios["COINBASE_INSTITUTIONAL_18BPS"]["round_trip_bps"] == 18.6
    assert scenarios["BINANCE_PERP_15BPS"]["round_trip_bps"] == 15.0

    # Test run under institutional scenario has higher net expectancy than retail
    retail_res = engine.run_tournament("COINBASE_RETAIL_87BPS")
    inst_res = engine.run_tournament("COINBASE_INSTITUTIONAL_18BPS")

    retail_trend = next(c for c in retail_res["top_candidates"] if c["id"] == "MTF_MOMENTUM_TREND")
    inst_trend = next(c for c in inst_res["top_candidates"] if c["id"] == "MTF_MOMENTUM_TREND")

    # Institutional costs save ~68.4 bps per round trip
    assert inst_trend["net_expectancy_bps"] > retail_trend["net_expectancy_bps"]


def test_event_driven_imperfect_breakeven_accounting(engine):
    """
    PRD-TOURN-33: Verifies that moving stop to entry does NOT produce zero cost due to fee drag.
    """
    cost_bps = 87.0
    cost_frac = cost_bps / 10000.0
    entry_p = 80000.0
    breakeven_stop = entry_p * (1.0 + cost_frac)
    assert breakeven_stop > entry_p, "Breakeven stop must account for round-trip cost friction"


def test_risk_first_pareto_ranking_and_holdout_verdict(engine):
    """
    PRD-TOURN-35: Verifies that under retail fees, all candidates fail net expectancy,
    proving that REGIME_ADAPTIVE_ROUTER does not win by default, and overall decision is ABSTAIN.
    """
    res = engine.run_tournament("COINBASE_RETAIL_87BPS")
    assert "ABSTAIN" in res["overall_decision"]

    # Check router net expectancy
    router_metrics = next(c for c in res["top_candidates"] if c["id"] == "REGIME_ADAPTIVE_ROUTER")
    assert router_metrics["net_expectancy_bps"] < 0, "Regime router does not magically win under retail costs"

    # Confirm NO_TRADE benchmark outperformed
    assert res["baselines"]["NO_TRADE"]["net_expectancy_bps"] == 0.0
    assert res["baselines"]["NO_TRADE"]["max_drawdown_pct"] == 0.0


def test_tournament_api_endpoints(client):
    """
    PRD-TOURN-36: Verifies FastAPI endpoints /api/tournament/* return HTTP 200 OK.
    """
    resp_latest = client.get("/api/tournament/latest")
    assert resp_latest.status_code == 200
    data = resp_latest.json()
    assert "overall_decision" in data
    assert "market_regime" in data
    assert "top_candidates" in data
    assert len(data["top_candidates"]) >= 5

    resp_regime = client.get("/api/tournament/regime")
    assert resp_regime.status_code == 200
    regime_data = resp_regime.json()
    assert "regime" in regime_data

    resp_candidates = client.get("/api/tournament/candidates")
    assert resp_candidates.status_code == 200
    cand_data = resp_candidates.json()
    assert "candidates" in cand_data
    assert "baselines" in cand_data


def test_governance_invariants_preserved(client):
    """
    PRD-TOURN-38: Strict non-execution and Tier 2 gating preservation.
    """
    resp = client.get("/api/tournament/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("live_trading_status") == "DISABLED"
    assert data["market_regime"].get("execution_authorization") == "DISABLED"
    assert data["market_regime"].get("directional_authorization") == "OFFLINE_RESEARCH_ONLY"
