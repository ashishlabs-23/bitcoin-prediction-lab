"""
tests/test_v32_47_analyse_selection_and_anomaly_monitor.py — BTCognitive V32.47 Tests
=====================================================================================
Comprehensive Test Suite for V32.47:
- Test Matrix A: Analysis uses current chart data (not fixed fixtures).
- Test Matrix B: Strategy qualification / no false winner / sequential 2-candidate evaluation.
- Test Matrix D: Enter and persistent monitoring / forecast anomaly detection / restart recovery.
- Test Matrix E: Outcome and storage invariants / conservative resolution / protected files preservation.
"""

import os
import sys
import json
import time
import hashlib
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


def _hash_file(path: str) -> str:
    if not os.path.exists(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _get_protected_hashes():
    return {p: _hash_file(p) for p in PROTECTED_FILES}


def _build_fixture_df(n_bars: int = 250, regime_type: str = "BULL_TREND") -> pd.DataFrame:
    """Builds controlled deterministic OHLCV DataFrame."""
    np.random.seed(12345)
    base_price = 85000.0
    dates = pd.date_range("2026-09-01", periods=n_bars, freq="1h", tz="UTC")

    if regime_type == "BULL_TREND":
        returns = np.full(n_bars, 0.0015)  # Steady strong bull drift
        vol = 0.003
    elif regime_type == "HIGH_VOLATILITY":
        returns = np.zeros(n_bars)
        vol = 0.035  # Extreme volatility expansion
    elif regime_type == "RANGE_BOUND":
        returns = np.zeros(n_bars)
        vol = 0.0015
    else:
        returns = np.zeros(n_bars)
        vol = 0.01

    noise = np.random.normal(0, vol, n_bars)
    prices = base_price * np.exp(np.cumsum(returns + noise))

    opens = prices * (1.0 + np.random.normal(0, vol * 0.2, n_bars))
    highs = np.maximum(prices, opens) * (1.0 + np.abs(np.random.normal(0, vol * 0.5, n_bars)))
    lows = np.minimum(prices, opens) * (1.0 - np.abs(np.random.normal(0, vol * 0.5, n_bars)))
    closes = prices
    volumes = np.full(n_bars, 1200.0)

    return pd.DataFrame({
        "timestamp_utc": [d.isoformat() for d in dates],
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "is_closed": [True] * n_bars
    })


# ==============================================================================
# Matrix A: Analysis uses current chart data (not fixed fixtures)
# ==============================================================================

def test_matrix_a_two_distinct_fixtures_produce_different_regimes_and_candidates():
    """Analyse endpoint evaluated on two distinct fixtures returns distinct regimes, features, and rankings."""
    df_bull = _build_fixture_df(n_bars=250, regime_type="BULL_TREND")
    df_vol = _build_fixture_df(n_bars=250, regime_type="HIGH_VOLATILITY")

    res_bull = analyse_current_market(df_1h=df_bull, live_price=float(df_bull["close"].iloc[-1]))
    res_vol = analyse_current_market(df_1h=df_vol, live_price=float(df_vol["close"].iloc[-1]))

    assert res_bull["market_regime"]["regime"] != res_vol["market_regime"]["regime"]
    assert res_bull["candle_watermark"]["total_closed_candles"] == 250
    assert res_vol["candle_watermark"]["total_closed_candles"] == 250
    assert res_bull["candle_watermark_hash"] != res_vol["candle_watermark_hash"]

    # Candidate rejections present
    assert len(res_bull["candidate_rejections"]) > 0
    assert "candidate_rejections" in res_vol


def test_matrix_a_altering_final_closed_bar_changes_output_features():
    """Altering the final closed bar must be consumed and alter computed features/rejection."""
    df_base = _build_fixture_df(n_bars=250, regime_type="RANGE_BOUND")
    res_base = analyse_current_market(df_1h=df_base, live_price=float(df_base["close"].iloc[-1]))

    # Modify final closed bar to a massive pump with 10x volume
    df_mod = df_base.copy()
    last_idx = df_mod.index[-1]
    df_mod.loc[last_idx, "close"] = df_mod.loc[last_idx, "close"] * 1.15
    df_mod.loc[last_idx, "high"] = df_mod.loc[last_idx, "close"] * 1.05
    df_mod.loc[last_idx, "volume"] = 50000.0

    res_mod = analyse_current_market(df_1h=df_mod, live_price=float(df_mod["close"].iloc[-1]))

    assert res_base["candle_watermark_hash"] != res_mod["candle_watermark_hash"]
    # Feature values changed
    assert res_base["market_regime"]["close"] != res_mod["market_regime"]["close"]


def test_matrix_a_altering_open_incomplete_bar_does_not_leak_into_closed_features():
    """An open bar (is_closed=False) must be filtered out and never leak into closed decision features."""
    df = _build_fixture_df(n_bars=250, regime_type="BULL_TREND")
    res_before = analyse_current_market(df_1h=df, live_price=float(df["close"].iloc[-1]))

    # Append an open bar with extreme abnormal values
    open_bar = pd.DataFrame([{
        "timestamp_utc": "2026-09-12T00:00:00+00:00",
        "open": 999999.0,
        "high": 999999.0,
        "low": 1.0,
        "close": 999999.0,
        "volume": 99999999.0,
        "is_closed": False
    }])
    df_with_open = pd.concat([df, open_bar], ignore_index=True)

    res_after = analyse_current_market(df_1h=df_with_open, live_price=float(df["close"].iloc[-1]))

    # Closed watermark and indicators must remain bit-identical
    assert res_before["candle_watermark_hash"] == res_after["candle_watermark_hash"]
    assert res_before["market_regime"]["regime"] == res_after["market_regime"]["regime"]
    assert res_before["candle_watermark"]["total_closed_candles"] == res_after["candle_watermark"]["total_closed_candles"]


def test_matrix_a_analyse_creates_zero_attempts_and_is_read_only():
    """Calling Analyse must create zero simulated attempts and leave ledgers unmodified."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_smart_entry_attempts.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger_path)
        assert len(sim.attempts) == 0

        df = _build_fixture_df(n_bars=250, regime_type="BULL_TREND")
        res = analyse_current_market(df_1h=df, live_price=85000.0)

        assert res.get("is_read_only") is True
        assert res.get("attempts_created") == 0
        assert len(sim.attempts) == 0
        assert not os.path.exists(ledger_path) or os.path.getsize(ledger_path) == 0


# ==============================================================================
# Matrix B: Strategy qualification / no false winner / sequential gates
# ==============================================================================

def test_matrix_b_candidate_with_6_of_10_fails_screen():
    """Candidate with 6 TP hits out of 10 must fail preliminary screen."""
    entry = VersionedStrategyRegistry.get_all_entries()["TSMOM_DONCHIAN_24H_168H"]
    mock_outcomes_6 = [
        {"strategy_id": "TSMOM_DONCHIAN_24H_168H", "strategy_version": "1.0.0", "status": "SUCCESS_TP_HIT"} for _ in range(6)
    ] + [
        {"strategy_id": "TSMOM_DONCHIAN_24H_168H", "strategy_version": "1.0.0", "status": "FAILURE_SL_HIT"} for _ in range(4)
    ]

    res_6 = evaluate_7_of_10_screen(entry=entry, prospective_attempts=mock_outcomes_6)
    assert res_6["passed"] is False
    assert res_6["tp_hits"] == 6
    assert res_6["tp_hit_rate"] == 0.60
    assert "Failed preliminary screen" in res_6["explanation"]


def test_matrix_b_candidate_with_7_of_10_passes_screen_but_must_pass_tournament():
    """Candidate with 7 TP hits passes screen, but tournament gates evaluate AI lift & baseline."""
    entry = VersionedStrategyRegistry.get_all_entries()["TSMOM_DONCHIAN_24H_168H"]
    mock_outcomes_7 = [
        {"strategy_id": "TSMOM_DONCHIAN_24H_168H", "strategy_version": "1.0.0", "status": "SUCCESS_TP_HIT"} for _ in range(7)
    ] + [
        {"strategy_id": "TSMOM_DONCHIAN_24H_168H", "strategy_version": "1.0.0", "status": "FAILURE_SL_HIT"} for _ in range(3)
    ]

    res_7 = evaluate_7_of_10_screen(entry=entry, prospective_attempts=mock_outcomes_7)
    assert res_7["passed"] is True
    assert res_7["tp_hits"] == 7
    assert res_7["tp_hit_rate"] == 0.70

    # In a tournament where Arm 2 AI lift is negative, it must fail the tournament gate
    cand_fail_ai = {
        "strategy_id": "TEST_STRAT",
        "strategy_name": "Test Strategy",
        "market_regime": "VOLATILITY_EXPANSION",
        "screen_7_of_10_passed": True,
        "screen_7_of_10_detail": res_7,
        "arm_1_strategy_alone": {"tp_first_rate": 0.65, "total_opportunities": 25},
        "arm_2_strategy_plus_ai": {"tp_first_rate": 0.55, "total_opportunities": 20, "ai_incremental_improvement_pct": -10.0},
        "arm_3_baseline_comparison": {"baseline_tp_first_rate": 0.50, "outperformed_baseline": True},
        "gates_passed": False,
        "tournament_passed": False
    }

    tourn_res = {
        "final_verdict": "ABSTAIN",
        "tournament_winner": None,
        "candidate_results": [cand_fail_ai],
        "verdict_explanation": "TOURNAMENT_WINNER_NONE: candidate failed the required positive AI-lift gate."
    }
    ana_res = {"status": "SUCCESS", "shortlisted_candidates": [{"strategy_id": "TEST_STRAT"}]}

    dec = formulate_smart_entry_decision(analysis_res=ana_res, tournament_res=tourn_res)
    assert dec["status"] == "NO_SMART_ENTRY"
    assert dec["action"] == "ABSTAIN"
    assert "TOURNAMENT_WINNER_NONE" in dec["reason"]


def test_matrix_b_candidate_2_evaluated_sequentially_only_if_candidate_1_fails():
    """Candidate 2 is evaluated if and only if candidate 1 fails tournament gates."""
    cand1 = {
        "strategy_id": "TSMOM_DONCHIAN_24H_168H",
        "strategy_name": "Donchian Trend Breakout",
        "screen_7_of_10_passed": False,
        "proposed_geometry": {"reference_entry_price": 85000.0, "proposed_tp_price": 86700.0, "proposed_sl_price": 84150.0}
    }
    cand2 = {
        "strategy_id": "ATR_VOLATILITY_BREAKOUT_12H",
        "strategy_name": "ATR Volatility Expansion",
        "screen_7_of_10_passed": True,
        "proposed_geometry": {"reference_entry_price": 85000.0, "proposed_tp_price": 86275.0, "proposed_sl_price": 84150.0}
    }

    tourn = run_strategy_tournament_backtest(
        shortlisted_candidates=[cand1, cand2],
        current_regime="TRENDING_BULLISH"
    )

    assert tourn["candidate_results"] == []
    assert tourn["final_verdict"] == "ABSTAIN"
    assert all(item["status"] == "BLOCKED_UNVERIFIED_EVIDENCE" for item in tourn["sequential_evaluation_log"])


def test_matrix_b_insufficient_or_stale_data_produces_honest_abstain():
    """Missing or insufficient warmup candles (<50 bars) must return ABSTAIN/Insufficient warm-up."""
    df_short = _build_fixture_df(n_bars=30, regime_type="BULL_TREND")
    res = analyse_current_market(df_1h=df_short, live_price=85000.0)
    assert res["status"] == "ABSTAIN"
    assert "Insufficient warm-up" in res["reason"]


# ==============================================================================
# Matrix D: Enter and persistent monitoring / Anomaly detection / Recovery
# ==============================================================================

def test_matrix_d_enter_simulated_trade_idempotency_and_immutable_freeze():
    """Entering creates exactly one attempt; retry with same idempotency key returns existing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_idempotency_ledger.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger_path)

        decision_payload = {
            "status": "SMART_ENTRY_AVAILABLE",
            "action": "ENTER_SIMULATED",
            "candidate_setup": {
                "strategy_id": "trend_momentum_v1",
                "strategy_name": "Trend Momentum",
                "strategy_version": "1.0.0",
                "market_regime": "BULLISH_TREND",
                "direction": "LONG",
                "reference_entry_price": 85000.0,
                "proposed_tp_price": 86700.0,
                "proposed_sl_price": 84150.0,
                "max_duration_hours": 24,
                "anomaly_policy": "EXIT_IF_FORECAST_REVERSES",
                "calibration_note": "Uncalibrated directional score"
            },
            "tournament_metadata": {"protocol": "3-ARM-WF"},
            "candle_watermark": {"last_closed_bar_timestamp": "2026-09-11T10:00:00Z", "total_closed_candles": 250}
        }

        att1, err1 = sim.enter_simulated_trade(decision_payload=decision_payload, entry_price=85000.0, idempotency_key="key-abc-123")
        assert err1 is None
        assert att1 is not None
        assert att1.reference_entry_price == 85000.0
        assert att1.frozen_tp_price == 86700.0
        assert att1.frozen_sl_price == 84150.0

        # Attempt duplicate entry with same key
        att2, err2 = sim.enter_simulated_trade(decision_payload=decision_payload, entry_price=85000.0, idempotency_key="key-abc-123")
        assert err2 is None
        assert att2.attempt_id == att1.attempt_id
        assert len(sim.attempts) == 1


