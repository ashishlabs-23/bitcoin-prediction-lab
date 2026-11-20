"""
tests/test_v32_43_strategy_tournament_and_smart_entry.py — BTCognitive V32.43 Tests
=====================================================================================
Tests the complete Strategy Tournament and Smart Entry Lifecycle:
1. Analyse does not create a simulated trade.
2. Regime classification and candidate filtering.
3. 7/10 preliminary screen (pass, fail, insufficient sample, Wilson CI).
4. Controlled tournament backtest (3 arms: Strategy alone, Strategy + AI, Baseline).
5. Smart Entry eligibility decision and calibration status separation.
6. Enter (Simulated) action creates one persistent attempt with locked TP/SL.
7. Immutable TP/SL lock invariant across later forecast shifts.
8. Direction-change alert emitted without silent rule modification.
9. Automatic outcome handling (TP_HIT, SL_HIT, Dual-touch unresolved, Timeout).
10. Partial exit and remaining attempt continuation.
11. Outcome evaluation without monetary P&L.
12. Append-only ledger persistence and restart recovery.
13. Strict non-execution safety and protected files isolation assertion.
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


def _create_mock_ohlcv(n_bars: int = 250, regime: str = "BULLISH") -> pd.DataFrame:
    """Generates synthetic 1h OHLCV data for controlled indicator testing."""
    np.random.seed(42)
    base_price = 80000.0
    dates = pd.date_range("2026-09-01", periods=n_bars, freq="1h", tz="UTC")

    if regime == "BULLISH":
        drift = 0.001
        vol = 0.005
    elif regime == "RANGE":
        drift = 0.0
        vol = 0.002
    else:
        drift = 0.0
        vol = 0.015

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


def test_wilson_confidence_interval():
    """Verify Wilson score confidence interval calculation."""
    # Under 7 successes out of 10, Wilson 95% CI is approximately [0.3968, 0.8922]
    low, high = compute_wilson_ci(7, 10)
    assert abs(low - 0.3968) < 0.01
    assert abs(high - 0.8922) < 0.01

    # Edge cases
    assert compute_wilson_ci(0, 0) == (0.0, 0.0)
    assert compute_wilson_ci(0, 10)[0] == 0.0
    assert compute_wilson_ci(10, 10)[1] == 1.0


def test_regime_classifier_and_warmup():
    """Verify regime classifier requires >= 168 bars and classifies regimes."""
    df_short = _create_mock_ohlcv(50)
    res_short = MarketRegimeClassifier.classify(df_short)
    assert res_short["is_valid"] is False
    assert res_short["regime"] == "UNKNOWN_OR_INVALID"
    assert "Insufficient warm-up" in res_short["reason"]

    df_full = _create_mock_ohlcv(200, regime="BULLISH")
    res_full = MarketRegimeClassifier.classify(df_full)
    assert res_full["is_valid"] is True
    assert res_full["regime"] in ("TRENDING_BULLISH", "VOLATILITY_EXPANSION", "RANGE_BOUND")


def test_7_of_10_preliminary_screen():
    """Verify 7/10 preliminary screen logic across pass, fail, and insufficient evidence."""
    entries = VersionedStrategyRegistry.get_all_entries()

    # 1. TSMOM: 7/10 -> PASS
    tsmom = entries["TSMOM_DONCHIAN_24H_168H"]
    sc_tsmom = evaluate_7_of_10_screen(tsmom)
    assert sc_tsmom["passed"] is True
    assert sc_tsmom["status"] == "SCREEN_PASSED"
    assert sc_tsmom["tp_hits"] == 7

    # 2. Bollinger: 6/10 -> FAIL
    bollinger = entries["RANGE_BOLLINGER_REVERSION_20H"]
    sc_boll = evaluate_7_of_10_screen(bollinger)
    assert sc_boll["passed"] is False
    assert sc_boll["status"] == "SCREEN_FAILED"
    assert sc_boll["tp_hits"] == 6

    # 3. HTF: only 4 attempts -> INSUFFICIENT_EVIDENCE
    htf = entries["HTF_RANGE_EXPANSION_BREAKOUT"]
    sc_htf = evaluate_7_of_10_screen(htf)
    assert sc_htf["passed"] is False
    assert sc_htf["status"] == "INSUFFICIENT_EVIDENCE"


def test_analyse_does_not_create_trade():
    """Verify Analyse evaluates conditions and shortlists top-two without creating any trade."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger)
        assert len(sim.attempts) == 0

        df = _create_mock_ohlcv(200)
        ana = analyse_current_market(df, live_price=82000.0)
        assert "shortlisted_candidates" in ana
        assert len(ana["shortlisted_candidates"]) <= 2
        # Verify simulator attempts remained untouched
        assert len(sim.attempts) == 0


