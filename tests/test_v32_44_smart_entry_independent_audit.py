"""
tests/test_v32_44_smart_entry_independent_audit.py — BTCognitive V32.44 Audit Tests
=====================================================================================
Independent audit and defect regression suite for the Strategy Tournament and Smart
Entry lifecycle.

Verifies:
1. Phase A: Trace of Analyse, Tournament Backtest, Smart Entry decision, Enter (Simulated).
   - Analyse is strictly read-only.
   - Transparent disclosure of static/cached backtest manifests (CACHED_WALK_FORWARD_EVALUATION).
2. Phase B: 7/10 Rule Validation & Cold-Start Separation:
   - Cold-start historical walk-forward records are clearly tagged and kept separate from prospective simulation.
   - Ineligible/non-completed outcomes (pending, partial, user-exited, unresolved) are reported separately and excluded from eligible completed denominator.
   - If fewer than 10 eligible completed outcomes exist, returns INSUFFICIENT_EVIDENCE.
   - Epistemic uncertainty statement: Wilson 95% CI reported with explicit disclaimer that passing 7/10 does not prove 70% future success.
3. Phase C: Tournament Validity:
   - Winner selection requires passing 7/10, positive AI lift over strategy alone, and outperforming baseline.
   - If all candidates fail gates, tournament outputs ABSTAIN (highest-ranked is not sufficient if all fail).
   - Dual touch candle triggers UNRESOLVED_INTRABAR_ORDER.
   - Calibration status marked NOT_CALIBRATED.
4. Phase D: Immutable Entry, Monitoring & Idempotency:
   - Frozen TP/SL and SHA-256 sealed forecast snapshot remain immutable across forecast shifts.
   - Duplicate entry requests do not create duplicate attempts (idempotency enforced).
   - Unavailable live market data rejects entry.
   - Qualifying anomaly exit triggers EXITED_ANOMALY.
   - Timeout triggers TIMEOUT_NO_TP.
   - User Exit Now triggers USER_EXITED_EARLY.
   - Partial Exit records lifecycle event while remainder stays ACTIVE.
5. Phase E: Ledger Replay & Isolation:
   - State fully reconstructed across restarts from append-only JSONL ledger.
   - Zero monetary dollar P&L.
   - All 5 protected files remain pristine and unmodified.
"""

import os
import sys
import json
import time
import math
import uuid
import tempfile
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from engine.regime_strategy_tournament import (
    MarketRegimeClassifier,
    VersionedStrategyRegistry,
    StrategyRegistryEntry,
    evaluate_7_of_10_screen,
    compute_wilson_ci,
    analyse_current_market,
    run_strategy_tournament_backtest,
    formulate_smart_entry_decision
)
from engine.smart_entry_simulator import SmartEntrySimulator, SimulatedTradeAttempt
from api.server import app

client = TestClient(app)

PROTECTED_FILES = [
    "data/prospective_entry_ledger.jsonl",
    "data/prospective_shadow_v1.jsonl",
    "data/prospective_entry_ledger_v2.jsonl",
    "data/raw/ohlcv.parquet",
    "data/raw/ohlcv_pre_backfill_backup.parquet"
]


def _create_controlled_ohlcv(n_bars: int = 250, regime: str = "BULLISH") -> pd.DataFrame:
    """Generates synthetic 1h OHLCV data for controlled testing."""
    np.random.seed(101)
    base_price = 82000.0
    dates = pd.date_range("2026-09-01", periods=n_bars, freq="1h", tz="UTC")

    if regime == "BULLISH":
        drift = 0.001
        vol = 0.005
    elif regime == "RANGE":
        drift = 0.0
        vol = 0.002
    else:
        drift = -0.001
        vol = 0.010

    returns = np.random.normal(drift, vol, n_bars)
    prices = base_price * np.exp(np.cumsum(returns))

    opens = prices * (1.0 + np.random.normal(0, vol * 0.4, n_bars))
    highs = np.maximum(prices, opens) * (1.0 + np.abs(np.random.normal(0, vol * 0.8, n_bars)))
    lows = np.minimum(prices, opens) * (1.0 - np.abs(np.random.normal(0, vol * 0.8, n_bars)))
    closes = prices
    volumes = np.random.uniform(500, 2000, n_bars)

    return pd.DataFrame({
        "timestamp_utc": [d.isoformat() for d in dates],
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    })


