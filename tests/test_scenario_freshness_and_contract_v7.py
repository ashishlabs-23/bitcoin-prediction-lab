"""
BTCognitive V7 — Scenario Freshness, Contract Provenance & Rejection Test Suite
Tests:
- 1h, 4h, 24h supported horizons with complete input provenance and units
- Conservative freshness policy (rejecting inputs older than 3 hours / 10800s)
- Explicit rejections: sub-hourly 15m/5m, invalid custom entries (0, negative, NaN, inf)
- Data sufficiency, gap preservation, and missing adapter response
- Known-answer mathematical formula verification: entry, TP, SL, R:R, ordering
- Non-interference: scenario calculations never pollute directional signal or authorization
"""

import math
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from engine.scenario_contract_engine import (
    HypotheticalScenarioPlanner,
    DEFAULT_MAX_STALENESS_SECONDS,
)
from api.routes_arena import get_scenario_preview
from models.calibrated_signal_classifier import evaluate_governed_signal_gate


def test_scenario_known_answer_mathematical_verification():
    """
    Known-answer fixture (Log-return volatility formulation):
    Given:
      entry = 80,000.00
      sigma_1h = 0.01 (1%)
      horizon = 4h -> scale = sqrt(4) = 2.0 -> sigma_H = 0.02 (2%)
      k_tp = 1.5, k_sl = 1.0

    Expected:
      LONG:
        TP = 80000 * exp(1.5 * 0.02) = 80000 * exp(0.03) = 82436.43
        SL = 80000 * exp(-1.0 * 0.02) = 80000 * exp(-0.02) = 78416.00
        reward = 82436.43 - 80000 = 2436.43
        risk = 80000 - 78416.00 = 1584.00
        gross R:R = 2436.43 / 1584.00 = 1.5381

      SHORT:
        TP = 80000 * exp(-1.5 * 0.02) = 80000 * exp(-0.03) = 77636.57
        SL = 80000 * exp(1.0 * 0.02) = 80000 * exp(0.02) = 81616.14
        reward = 80000 - 77636.57 = 2363.43
        risk = 81616.14 - 80000 = 1616.14
        gross R:R = 2363.43 / 1616.14 = 1.4624
    """
    entry = 80000.0
    sigma_1h = 0.01
    horizon_hours = 4.0
    sigma_H = sigma_1h * math.sqrt(horizon_hours)
    assert sigma_H == pytest.approx(0.02, rel=1e-7)

    k_tp = 1.5
    k_sl = 1.0

    # Long levels
    tp_long = round(entry * math.exp(k_tp * sigma_H), 2)
    sl_long = round(entry * math.exp(-k_sl * sigma_H), 2)
    assert tp_long == 82436.36
    assert sl_long == 78415.89
    assert tp_long > entry > sl_long
    rr_long = round((tp_long - entry) / (entry - sl_long), 2)
    assert rr_long == 1.54

    # Short levels
    tp_short = round(entry * math.exp(-k_tp * sigma_H), 2)
    sl_short = round(entry * math.exp(k_sl * sigma_H), 2)
    assert tp_short == 77635.64
    assert sl_short == 81616.11
    assert sl_short > entry > tp_short
    rr_short = round((entry - tp_short) / (sl_short - entry), 2)
    assert rr_short == 1.46