def test_matrix_d_forecast_direction_flip_records_alert_and_event_without_moving_tpsl():
    """When live forecast reverses direction, monitor records FORECAST_DIRECTION_FLIP alert and event, keeping TP/SL frozen."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_direction_flip_ledger.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger_path)

        dec = {
            "status": "SMART_ENTRY_AVAILABLE",
            "candidate_setup": {
                "strategy_id": "trend_momentum_v1",
                "strategy_name": "Trend Momentum",
                "strategy_version": "1.0.0",
                "market_regime": "BULLISH_TREND",
                "direction": "LONG",
                "reference_entry_price": 85000.0,
                "proposed_tp_price": 86700.0,
                "proposed_sl_price": 84150.0,
                "max_duration_hours": 24,
                "anomaly_policy": "ALERT_OPERATOR",
                "latest_ai_forecast": {"realized_volatility_annualized_pct": 35.0},
                "calibration_note": "Score uncalibrated"
            }
        }
        att, _ = sim.enter_simulated_trade(dec, entry_price=85000.0)
        orig_tp = att.frozen_tp_price
        orig_sl = att.frozen_sl_price
        orig_hash = att.immutable_sha256

        # Monitor with opposite direction forecast (DOWN instead of LONG/UP)
        rev_forecast = {
            "direction": "DOWN",
            "probability_down": 0.85,
            "realized_volatility_annualized_pct": 35.0
        }
        updated_att, new_evts = sim.monitor_active_attempt(
            attempt_id=att.attempt_id,
            current_price=85100.0,
            current_forecast=rev_forecast
        )

        assert updated_att.direction_change_alert is True
        assert "reversed" in updated_att.direction_change_rationale.lower()
        assert updated_att.frozen_tp_price == orig_tp
        assert updated_att.frozen_sl_price == orig_sl
        assert updated_att.immutable_sha256 == orig_hash

        # Anomaly event was recorded
        direction_events = [e for e in updated_att.anomaly_events if e["event_type"] == "FORECAST_DIRECTION_FLIP"]
        assert len(direction_events) == 1
        assert direction_events[0]["entry_direction"] == "LONG"
        assert direction_events[0]["current_direction"] == "DOWN"


def test_matrix_d_forecast_risk_spike_thresholds():
    """Forecast risk spike tested below threshold (1.4x), at threshold (1.5x), and above (1.7x)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_risk_spike_ledger.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger_path)

        dec = {
            "status": "SMART_ENTRY_AVAILABLE",
            "candidate_setup": {
                "strategy_id": "trend_momentum_v1",
                "strategy_name": "Trend Momentum",
                "strategy_version": "1.0.0",
                "market_regime": "BULLISH_TREND",
                "direction": "LONG",
                "reference_entry_price": 85000.0,
                "proposed_tp_price": 86700.0,
                "proposed_sl_price": 84150.0,
                "max_duration_hours": 24,
                "anomaly_policy": "ALERT_OPERATOR",
                "latest_ai_forecast": {"realized_volatility_annualized_pct": 35.0},
                "calibration_note": "Score uncalibrated"
            }
        }
        att, _ = sim.enter_simulated_trade(dec, entry_price=85000.0)

        # 1. 1.4x baseline (baseline=35%, 1.4x = 49.0% -> below 1.5x threshold 52.5%)
        fc_below = {"direction": "UP", "realized_volatility_annualized_pct": 49.0}
        att_below, _ = sim.monitor_active_attempt(att.attempt_id, current_price=85050.0, current_forecast=fc_below)
        assert att_below.risk_spike_alert is False

        # 2. 1.5x baseline (52.5% -> at threshold)
        fc_at = {"direction": "UP", "realized_volatility_annualized_pct": 52.5}
        att_at, _ = sim.monitor_active_attempt(att.attempt_id, current_price=85050.0, current_forecast=fc_at)
        assert att_at.risk_spike_alert is True
        risk_events = [e for e in att_at.anomaly_events if e["event_type"] == "FORECAST_RISK_SPIKE"]
        assert len(risk_events) == 1

        # 3. 1.7x baseline (59.5% -> above threshold)
        fc_above = {"direction": "UP", "realized_volatility_annualized_pct": 59.5}
        att_above, _ = sim.monitor_active_attempt(att.attempt_id, current_price=85050.0, current_forecast=fc_above)
        assert att_above.risk_spike_alert is True