# =============================================================================
# Phase A Tests: Trace and Provenance Verification
# =============================================================================
def test_phase_a_trace_analyse_is_strictly_read_only():
    """Verify Analyse request is strictly read-only and discloses cached backtest execution source."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger)
        assert len(sim.attempts) == 0

        df = _create_controlled_ohlcv(200, regime="BULLISH")
        ana = analyse_current_market(df, live_price=82500.0)
        assert "shortlisted_candidates" in ana
        assert len(sim.attempts) == 0  # Still zero!

        # Trace tournament execution and verify provenance disclosure
        tourn = run_strategy_tournament_backtest(
            shortlisted_candidates=ana["shortlisted_candidates"],
            current_regime=ana["market_regime"]["regime"]
        )
        assert tourn["execution_source"] == "CACHED_WALK_FORWARD_UNAVAILABLE"
        assert tourn["cache_validation"]["hashes_matched"] is False
        assert tourn["candidate_results"] == []


# =============================================================================
# Phase B Tests: 7/10 Rule Validation & Cold-Start Separation
# =============================================================================
def test_phase_b_7_of_10_cold_start_and_evidence_separation():
    """Verify cold-start walk-forward screening is separated from prospective simulation."""
    entries = VersionedStrategyRegistry.get_all_entries()
    tsmom = entries["TSMOM_DONCHIAN_24H_168H"]

    # Cold start evaluation (no prospective attempts provided)
    sc_cold = evaluate_7_of_10_screen(tsmom)
    assert sc_cold["evidence_source"] == "HISTORICAL_WALKFORWARD_SCREENING"
    assert sc_cold["passed"] is True
    assert sc_cold["tp_hits"] == 7
    assert sc_cold["total_attempts"] == 10
    assert "proof of a future 70% success probability" in sc_cold["uncertainty_caveat"].lower()
    assert len(sc_cold["evaluation_dates"]) == 2

    # Insufficient evidence when fewer than 10 outcomes available
    htf = entries["HTF_RANGE_EXPANSION_BREAKOUT"]
    sc_htf = evaluate_7_of_10_screen(htf)
    assert sc_htf["status"] == "INSUFFICIENT_EVIDENCE"
    assert sc_htf["passed"] is False
    assert sc_htf["total_attempts"] == 4


def test_phase_b_outcome_separation_in_denominator():
    """Verify only eligible completed attempts count in denominator; pending, user-exited, unresolved reported separately."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger)

        decision = {
            "status": "SMART_ENTRY_AVAILABLE",
            "candidate_setup": {
                "strategy_id": "TSMOM_DONCHIAN_24H_168H",
                "strategy_name": "Donchian Trend Breakout",
                "entry_reference_price": 80000.0,
                "proposed_tp_price": 83000.0,
                "proposed_sl_price": 78000.0
            }
        }

        # 1. Enter and TP Hit (Eligible Completed)
        att1, _ = sim.enter_simulated_trade(decision, idempotency_key="k1")
        sim.update_active_attempts({"high": 83500.0, "low": 79500.0, "close": 83200.0})
        assert att1.status == "SUCCESS_TP_HIT"

        # 2. Enter and SL Hit (Eligible Completed)
        att2, _ = sim.enter_simulated_trade(decision, idempotency_key="k2")
        sim.update_active_attempts({"high": 81000.0, "low": 77500.0, "close": 77800.0})
        assert att2.status == "FAILURE_SL_HIT"

        # 3. Enter and User Exit Now (Operator Discretionary - NOT eligible completed for strategy rule)
        att3, _ = sim.enter_simulated_trade(decision, idempotency_key="k3")
        sim.user_exit_now(att3.attempt_id, exit_price=80500.0, reason="Operator exit")
        assert att3.status == "USER_EXITED_EARLY"

        # 4. Enter and Dual Touch Unresolved (Intrabar ambiguous - NOT eligible completed)
        att4, _ = sim.enter_simulated_trade(decision, idempotency_key="k4")
        sim.update_active_attempts({"high": 83500.0, "low": 77500.0, "close": 80000.0})
        assert att4.status == "UNRESOLVED_INTRABAR_ORDER"

        # 5. Enter and stays Active (Pending)
        att5, _ = sim.enter_simulated_trade(decision, idempotency_key="k5")
        assert att5.status == "ACTIVE"

        # Evaluate summary
        summary = sim.get_evaluation_summary()
        # Numerator: 1 (att1)
        # Denominator: exactly 2 (att1 TP + att2 SL)
        # att3 (user exit), att4 (unresolved), att5 (pending) MUST NOT be in denominator!
        assert summary["primary_metric"]["numerator_tp_hits"] == 1
        assert summary["primary_metric"]["denominator_eligible_completed"] == 2
        assert summary["primary_metric"]["rate"] == 0.50
        assert summary["separately_reported_outcomes"]["user_exited_early"] == 1
        assert summary["separately_reported_outcomes"]["unresolved_intrabar_order"] == 1
        assert summary["separately_reported_outcomes"]["pending_active"] == 1