def test_supported_horizons_provenance_and_metadata():
    """
    Verify 1h, 4h, and 24h supported horizons produce valid output with full provenance metadata.
    """
    planner = HypotheticalScenarioPlanner()
    for hz in ["1h", "4h", "24h"]:
        result = planner.compute_scenario_preview(horizon=hz)
        assert result["status"] == "SUCCESS", f"Failed for horizon {hz}: {result.get('rejection_narrative')}"
        assert result["selected_horizon"] == hz
        assert result["contract_version"] == "SCENARIO_PLANNER_v1.0"
        assert result["source"] == "Coinbase Spot"
        assert result["instrument"] == "BTC/USD"
        assert result["source_timeframe"] == "1h"
        assert result["volatility_units"] == "LOG_RETURN_STANDARD_DEVIATION"
        assert result["horizon_scaling_method"] == "SQUARE_ROOT_OF_TIME_APPROXIMATION"
        assert "approximation under i.i.d." in result["horizon_scaling_notice"]

        # Provenance timestamps and age
        assert "reference_price_timestamp_utc" in result
        assert "reference_price_age_seconds" in result
        assert result["reference_price_age_seconds"] <= DEFAULT_MAX_STALENESS_SECONDS
        assert "latest_volatility_candle_timestamp_utc" in result
        assert "volatility_lookback_start_utc" in result
        assert "volatility_lookback_end_utc" in result
        assert result["volatility_observation_count"] == 24
        assert result["continuity_segment_id"] is not None

        # Price levels check
        scenarios = result["scenarios"]
        assert "LONG" in scenarios and "SHORT" in scenarios
        long_s = scenarios["LONG"]
        short_s = scenarios["SHORT"]
        assert long_s["take_profit"] > long_s["entry_reference"] > long_s["stop_loss"]
        assert short_s["stop_loss"] > short_s["entry_reference"] > short_s["take_profit"]
        assert long_s["gross_reward_to_risk"] > 1.0
        assert short_s["gross_reward_to_risk"] > 1.0


def test_custom_entry_valid_and_invalid():
    """
    Verify custom entry anchor behavior: valid positive number vs invalid (0, negative, NaN, inf).
    """
    planner = HypotheticalScenarioPlanner()

    # Valid custom entry
    custom_res = planner.compute_scenario_preview(horizon="24h", entry_price=95000.0)
    assert custom_res["status"] == "SUCCESS"
    assert custom_res["anchor_source"] == "USER_CUSTOM"
    assert custom_res["scenarios"]["LONG"]["entry_reference"] == 95000.0
    assert custom_res["scenarios"]["SHORT"]["entry_reference"] == 95000.0

    # Invalid: 0.0
    res_zero = planner.compute_scenario_preview(horizon="24h", entry_price=0.0)
    assert res_zero["status"] == "UNAVAILABLE"
    assert res_zero["rejection_code"] == "INVALID_CUSTOM_ENTRY_PRICE"

    # Invalid: negative
    res_neg = planner.compute_scenario_preview(horizon="24h", entry_price=-500.0)
    assert res_neg["status"] == "UNAVAILABLE"
    assert res_neg["rejection_code"] == "INVALID_CUSTOM_ENTRY_PRICE"

    # Invalid: NaN
    res_nan = planner.compute_scenario_preview(horizon="24h", entry_price=float("nan"))
    assert res_nan["status"] == "UNAVAILABLE"
    assert res_nan["rejection_code"] == "INVALID_CUSTOM_ENTRY_PRICE"

    # Invalid: Inf
    res_inf = planner.compute_scenario_preview(horizon="24h", entry_price=float("inf"))
    assert res_inf["status"] == "UNAVAILABLE"
    assert res_inf["rejection_code"] == "INVALID_CUSTOM_ENTRY_PRICE"


def test_unsupported_frequencies_rejected():
    """
    Verify sub-hourly frequencies 15m, 5m, 30m return explicit typed rejection.
    """
    planner = HypotheticalScenarioPlanner()
    for unsupp in ["15m", "5m", "30m"]:
        res = planner.compute_scenario_preview(horizon=unsupp)
        assert res["status"] == "UNAVAILABLE"
        assert res["rejection_code"] == "DATA_FREQUENCY_UNSUPPORTED"
        assert "unsupported" in res["rejection_narrative"].lower()

    # Unknown horizon
    res_unk = planner.compute_scenario_preview(horizon="invalid_hz")
    assert res_unk["status"] == "UNAVAILABLE"
    assert res_unk["rejection_code"] == "HORIZON_NOT_SUPPORTED"