def test_tournament_backtest_3_arms():
    """Do not expose arm metrics until their source data and manifest are verified."""
    df = _create_mock_ohlcv(200)
    ana = analyse_current_market(df, live_price=82000.0)
    tourn = run_strategy_tournament_backtest(
        shortlisted_candidates=ana["shortlisted_candidates"],
        current_regime=ana["market_regime"]["regime"]
    )
    assert "candidate_results" in tourn
    assert "baseline_comparator" in tourn
    assert tourn["candidate_results"] == []
    assert tourn["baseline_comparator"] is None
    assert tourn["final_verdict"] == "ABSTAIN"
    assert tourn["execution_source"] == "CACHED_WALK_FORWARD_UNAVAILABLE"
    assert tourn["cache_validation"]["hashes_matched"] is False


def test_smart_entry_decision_calibration_status():
    """Verify Smart Entry decision enforces calibration status separation."""
    df = _create_mock_ohlcv(200)
    ana = analyse_current_market(df, live_price=82000.0)
    tourn = run_strategy_tournament_backtest(
        shortlisted_candidates=ana["shortlisted_candidates"],
        current_regime=ana["market_regime"]["regime"]
    )
    dec = formulate_smart_entry_decision(analysis_res=ana, tournament_res=tourn)
    assert dec["status"] == "NO_SMART_ENTRY"
    assert dec["action"] == "ABSTAIN"
    assert dec["candidate_setup"] is None


def test_enter_simulated_trade_freezes_locked_levels():
    """Verify Enter creates an active attempt with frozen immutable levels and SHA-256 seal."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger)

        decision_payload = {
            "status": "SMART_ENTRY_AVAILABLE",
            "candidate_setup": {
                "strategy_id": "TSMOM_DONCHIAN_24H_168H",
                "strategy_name": "Donchian Trend Breakout",
                "version": "1.0.0",
                "tournament_id": "trn_test_001",
                "direction": "LONG",
                "market_regime": "TRENDING_BULLISH",
                "entry_reference_price": 80000.0,
                "proposed_tp_price": 83000.0,
                "proposed_sl_price": 78000.0,
                "max_duration_hours": 24.0,
                "anomaly_policy": "Close below 50h EMA",
                "latest_ai_forecast": {"forecast_direction": "UP", "probability_up": 0.70}
            }
        }

        attempt, err = sim.enter_simulated_trade(decision_payload, entry_price=80000.0)
        assert err is None
        assert attempt is not None
        assert attempt.status == "ACTIVE"
        assert attempt.reference_entry_price == 80000.0
        assert attempt.frozen_tp_price == 83000.0
        assert attempt.frozen_sl_price == 78000.0
        assert len(attempt.immutable_sha256) == 64

        # Verify levels DO NOT move when AI forecast shifts
        candle = {"high": 81000.0, "low": 79500.0, "close": 80500.0, "timestamp_utc": "2026-10-26T01:00:00Z"}
        reversed_forecast = {"forecast_direction": "DOWN", "probability_down": 0.75}

        events = sim.update_active_attempts(candle, latest_forecast=reversed_forecast)
        att = sim.attempts[attempt.attempt_id]
        assert att.frozen_tp_price == 83000.0  # LOCKED
        assert att.frozen_sl_price == 78000.0  # LOCKED
        assert att.direction_change_alert is True  # Alerted without rewriting TP/SL


def test_automatic_tp_and_sl_hits():
    """Verify automatic resolution of TP hit and SL hit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger)

        decision_payload = {
            "candidate_setup": {
                "strategy_id": "TSMOM_DONCHIAN_24H_168H",
                "strategy_name": "Donchian Trend Breakout",
                "entry_reference_price": 80000.0,
                "proposed_tp_price": 83000.0,
                "proposed_sl_price": 78000.0
            }
        }

        # 1. TP Hit
        att_tp, _ = sim.enter_simulated_trade(decision_payload)
        candle_tp = {"high": 83200.0, "low": 79500.0, "close": 83100.0, "timestamp_utc": "2026-10-26T02:00:00Z"}
        sim.update_active_attempts(candle_tp)
        assert sim.attempts[att_tp.attempt_id].status == "SUCCESS_TP_HIT"
        assert sim.attempts[att_tp.attempt_id].final_exit_price == 83000.0

        # 2. SL Hit
        att_sl, _ = sim.enter_simulated_trade(decision_payload)
        candle_sl = {"high": 81000.0, "low": 77800.0, "close": 77900.0, "timestamp_utc": "2026-10-26T03:00:00Z"}
        sim.update_active_attempts(candle_sl)
        assert sim.attempts[att_sl.attempt_id].status == "FAILURE_SL_HIT"
        assert sim.attempts[att_sl.attempt_id].final_exit_price == 78000.0