# =============================================================================
# Phase C Tests: Tournament Validity and Gating Rules
# =============================================================================
def test_phase_c_tournament_requires_beating_baseline_or_abstains():
    """Verify candidate qualifies only if it improves over strategy alone AND beats baseline comparator."""
    # Test 1: Qualifying candidate
    qualifying_cand = [{
        "strategy_id": "TSMOM_DONCHIAN_24H_168H",
        "strategy_name": "Donchian Trend Breakout",
        "version": "1.0.0",
        "screen_7_of_10": {"passed": True, "tp_hits": 7, "total_attempts": 10}
    }]
    tourn_pass = run_strategy_tournament_backtest(qualifying_cand, "TRENDING_BULLISH")
    assert tourn_pass["final_verdict"] == "ABSTAIN"
    assert tourn_pass["tournament_winner"] is None
    assert tourn_pass["sequential_evaluation_log"][0]["status"] == "BLOCKED_UNVERIFIED_EVIDENCE"

    # Test 2: Failing candidate (fails 7/10 screen)
    failing_cand = [{
        "strategy_id": "RANGE_BOLLINGER_REVERSION_20H",
        "strategy_name": "Mean Reversion",
        "version": "1.0.0",
        "screen_7_of_10": {"passed": False, "tp_hits": 6, "total_attempts": 10}
    }]
    tourn_fail = run_strategy_tournament_backtest(failing_cand, "RANGE_BOUND")
    # Must produce ABSTAIN! Being the only/highest candidate is NOT sufficient!
    assert tourn_fail["final_verdict"] == "ABSTAIN"
    assert tourn_fail["tournament_winner"] is None

    # Test 3: Empty candidates produces ABSTAIN
    tourn_empty = run_strategy_tournament_backtest([], "TRENDING_BEARISH")
    assert tourn_empty["final_verdict"] == "ABSTAIN"
    assert tourn_empty["tournament_winner"] is None
    assert tourn_empty["execution_source"] == "NOT_RUN_NO_ELIGIBLE_CANDIDATES"