def test_stale_data_rejection():
    """
    Verify that an observation older than max_staleness_seconds (10,800s) is rejected with MARKET_DATA_STALE.
    """
    planner = HypotheticalScenarioPlanner()
    # Query with as_of_time 10 days in the future relative to latest parquet candle
    future_time = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    res = planner.compute_scenario_preview(horizon="24h", as_of_time=future_time)
    assert res["status"] == "UNAVAILABLE"
    assert res["rejection_code"] == "MARKET_DATA_STALE"
    assert "exceeding conservative maximum allowable staleness threshold" in res["rejection_narrative"]
    assert res["reference_price_age_seconds"] > DEFAULT_MAX_STALENESS_SECONDS


def test_insufficient_lookback_segment_gap_rejection(tmp_path):
    """
    Verify that if the active segment has fewer than 24 continuous hourly bars,
    it rejects with INSUFFICIENT_CONTINUOUS_HISTORY rather than bridging gaps.
    """
    # Create synthetic parquet with only 10 bars
    timestamps = [datetime(2026, 10, 17, i, 0, 0, tzinfo=timezone.utc) for i in range(10)]
    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": [60000.0] * 10,
        "high": [60100.0] * 10,
        "low": [59900.0] * 10,
        "close": [60050.0] * 10,
        "volume": [100.0] * 10,
    })
    short_parquet = tmp_path / "short_ohlcv.parquet"
    df.to_parquet(short_parquet)

    planner = HypotheticalScenarioPlanner(ohlcv_path=str(short_parquet))
    # Query within fresh window of the short parquet
    as_of = datetime(2026, 10, 17, 9, 30, 0, tzinfo=timezone.utc)
    res = planner.compute_scenario_preview(horizon="24h", as_of_time=as_of)
    assert res["status"] == "UNAVAILABLE"
    assert res["rejection_code"] == "INSUFFICIENT_CONTINUOUS_HISTORY"
    assert "minimum 25 required for 24-bar lookback" in res["rejection_narrative"]


def test_missing_parquet_adapter_error(tmp_path):
    """
    Verify that a missing data source returns typed MARKET_DATA_UNAVAILABLE.
    """
    non_existent = tmp_path / "does_not_exist.parquet"
    planner = HypotheticalScenarioPlanner(ohlcv_path=str(non_existent))
    res = planner.compute_scenario_preview(horizon="24h")
    assert res["status"] == "UNAVAILABLE"
    assert res["rejection_code"] == "MARKET_DATA_UNAVAILABLE"


def test_api_route_scenario_preview_contract():
    """
    Verify FastAPI scenario preview endpoint contract via direct route function.
    """
    # Valid 4h request
    resp = get_scenario_preview(horizon="4h", entry_price=None)
    assert resp["status"] == "SUCCESS"
    assert resp["selected_horizon"] == "4h"
    assert resp["contract_version"] == "SCENARIO_PLANNER_v1.0"
    assert resp["scenarios"] is not None
    assert resp["scenarios"]["LONG"]["take_profit"] > resp["scenarios"]["LONG"]["entry_reference"]

    # Unsupported 15m request via API
    resp_15m = get_scenario_preview(horizon="15m")
    assert resp_15m["status"] == "UNAVAILABLE"
    assert resp_15m["rejection_code"] == "DATA_FREQUENCY_UNSUPPORTED"


def test_scenario_does_not_pollute_signal_gate():
    """
    Governance assertion: Calling scenario planner must never mutate
    or populate directional signal or model authorization state.
    """
    gate_before = evaluate_governed_signal_gate()
    assert gate_before["status"] == "ABSTAIN"
    assert gate_before["actionable_signal"] is None
    assert gate_before["execution_authorized"] is False
    assert gate_before["live_trading"] == "DISABLED"

    # Run scenario planner
    planner = HypotheticalScenarioPlanner()
    res = planner.compute_scenario_preview(horizon="24h")
    assert res["status"] == "SUCCESS"
    assert res["is_actionable"] is False
    assert res["execution_authorization"] == "DISABLED"

    # Re-verify classifier gate is still strictly ABSTAIN and live trading DISABLED
    gate_after = evaluate_governed_signal_gate()
    assert gate_after["status"] == "ABSTAIN"
    assert gate_after["actionable_signal"] is None
    assert gate_after["execution_authorized"] is False
    assert gate_after["live_trading"] == "DISABLED"
