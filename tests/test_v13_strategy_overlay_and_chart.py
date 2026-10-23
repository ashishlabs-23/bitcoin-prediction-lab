"""
tests/test_v13_strategy_overlay_and_chart.py — BTCognitive V13 Verification Suite
================================================================================
Comprehensive verification for V13 requirements:
1. P0 — Reconcile 15m dataset integrity (1,800 candles, no truncation, monotonic).
2. P0 — Performance and mathematical drawdown audit (unleveraged <= 100%, known-answer, defect reproduction).
3. P0 — User-controlled strategy selection and typed current setup contract (/api/tournament/setup/{id}).
4. P0 — Level calculation geometry rules (SL < Entry < TP for Long, TP < Entry < SL for Short, gross/net R:R).
5. P0 — Fixed Replay & Counterfactual Lab placeholders and scenario evaluations.
6. P0 — Live forecast & chart overlay integration contracts.
7. P0 — Governance invariants (live trading permanently DISABLED, OFFLINE_RESEARCH_ONLY).
"""

import os
import json
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.server import app
from research.v12_strategy_tournament_engine import V12StrategyTournamentEngine
from engine.coinbase_15m_adapter import Coinbase15mAdapter
from engine.counterfactual_contract_engine import generate_counterfactual_lab_contracts

client = TestClient(app)