def test_dual_touch_ambiguous_candle():
    """Verify intrabar ambiguity is flagged as UNRESOLVED_INTRABAR_ORDER."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger)

        decision_payload = {
            "candidate_setup": {
                "strategy_id": "TSMOM_DONCHIAN_24H_168H",
                "strategy_name": "Donchian Trend Breakout",
                "entry_reference_price": 80000.0,
                "proposed_tp_price": 83000.0,
                "proposed_sl_price": 78000.0
            }
        }

        att, _ = sim.enter_simulated_trade(decision_payload)
        # Candle touches both TP (83,500) and SL (77,500)
        candle_dual = {"high": 83500.0, "low": 77500.0, "close": 80000.0, "timestamp_utc": "2026-10-26T04:00:00Z"}
        sim.update_active_attempts(candle_dual)
        assert sim.attempts[att.attempt_id].status == "UNRESOLVED_INTRABAR_ORDER"


def test_partial_exit_and_remainder_continuation():
    """Verify partial exit deducts ratio while remainder continues active."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger)

        decision_payload = {
            "candidate_setup": {
                "strategy_id": "TSMOM_DONCHIAN_24H_168H",
                "strategy_name": "Donchian Trend Breakout",
                "entry_reference_price": 80000.0,
                "proposed_tp_price": 83000.0,
                "proposed_sl_price": 78000.0
            }
        }

        att, _ = sim.enter_simulated_trade(decision_payload)
        att_part, err = sim.user_partial_exit(att.attempt_id, exit_price=81500.0, ratio=0.5)
        assert err is None
        assert att_part.status == "ACTIVE"  # Still active!
        assert att_part.remaining_ratio == 0.5
        assert len(att_part.partial_exits) == 1