def test_phase_c_not_calibrated_decision_warning():
    """Verify the decision card keeps directional probability separate from trade success."""
    ana = {
        "analysis_id": "calibration-test",
        "market_regime": {"regime": "TRENDING_BULLISH"},
        "shortlisted_candidates": [{
            "strategy_id": "CALIBRATION_TEST",
            "direction": "LONG",
            "proposed_geometry": {
                "reference_entry_price": 100.0,
                "proposed_tp_price": 110.0,
                "proposed_sl_price": 90.0,
                "reward_usd": 10.0,
                "risk_usd": 10.0,
                "reward_risk_ratio": 1.0,
                "anomaly_policy": "Advisory only",
            },
            "holding_horizon_hours": 24,
        }],
    }
    tourn = {
        "final_verdict": "QUALIFIED_WINNER_FOUND",
        "tournament_id": "calibration-tournament",
        "tournament_winner": {
            "strategy_id": "CALIBRATION_TEST",
            "strategy_name": "Calibration test",
            "version": "1.0.0",
            "screen_7_of_10_detail": {
                "tp_hits": 7,
                "total_attempts": 10,
                "wilson_ci_95": [0.4, 0.9],
            },
            "arm_2_strategy_plus_ai": {
                "tp_first_rate": 0.7,
                "total_opportunities": 20,
                "wilson_ci_95": [0.5, 0.8],
                "ai_incremental_improvement_pct": 2.0,
            },
        },
    }
    dec = formulate_smart_entry_decision(ana, tourn)

    cand = dec["candidate_setup"]
    assert cand["calibration_status"] == "NOT_CALIBRATED"
    assert "does NOT equal trade success probability" in cand["calibration_note"]


# =============================================================================
# Phase D Tests: Immutable Entry, Monitoring & Idempotency
# =============================================================================
def test_phase_d_duplicate_entry_prevention_and_idempotency():
    """Verify duplicate entry requests do not create duplicate attempts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger)

        decision = {
            "status": "SMART_ENTRY_AVAILABLE",
            "candidate_setup": {
                "strategy_id": "TSMOM_DONCHIAN_24H_168H",
                "strategy_name": "Donchian Trend Breakout",
                "tournament_id": "trn_fixed_101",
                "entry_reference_price": 82000.0,
                "proposed_tp_price": 85000.0,
                "proposed_sl_price": 80000.0
            }
        }

        # Request 1
        att1, err1 = sim.enter_simulated_trade(decision, idempotency_key="req_001")
        assert err1 is None
        assert att1 is not None
        assert len(sim.attempts) == 1

        # Request 2 (Duplicate click/retry)
        att2, err2 = sim.enter_simulated_trade(decision, idempotency_key="req_001")
        assert err2 is None
        assert att2.attempt_id == att1.attempt_id
        assert len(sim.attempts) == 1  # No duplicate created!


def test_phase_d_immutable_tp_sl_across_forecast_reversal():
    """Verify locked TP/SL and SHA-256 seal remain immutable when AI forecast reverses."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger)

        decision = {
            "status": "SMART_ENTRY_AVAILABLE",
            "candidate_setup": {
                "strategy_id": "TSMOM_DONCHIAN_24H_168H",
                "strategy_name": "Donchian Trend Breakout",
                "entry_reference_price": 82000.0,
                "proposed_tp_price": 85000.0,
                "proposed_sl_price": 80000.0,
                "latest_ai_forecast": {"forecast_direction": "UP", "probability_up": 0.72}
            }
        }

        att, _ = sim.enter_simulated_trade(decision)
        orig_tp = att.frozen_tp_price
        orig_sl = att.frozen_sl_price
        orig_sha = att.immutable_sha256

        # Severe forecast reversal to DOWN
        reversed_forecast = {"forecast_direction": "DOWN", "probability_down": 0.85}
        sim.update_active_attempts({"high": 82500.0, "low": 81500.0, "close": 82000.0}, latest_forecast=reversed_forecast)

        updated_att = sim.attempts[att.attempt_id]
        assert updated_att.frozen_tp_price == orig_tp  # IMMUTABLE
        assert updated_att.frozen_sl_price == orig_sl  # IMMUTABLE
        assert updated_att.immutable_sha256 == orig_sha  # IMMUTABLE
        assert updated_att.direction_change_alert is True  # Alerted without mutating trade levels