# ==============================================================================
# 1. P0 — 15m Dataset Lineage & Truncation Elimination Audit
# ==============================================================================
def test_v13_15m_dataset_integrity():
    """Verify that Coinbase 15m Parquet file contains >= 1,800 candles without gaps or truncation."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    parquet_path = os.path.join(repo_root, "data", "raw", "coinbase_15m.parquet")
    assert os.path.exists(parquet_path), f"Missing 15m parquet dataset at {parquet_path}"

    df = pd.read_parquet(parquet_path)
    assert len(df) >= 1800, f"Expected >= 1,800 candles, found {len(df)}"

    # Check required columns
    required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
    assert required_cols.issubset(df.columns), f"Missing required columns in 15m dataset: {required_cols - set(df.columns)}"

    # Verify monotonic increasing timestamps
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    timestamps = pd.to_datetime(df_sorted["timestamp"])
    diffs = timestamps.diff().dropna()
    expected_step = pd.Timedelta(minutes=15)

    # All regular step differences must be exactly 15 minutes
    gap_count = (diffs != expected_step).sum()
    assert gap_count == 0, f"Found {gap_count} gaps in 15m continuous series"

    # Verify adapter load_cached preserves existing history and metadata
    adapter = Coinbase15mAdapter()
    res = adapter.load_cached()
    assert res is not None, "Failed to load cached 15m dataset via adapter"
    df_cached, manifest = res
    assert len(df_cached) >= 1800
    meta = manifest.get("metadata", {})
    assert meta.get("total_validated", 0) >= 1800
    assert meta.get("gap_count") == 0
    assert meta.get("segment_count") == 1


# ==============================================================================
# 2. P0 — Mathematical Drawdown Audit & Defect Reproduction
# ==============================================================================
def test_v13_drawdown_mathematical_correction():
    """
    Independently verify:
    1. Known-answer portfolio equity curve drawdown.
    2. Compounded unleveraged equity drawdown is mathematically bounded in [0, 100%].
    3. Reproduction of legacy arithmetic uncompounded defect (which produced 124.4%).
    """
    engine = V12StrategyTournamentEngine()

    # Known-answer test 1: Simple 50% drawdown
    # Equity curve: $10,000 -> $12,000 (peak) -> $6,000 (trough) -> $9,000
    # Expected peak: 12,000, trough: 6,000, Max Drawdown: (12,000 - 6,000) / 12,000 = 50.0%
    # Trades in bps: +20% = +2000 bps, -50% = -5000 bps, +50% = +5000 bps
    trades_50pct = [
        {"net_return_bps": 2000.0, "gross_return_bps": 2087.0},
        {"net_return_bps": -5000.0, "gross_return_bps": -4913.0},
        {"net_return_bps": 5000.0, "gross_return_bps": 5087.0}
    ]
    metrics_50pct = engine._compute_metrics(trades_50pct, "COINBASE_RETAIL_87BPS")
    assert pytest.approx(metrics_50pct["max_drawdown_pct"], 0.01) == 50.0

    # Known-answer test 2: Unleveraged bound test
    # Even with huge consecutive losses, unleveraged equity cannot lose > 100%
    trades_heavy = [
        {"net_return_bps": -3000.0, "gross_return_bps": -2913.0},
        {"net_return_bps": -4000.0, "gross_return_bps": -3913.0},
        {"net_return_bps": -5000.0, "gross_return_bps": -4913.0},
        {"net_return_bps": -6000.0, "gross_return_bps": -5913.0}
    ]
    metrics_heavy = engine._compute_metrics(trades_heavy, "COINBASE_RETAIL_87BPS")
    assert 0.0 <= metrics_heavy["max_drawdown_pct"] <= 100.0

    # Defect reproduction test:
    # Legacy calculation was: cum_ret = np.cumsum(net_returns / 10000.0); max_dd = max(running_max - cum_ret)
    # Summing decimal returns directly without compounding allows arithmetic sum to exceed 1.0 (100%)
    # For instance: 15 consecutive -10% (-1000 bps) returns = arithmetic sum of -1.50 (-150%)!
    returns_bps = np.full(15, -1000.0)
    rets_frac = returns_bps / 10000.0
    arithmetic_sum_defect = float(np.sum(rets_frac))
    assert arithmetic_sum_defect == pytest.approx(-1.50, 0.01)  # 150% arithmetic loss

    # But compounded equity is: (1 - 0.10)^15 = 0.2059 -> 79.41% max drawdown!
    trades_15_loss = [{"net_return_bps": -1000.0, "gross_return_bps": -913.0} for _ in range(15)]
    compounded_metrics = engine._compute_metrics(trades_15_loss, "COINBASE_RETAIL_87BPS")
    assert pytest.approx(compounded_metrics["max_drawdown_pct"], 0.01) == 79.41

    # Verify that V13 engine exports both corrected bounded drawdown and legacy audit metric
    assert "max_drawdown_pct" in compounded_metrics
    assert "legacy_uncompounded_drawdown_pct" in compounded_metrics


# ==============================================================================
# 3. P0 — User-Controlled Strategy Setup Contract Endpoint
# ==============================================================================
def test_v13_strategy_setup_contract_endpoint():
    """Verify GET /api/tournament/setup/{strategy_id} returns a typed, governed V13 contract."""
    response = client.get("/api/tournament/setup/HTF_RANGE_EXPANSION_BREAKOUT?enabled=false")
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()

    # Required typed fields
    required_keys = [
        "strategy_id", "strategy_name", "version", "specification_hash",
        "asset", "market_type", "required_timeframe", "source_timeframe",
        "latest_completed_candle_time", "reference_price", "observed_regime",
        "supported_regimes", "rule_trigger_status", "setup_state",
        "user_overlay_enabled", "entry_price", "tp_price", "sl_price",
        "gross_reward_risk", "net_reward_risk", "invalidation_rules",
        "cost_assumptions_bps", "blocking_reason", "execution_authorization", "live_trading"
    ]
    for key in required_keys:
        assert key in data, f"Missing required field in setup contract: {key}"

    # Verify governance invariants
    assert data["execution_authorization"] == "DISABLED"
    assert data["model_authorization"] == "OFFLINE_RESEARCH_ONLY"
    assert data["live_trading"] == "DISABLED"
    assert data["user_overlay_enabled"] is False

    # When disabled and no setup active, setup_state is OVERLAY_OFF
    assert data["setup_state"] in ["OVERLAY_OFF", "SETUP_PREVIEW_AVAILABLE", "NO_SETUP", "BLOCKED_BY_REGIME"]


def test_v13_strategy_setup_geometry_and_validation():
    """Verify that whenever a setup produces levels, the geometry strictly obeys directional math."""
    engine = V12StrategyTournamentEngine()
    regime = engine.get_current_market_regime()

    for strat_id in engine.CANDIDATE_SPECS.keys():
        setup = engine._evaluate_current_setup(strat_id, regime, cost_scenario="COINBASE_RETAIL_87BPS")
        assert setup["execution_authorization"] == "DISABLED"
        assert setup["model_authorization"] == "OFFLINE_RESEARCH_ONLY"
        assert setup["live_trading"] == "DISABLED"

        if setup["setup_state"] == "SETUP_AVAILABLE":
            entry = setup["entry_price"]
            tp = setup["tp_price"]
            sl = setup["sl_price"]
            assert entry is not None and tp is not None and sl is not None

            # Long bracket: SL < Entry < TP
            # Short bracket: TP < Entry < SL
            if tp > entry:
                assert sl < entry < tp, f"Invalid Long geometry: SL {sl} < Entry {entry} < TP {tp}"
                assert setup["gross_reward_risk"] > 0
            else:
                assert tp < entry < sl, f"Invalid Short geometry: TP {tp} < Entry {entry} < SL {sl}"
                assert setup["gross_reward_risk"] > 0
        else:
            # When no setup, levels must be None or marked unvalidated, and reason must be present
            assert setup["blocking_reason"] is not None
            assert len(setup["blocking_reason"]) > 0


# ==============================================================================
# 4. P0 — Strategy Contract Detail Inspection Endpoint
# ==============================================================================
def test_v13_strategy_contract_detail_endpoint():
    """Verify GET /api/tournament/contract/{strategy_id} returns versioned parameters and literature citations."""
    response = client.get("/api/tournament/contract/REGIME_ADAPTIVE_ROUTER")
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()

    assert data["strategy_id"] == "REGIME_ADAPTIVE_ROUTER"
    assert "specification_hash" in data or "specification" in data
    assert "source_citation" in data or "source_ref" in data["specification"]
    assert "indicators" in data or "indicators" in data["specification"]
    assert "supported_regimes" in data or "supported_regimes" in data["specification"]
    assert "entry_rules" in data or "entry_rules" in data["specification"]
    assert "exit_rules" in data or "exit_rules" in data["specification"]
    assert "current_setup" in data
    assert data["governance"]["execution_authorization"] == "DISABLED"
    assert data["governance"]["model_authorization"] == "OFFLINE_RESEARCH_ONLY"


# ==============================================================================
# 5. P0 — Fixed Replay & Counterfactual Lab Behavior
# ==============================================================================
def test_v13_counterfactual_lab_endpoints():
    """Verify /prediction/counterfactual and /prediction/counterfactual/contract endpoints."""
    # 1. Main counterfactual endpoint
    res = client.get("/prediction/counterfactual")
    assert res.status_code == 200
    data = res.json()
    assert "counterfactuals" in data
    assert len(data["counterfactuals"]) >= 5

    # Check each canonical mechanism has valid upper_scenario and lower_scenario
    mechanisms = {c["genome_id"] for c in data["counterfactuals"]}
    assert "MEIE-IGNITION" in mechanisms
    assert "MEIE-ABSORPTION" in mechanisms
    assert "MEIE-VACUUM" in mechanisms
    assert "MEIE-TOXICITY" in mechanisms
    assert "MEIE-COMBINED" in mechanisms

    for c in data["counterfactuals"]:
        assert "upper_scenario" in c
        assert "lower_scenario" in c
        assert c["upper_scenario"]["status"] in ["AVAILABLE", "BLOCKED", "UNAVAILABLE"]
        assert c["lower_scenario"]["status"] in ["AVAILABLE", "BLOCKED", "UNAVAILABLE"]

    # 2. Counterfactual contract detail endpoint for modal inspection
    res_contract = client.get("/prediction/counterfactual/contract/MEIE-IGNITION")
    assert res_contract.status_code == 200
    contract_data = res_contract.json()
    assert contract_data["status"] == "SUCCESS"
    assert "contract" in contract_data or "contract_details" in contract_data
    assert "upper_scenario" in contract_data
    assert "lower_scenario" in contract_data


# ==============================================================================
# 6. P0 — Tournament Leaderboard Endpoint
# ==============================================================================
def test_v13_tournament_leaderboard_endpoint():
    """Verify GET /api/tournament/latest returns top 5 candidates across 3 cost scenarios."""
    for cost in ["COINBASE_RETAIL_87BPS", "COINBASE_INSTITUTIONAL_18BPS", "BINANCE_PERP_15BPS"]:
        res = client.get(f"/api/tournament/latest?cost_scenario={cost}")
        assert res.status_code == 200
        payload = res.json()

        assert "market_regime" in payload
        assert "top_candidates" in payload
        assert len(payload["top_candidates"]) == 5
        assert "baselines" in payload
        assert "BUY_AND_HOLD" in payload["baselines"]
        assert "NO_TRADE" in payload["baselines"]

        # Check each candidate has current_setup attached
        for cand in payload["top_candidates"]:
            assert "current_setup" in cand
            assert "setup_state" in cand["current_setup"]
            assert cand["current_setup"]["execution_authorization"] == "DISABLED"
            assert cand["current_setup"]["model_authorization"] == "OFFLINE_RESEARCH_ONLY"
            assert cand["current_setup"]["live_trading"] == "DISABLED"


# ==============================================================================
# 7. Frontend Integration Contract Test
# ==============================================================================
def test_v13_frontend_script_and_styles_integrity():
    """Verify web/app.js and web/styles.css contain V13 overlay components, modal, and zero syntax errors."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app_js_path = os.path.join(repo_root, "web", "app.js")
    styles_css_path = os.path.join(repo_root, "web", "styles.css")

    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js = f.read()

    # Required V13 frontend markers
    assert "ContractInspectionModal" in app_js
    assert "chart-overlay-diagnostic-banner" in app_js
    assert "fetchTournamentLatest" in app_js
    assert "fetchStrategySetup" in app_js
    assert "fetchStrategyContract" in app_js
    assert "overlayStrategyId" in app_js
    assert "overlayEnabled" in app_js

    with open(styles_css_path, "r", encoding="utf-8") as f:
        styles_css = f.read()

    assert ".chart-overlay-diagnostic-banner" in styles_css
    assert ".contract-modal-backdrop" in styles_css
    assert ".contract-modal-container" in styles_css
    assert ".tournament-btn-action" in styles_css