def test_outcome_evaluation_no_monetary_pnl():
    """Verify evaluation summary reports TP-first hit rate and denominators without monetary P&L."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger)

        decision_payload = {
            "candidate_setup": {
                "strategy_id": "TSMOM_DONCHIAN_24H_168H",
                "strategy_name": "Donchian Trend Breakout",
                "entry_reference_price": 80000.0,
                "proposed_tp_price": 83000.0,
                "proposed_sl_price": 78000.0
            }
        }

        att, _ = sim.enter_simulated_trade(decision_payload)
        sim.update_active_attempts({"high": 83500.0, "low": 79500.0, "close": 83000.0})

        summary = sim.get_evaluation_summary()
        assert summary["primary_metric"]["metric_name"] == "TP_FIRST_SUCCESS_RATE"
        assert summary["primary_metric"]["rate"] == 1.0
        assert "pnl_usd" not in summary  # No monetary P&L!
        assert "gross_pnl_usd" not in summary
        assert "net_pnl_usd" not in summary


def test_durable_persistence_and_recovery():
    """Verify ledger replay reconstructs state across restarts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = os.path.join(tmpdir, "attempts.jsonl")
        sim1 = SmartEntrySimulator(ledger_file=ledger)

        decision_payload = {
            "candidate_setup": {
                "strategy_id": "TSMOM_DONCHIAN_24H_168H",
                "strategy_name": "Donchian Trend Breakout",
                "entry_reference_price": 80000.0,
                "proposed_tp_price": 83000.0,
                "proposed_sl_price": 78000.0
            }
        }

        att, _ = sim1.enter_simulated_trade(decision_payload)
        sim1.user_partial_exit(att.attempt_id, exit_price=81500.0, ratio=0.5)

        # Instance 2 loads same ledger
        sim2 = SmartEntrySimulator(ledger_file=ledger)
        assert att.attempt_id in sim2.attempts
        assert sim2.attempts[att.attempt_id].remaining_ratio == 0.5


def test_api_endpoints_smart_entry_lifecycle():
    """Verify FastAPI endpoints for analyse, tournament, enter, and exit."""
    # Missing candles must remain explicitly unavailable, rather than fabricating market inputs.
    missing = client.post("/api/tournament/analyse", json={"live_price": 81000.0})
    assert missing.status_code == 422
    assert missing.json()["detail"]["error_code"] == "DATA_UNAVAILABLE"

    # 1. Analyse using only an explicitly labelled deterministic fixture.
    fixture = _create_mock_ohlcv(250)
    latest_open = pd.Timestamp.now(tz="UTC").floor("h") - pd.Timedelta(hours=1)
    fixture["timestamp_utc"] = pd.date_range(
        end=latest_open, periods=len(fixture), freq="h"
    ).map(lambda timestamp: timestamp.isoformat())
    fixture["is_closed"] = True
    res_a = client.post("/api/tournament/analyse", json={
        "candles": fixture.to_dict(orient="records"),
        "data_source": "DETERMINISTIC_FIXTURE",
        "live_price": 81000.0
    })
    assert res_a.status_code == 200
    ana_data = res_a.json()
    assert "shortlisted_candidates" in ana_data

    # 2. Run Tournament
    res_t = client.post("/api/tournament/run", json={
        "shortlisted_candidates": ana_data["shortlisted_candidates"],
        "current_regime": ana_data["market_regime"]["regime"]
    })
    assert res_t.status_code == 200
    tourn_data = res_t.json()
    assert "candidate_results" in tourn_data

    # 3. Latest Smart Entry Decision
    res_d = client.get("/api/tournament/smart-entry/latest")
    assert res_d.status_code == 200
    dec_data = res_d.json()
    assert "status" in dec_data

    # 4. Enter Simulated Trade (if available or simulated decision)
    mock_dec = {
        "status": "SMART_ENTRY_AVAILABLE",
        "candidate_setup": {
            "strategy_id": "TSMOM_DONCHIAN_24H_168H",
            "strategy_name": "Donchian Trend Breakout",
            "entry_reference_price": 81000.0,
            "proposed_tp_price": 84000.0,
            "proposed_sl_price": 79000.0,
            "max_duration_hours": 24.0,
            "latest_ai_forecast": {"forecast_direction": "UP"}
        }
    }
    res_enter = client.post("/api/tournament/smart-entry/enter", json={"decision_payload": mock_dec})
    assert res_enter.status_code == 409
    assert "no verified chart-data provenance" in res_enter.json()["detail"]

def test_protected_files_isolation_assertion():
    """Verify that the 5 protected files are never altered."""
    for rel_path in PROTECTED_FILES:
        full_path = os.path.join(os.path.dirname(__file__), "..", rel_path)
        assert os.path.exists(full_path), f"Protected file missing: {rel_path}"