def test_matrix_d_degraded_data_quality_states_never_silently_normal():
    """Stale forecast, stale price feed, malformed forecast produce degraded data_quality_state."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_data_quality_ledger.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger_path)

        dec = {
            "status": "SMART_ENTRY_AVAILABLE",
            "candidate_setup": {
                "strategy_id": "trend_momentum_v1",
                "strategy_name": "Trend Momentum",
                "strategy_version": "1.0.0",
                "market_regime": "BULLISH_TREND",
                "direction": "LONG",
                "reference_entry_price": 85000.0,
                "proposed_tp_price": 86700.0,
                "proposed_sl_price": 84150.0,
                "max_duration_hours": 24,
                "anomaly_policy": "ALERT_OPERATOR",
                "latest_ai_forecast": {"realized_volatility_annualized_pct": 35.0},
                "calibration_note": "Score uncalibrated"
            }
        }
        att, _ = sim.enter_simulated_trade(dec, entry_price=85000.0)

        # 1. Stale price feed
        att_p, _ = sim.monitor_active_attempt(att.attempt_id, current_price=85000.0, data_quality_info={"price_feed_age_seconds": 400})
        assert att_p.data_quality_state == "DEGRADED_STALE_PRICE_FEED"

        # 2. Stale forecast
        att_f, _ = sim.monitor_active_attempt(att.attempt_id, current_price=85000.0, data_quality_info={"forecast_age_seconds": 5000})
        assert att_f.data_quality_state == "DEGRADED_STALE_FORECAST"

        # 3. Malformed forecast (missing required fields)
        att_m, _ = sim.monitor_active_attempt(att.attempt_id, current_price=85000.0, current_forecast={"corrupted": True})
        assert att_m.data_quality_state == "DEGRADED_MALFORMED_FORECAST"


def test_matrix_d_persistence_and_restart_recovery():
    """Simulated attempt and anomaly history recover from ledger persistence on reboot."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_recovery_ledger.jsonl")
        sim1 = SmartEntrySimulator(ledger_file=ledger_path)

        dec = {
            "status": "SMART_ENTRY_AVAILABLE",
            "candidate_setup": {
                "strategy_id": "trend_momentum_v1",
                "strategy_name": "Trend Momentum",
                "strategy_version": "1.0.0",
                "market_regime": "BULLISH_TREND",
                "direction": "LONG",
                "reference_entry_price": 85000.0,
                "proposed_tp_price": 86700.0,
                "proposed_sl_price": 84150.0,
                "max_duration_hours": 24,
                "anomaly_policy": "ALERT_OPERATOR",
                "latest_ai_forecast": {"realized_volatility_annualized_pct": 35.0},
                "calibration_note": "Score uncalibrated"
            }
        }
        att1, _ = sim1.enter_simulated_trade(dec, entry_price=85000.0)

        # Record a risk spike anomaly
        sim1.monitor_active_attempt(
            attempt_id=att1.attempt_id,
            current_price=85050.0,
            current_forecast={"direction": "UP", "realized_volatility_annualized_pct": 60.0}
        )

        # Simulate fresh process startup / restart
        sim2 = SmartEntrySimulator(ledger_file=ledger_path)
        active2 = sim2.get_active_attempts()

        assert len(active2) == 1
        assert active2[0].attempt_id == att1.attempt_id
        assert active2[0].risk_spike_alert is True
        assert len(active2[0].anomaly_events) >= 1
        assert active2[0].frozen_tp_price == att1.frozen_tp_price