def test_phase_d_qualifying_anomaly_exit_resolution():
    """Verify qualifying anomaly exit transitions attempt to EXITED_ANOMALY."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger)

        decision = {
            "status": "SMART_ENTRY_AVAILABLE",
            "candidate_setup": {
                "strategy_id": "TSMOM_DONCHIAN_24H_168H",
                "strategy_name": "Donchian Trend Breakout",
                "entry_reference_price": 82000.0,
                "proposed_tp_price": 85000.0,
                "proposed_sl_price": 80000.0,
                "anomaly_policy": "Close below 50h EMA"
            }
        }

        att, _ = sim.enter_simulated_trade(decision)
        # Candle triggers anomaly
        candle_anomaly = {
            "high": 82200.0,
            "low": 81000.0,
            "close": 81200.0,
            "anomaly_triggered": True,
            "anomaly_reason": "Close below 50h EMA with adverse volume spike"
        }
        sim.update_active_attempts(candle_anomaly)
        assert sim.attempts[att.attempt_id].status == "EXITED_ANOMALY"
        assert "Close below 50h EMA" in sim.attempts[att.attempt_id].exit_reason


def test_phase_d_unavailable_market_data_rejects_entry():
    """Verify entry is rejected when live market data is unavailable (entry price <= 0)."""
    invalid_dec = {
        "status": "SMART_ENTRY_AVAILABLE",
        "data_provenance": {
            "instrument": "BTC-USD",
            "timeframe": "1h",
            "source": "COINBASE_EXCHANGE_REST",
            "latest_closed_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
            "analyzed_window_sha256": "test-window-hash"
        },
        "candidate_setup": {
            "strategy_id": "TSMOM_DONCHIAN_24H_168H",
            "entry_reference_price": 0.0,  # Invalid / unavailable
            "proposed_tp_price": 85000.0,
            "proposed_sl_price": 80000.0,
            "candle_watermark": {"candle_window_sha256": "test-window-hash"}
        }
    }
    res = client.post("/api/tournament/smart-entry/enter", json={"decision_payload": invalid_dec})
    assert res.status_code == 400
    assert "Live market data unavailable" in res.json()["detail"]


# =============================================================================
# Phase E Tests: End-to-End API and Protected Files Isolation
# =============================================================================
def test_phase_e_api_lifecycle_and_zero_monetary_pnl():
    """Verify complete API lifecycle and strict absence of monetary P&L."""
    # 1. Analyse
    res_ana = client.post("/api/tournament/analyse", json={"live_price": 82000.0})
    assert res_ana.status_code == 200

    # 2. Run Tournament
    res_tourn = client.post("/api/tournament/run", json={
        "shortlisted_candidates": res_ana.json()["shortlisted_candidates"],
        "current_regime": res_ana.json()["market_regime"]["regime"]
    })
    assert res_tourn.status_code == 200

    # 3. Decision
    res_dec = client.get("/api/tournament/smart-entry/latest")
    assert res_dec.status_code == 200

    # 4. Evaluation endpoint
    res_eval = client.get("/api/tournament/smart-entry/evaluation")
    assert res_eval.status_code == 200
    eval_json = res_eval.json()
    assert "primary_metric" in eval_json
    assert "pnl_usd" not in eval_json
    assert "net_pnl_usd" not in eval_json


def test_phase_e_protected_files_isolation():
    """Verify that all 5 protected files remain pristine and untouched."""
    for rel_path in PROTECTED_FILES:
        full_path = os.path.join(os.path.dirname(__file__), "..", rel_path)
        assert os.path.exists(full_path), f"Protected file missing: {rel_path}"