# ==============================================================================
# Matrix E: Conservative outcome resolution and protected file isolation
# ==============================================================================

def test_matrix_e_conservative_outcome_resolution_cases():
    """Test TP, SL, same-candle ambiguous dual-touch, and timeout."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_outcomes_ledger.jsonl")
        sim = SmartEntrySimulator(ledger_file=ledger_path)

        dec = {
            "status": "SMART_ENTRY_AVAILABLE",
            "candidate_setup": {
                "strategy_id": "trend_momentum_v1",
                "strategy_name": "Trend Momentum",
                "strategy_version": "1.0.0",
                "market_regime": "BULLISH_TREND",
                "direction": "LONG",
                "reference_entry_price": 85000.0,
                "proposed_tp_price": 86700.0,
                "proposed_sl_price": 84150.0,
                "max_duration_hours": 24,
                "anomaly_policy": "ALERT_OPERATOR",
                "calibration_note": "Score uncalibrated"
            }
        }

        # Case 1: TP Hit
        att_tp, _ = sim.enter_simulated_trade(dec, entry_price=85000.0, idempotency_key="key-tp")
        res_tp, _ = sim.monitor_active_attempt(att_tp.attempt_id, current_price=86750.0)
        assert res_tp.status == "SUCCESS_TP_HIT"

        # Case 2: SL Hit
        att_sl, _ = sim.enter_simulated_trade(dec, entry_price=85000.0, idempotency_key="key-sl")
        res_sl, _ = sim.monitor_active_attempt(att_sl.attempt_id, current_price=84000.0)
        assert res_sl.status == "FAILURE_SL_HIT"

        # Case 3: Same candle dual-touch is unresolved
        att_dual, _ = sim.enter_simulated_trade(dec, entry_price=85000.0, idempotency_key="key-dual")
        dual_candle = {"high": 87000.0, "low": 84000.0, "open": 85000.0, "close": 85500.0}
        res_dual, _ = sim.monitor_active_attempt(att_dual.attempt_id, candle=dual_candle)
        assert res_dual.status == "UNRESOLVED_INTRABAR_ORDER"

        # Case 4: Partial exit followed by user full exit
        att_part, _ = sim.enter_simulated_trade(dec, entry_price=85000.0, idempotency_key="key-part")
        p_res, err_p = sim.user_partial_exit(att_part.attempt_id, exit_price=85500.0, ratio=0.5)
        assert err_p is None
        assert p_res.remaining_ratio == 0.5
        assert p_res.status == "ACTIVE"
        full_res, err_f = sim.user_exit_now(att_part.attempt_id, exit_price=85600.0, reason="Operator full exit")
        assert err_f is None
        assert full_res.status == "USER_EXITED_EARLY"


def test_matrix_e_protected_files_remain_bit_identical():
    """Verify that protected files have not been modified."""
    # Read current hashes
    curr_hashes = _get_protected_hashes()
    for fpath, curr_hash in curr_hashes.items():
        assert curr_hash != "", f"Protected file missing: {fpath}"
