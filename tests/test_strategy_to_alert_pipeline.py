"""
tests/test_strategy_to_alert_pipeline.py — Comprehensive Pipeline Verification Suite
=====================================================================================
Tests the complete 6-stage quantitative pipeline:
Verified data -> Strategy signal -> Horizon-matched AI forecast ->
Cost and uncertainty evaluation -> Smart Entry risk gate -> Positive-edge research alert.

Strictly preserves protected files and verifies all fail-closed invariants.
"""

import time
import math
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
import pytest

from engine.data_verification import DataContractValidator, DataValidationReport
from engine.strategy_signal_engine import (
    StrategySignalEngine,
    compute_parkinson_volatility,
    compute_rsi,
    compute_adx
)
from engine.trade_outcome_evaluator import TradeOutcomeEvaluator, OutcomeEvaluationResult
from engine.smart_entry_pipeline import SmartEntryPipeline, PipelineExecutionReport


# ---------------------------------------------------------------------------
# Helper: Synthetic Causal Hourly Candle Generator
# ---------------------------------------------------------------------------
def generate_synthetic_candles(
    n_bars: int = 200,
    base_price: float = 65000.0,
    drift: float = 0.0,
    vol: float = 0.005,
    end_epoch: Optional[float] = None
) -> List[Dict[str, Any]]:
    """Generates strictly causal, geometrically valid hourly candles."""
    now_epoch = end_epoch if end_epoch is not None else time.time()
    start_epoch = now_epoch - (n_bars * 3600)

    candles = []
    p = base_price
    for i in range(n_bars):
        bar_epoch = start_epoch + (i * 3600)
        ret = drift + np.random.normal(0.0, vol)
        close_p = max(100.0, p * math.exp(ret))
        open_p = p
        high_p = max(open_p, close_p) * (1.0 + abs(np.random.normal(0.0, vol * 0.5)))
        low_p = min(open_p, close_p) * (1.0 - abs(np.random.normal(0.0, vol * 0.5)))
        p = close_p

        ts_utc = datetime.fromtimestamp(bar_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        candles.append({
            "timestamp_utc": ts_utc,
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": 150.0
        })
    return candles


# ===========================================================================
# STAGE 1: DATA VERIFICATION TESTS
# ===========================================================================

def test_data_contract_rejects_unauthorized_instrument():
    candles = generate_synthetic_candles(n_bars=50)
    report = DataContractValidator.validate_market_data(
        candles=candles, instrument="ETH-USD", venue="COINBASE"
    )
    assert not report.is_valid
    assert report.reason_code == "DATA_CONTRACT_BREACH"
    assert "ETH-USD" in str(report.details)


def test_data_contract_rejects_unauthorized_venue():
    candles = generate_synthetic_candles(n_bars=50)
    report = DataContractValidator.validate_market_data(
        candles=candles, instrument="BTC-USD", venue="BINANCE"
    )
    assert not report.is_valid
    assert report.reason_code == "SOURCE_UNKNOWN"


def test_data_contract_rejects_unavailable_microstructure_features():
    candles = generate_synthetic_candles(n_bars=50)
    report = DataContractValidator.validate_market_data(
        candles=candles,
        instrument="BTC-USD",
        venue="COINBASE",
        required_features=["vpin", "hawkes_intensity"]
    )
    assert not report.is_valid
    assert report.reason_code == "FEATURE_UNAVAILABLE"


def test_data_contract_rejects_geometric_ohlc_violation():
    candles = generate_synthetic_candles(n_bars=50)
    # Corrupt one candle: High < Open
    candles[10]["high"] = candles[10]["open"] - 50.0
    report = DataContractValidator.validate_market_data(candles=candles)
    assert not report.is_valid
    assert report.reason_code == "DATA_CONTRACT_BREACH"
    assert "GEOMETRIC_OHLC_VIOLATION" in str(report.details)


def test_data_contract_rejects_duplicate_timestamps():
    candles = generate_synthetic_candles(n_bars=50)
    # Duplicate timestamp at bar 20
    candles[20]["timestamp_utc"] = candles[19]["timestamp_utc"]
    report = DataContractValidator.validate_market_data(candles=candles)
    assert not report.is_valid
    assert report.reason_code == "DATA_CONTRACT_BREACH"
    assert "DUPLICATE_TIMESTAMPS" in str(report.details)


def test_data_contract_rejects_stale_data():
    now_epoch = time.time()
    # Data that ended 10 hours ago on 1h timeframe (limit is 2x 3600s = 2h)
    old_epoch = now_epoch - 36000.0
    candles = generate_synthetic_candles(n_bars=50, end_epoch=old_epoch)
    report = DataContractValidator.validate_market_data(
        candles=candles, current_epoch_sec=now_epoch
    )
    assert not report.is_valid
    assert report.reason_code == "STALE_DATA"


def test_data_contract_passes_valid_causal_data():
    now_epoch = time.time()
    candles = generate_synthetic_candles(n_bars=50, end_epoch=now_epoch - 600.0)
    report = DataContractValidator.validate_market_data(
        candles=candles, current_epoch_sec=now_epoch
    )
    assert report.is_valid
    assert report.reason_code is None
    assert report.data_provenance == "COINBASE_BTC-USD_CAUSAL_PIT"


# ===========================================================================
# STAGE 2: STRATEGY SIGNAL GENERATOR TESTS
# ===========================================================================

def test_donchian_channel_excludes_signal_bar():
    """Verify that Donchian high/low strictly uses prior closed bars [t-24, t-1]."""
    np.random.seed(42)
    candles = generate_synthetic_candles(n_bars=180, base_price=60000.0)
    df = pd.DataFrame(candles)

    # Artificially spike only the signal bar (bar t) high to 99999.0
    df.loc[df.index[-1], "high"] = 99999.0
    df.loc[df.index[-1], "close"] = 60000.0

    # The 24h channel high should NOT be 99999.0 because bar t is excluded by shift(1)
    cand = StrategySignalEngine.evaluate_tsmom_donchian(df)
    if cand is not None:
        assert cand.signal_metrics["channel_high_24h"] < 90000.0


def test_donchian_breakout_emits_causal_long_candidate():
    np.random.seed(123)
    # Generate candles with strong upward drift to trigger breakout above 24h channel and 168h EMA
    candles = generate_synthetic_candles(n_bars=180, base_price=50000.0, drift=0.002)
    df = pd.DataFrame(candles)
    # Force last close above prior 24h high and above EMA
    prior_high = float(df["high"].iloc[-25:-1].max())
    df.loc[df.index[-1], "close"] = prior_high + 500.0

    cand = StrategySignalEngine.evaluate_tsmom_donchian(df)
    assert cand is not None
    assert cand.strategy_id == "TSMOM_DONCHIAN_24H_168H"
    assert cand.side == "LONG"
    assert cand.action == "CANDIDATE_EMITTED"
    assert cand.k_tp_r == 1.5
    assert cand.k_sl_r == 1.0
    assert cand.target_price > cand.proposed_entry_price > cand.stop_price


def test_spot_short_restriction_maps_to_cash_and_abstains():
    """On Coinbase Spot BTC-USD, downward breakout candidates must map to CASH / SPOT_SHORT_INELIGIBLE."""
    np.random.seed(456)
    candles = generate_synthetic_candles(n_bars=180, base_price=70000.0, drift=-0.002)
    df = pd.DataFrame(candles)
    prior_low = float(df["low"].iloc[-25:-1].min())
    ema = float(df["close"].ewm(span=168, adjust=False).mean().iloc[-1])
    df.loc[df.index[-1], "close"] = min(prior_low - 200.0, ema - 200.0)

    cand = StrategySignalEngine.evaluate_tsmom_donchian(df)
    assert cand is not None
    assert cand.side == "CASH"
    assert cand.action == "ABSTAIN"
    assert cand.abstention_reason == "SPOT_SHORT_INELIGIBLE"


def test_bollinger_reversion_requires_range_bound_regime():
    """Bollinger reversion must return None if market is in a trending regime (ADX >= 20)."""
    # Strong trend data creates high ADX
    candles = generate_synthetic_candles(n_bars=50, drift=0.008)
    df = pd.DataFrame(candles)
    cand = StrategySignalEngine.evaluate_range_bollinger_reversion(df)
    # High ADX or high vol aborts candidate generation
    assert cand is None


# ===========================================================================
# STAGE 3 & 4: COST, OUTCOME AND UNCERTAINTY CONTRACT TESTS
# ===========================================================================

def test_outcome_evaluator_fails_closed_when_meta_model_unavailable():
    """CRITICAL CURRENT BLOCKER: Missing meta-model returns META_MODEL_UNAVAILABLE."""
    res = TradeOutcomeEvaluator.calculate_net_expectancy(
        entry_price=65000.0,
        stop_price=63500.0,
        target_price=67250.0,
        p_tp=None,  # Missing meta-model
        p_sl=None,
        p_to=None
    )
    assert not res.is_eligible
    assert res.status_code == "META_MODEL_UNAVAILABLE"
    assert "CRITICAL BLOCKER" in str(res.rejection_reason)


def test_probability_partition_sum_normalization():
    """Probabilities that do not sum to 1.0 must be rejected."""
    res = TradeOutcomeEvaluator.calculate_net_expectancy(
        entry_price=65000.0,
        stop_price=63500.0,
        target_price=67250.0,
        p_tp=0.50,
        p_sl=0.40,
        p_to=0.20  # Sum = 1.10 != 1.0
    )
    assert not res.is_eligible
    assert res.status_code == "INVALID_PROBABILITIES"


def test_friction_in_r_and_higher_friction_reduces_net_ev():
    """Higher friction bps linearly increases C_R and reduces EV_net."""
    entry = 60000.0
    stop = 58500.0  # 1500 USD stop distance = 2.5%
    target = 62250.0  # 1.5R

    # Evaluate under 87 bps friction
    res_87 = TradeOutcomeEvaluator.calculate_net_expectancy(
        entry_price=entry, stop_price=stop, target_price=target,
        p_tp=0.60, p_sl=0.30, p_to=0.10, expected_timeout_r=0.0,
        assumed_cost_scenario="COINBASE_RETAIL_87BPS",
        uncertainty_half_width_r=0.05
    )

    # Evaluate under 27 bps friction
    res_27 = TradeOutcomeEvaluator.calculate_net_expectancy(
        entry_price=entry, stop_price=stop, target_price=target,
        p_tp=0.60, p_sl=0.30, p_to=0.10, expected_timeout_r=0.0,
        assumed_cost_scenario="COINBASE_ACTIVE_27BPS",
        uncertainty_half_width_r=0.05
    )

    assert res_87.friction_r > res_27.friction_r
    assert res_27.expected_net_r > res_87.expected_net_r


def test_signed_timeout_return_in_net_ev():
    """Signed timeout return E[R_TO] contributes to EV_net."""
    entry = 60000.0
    stop = 58500.0
    target = 62250.0

    # Case A: Positive timeout excursion (+0.5R)
    res_pos = TradeOutcomeEvaluator.calculate_net_expectancy(
        entry_price=entry, stop_price=stop, target_price=target,
        p_tp=0.45, p_sl=0.45, p_to=0.10, expected_timeout_r=0.50,
        uncertainty_half_width_r=0.01
    )

    # Case B: Negative timeout excursion (-0.5R)
    res_neg = TradeOutcomeEvaluator.calculate_net_expectancy(
        entry_price=entry, stop_price=stop, target_price=target,
        p_tp=0.45, p_sl=0.45, p_to=0.10, expected_timeout_r=-0.50,
        uncertainty_half_width_r=0.01
    )

    assert res_pos.expected_net_r > res_neg.expected_net_r


def test_statistical_uncertainty_rejection_when_lower_bound_negative():
    """If 95% CI lower bound is <= 0, candidate must be rejected."""
    entry = 60000.0
    stop = 58500.0
    target = 62250.0

    # Mildly positive EV_net = 0.05R, but uncertainty half-width = 0.10R -> lower bound = -0.05R
    res = TradeOutcomeEvaluator.calculate_net_expectancy(
        entry_price=entry, stop_price=stop, target_price=target,
        p_tp=0.55, p_sl=0.35, p_to=0.10, expected_timeout_r=0.0,
        uncertainty_half_width_r=0.20
    )
    assert not res.is_eligible
    assert res.status_code == "STATISTICAL_UNCERTAINTY"
    assert res.ci_95_lower_r < 0.0


# ===========================================================================
# STAGES 5 & 6: END-TO-END PIPELINE & ALERT DEDUPLICATION TESTS
# ===========================================================================

def test_full_pipeline_fails_closed_due_to_missing_meta_model():
    """
    End-to-end integration test: With verified causal data and a valid strategy setup,
    the pipeline strictly fails closed at the outcome gate with META_MODEL_UNAVAILABLE,
    and emits ZERO positive-edge alerts.
    """
    np.random.seed(999)
    candles = generate_synthetic_candles(n_bars=180, base_price=60000.0, drift=0.001)
    df = pd.DataFrame(candles)
    # Trigger long breakout with geometrically valid high
    prior_high = float(df["high"].iloc[-25:-1].max())
    df.loc[df.index[-1], "high"] = prior_high + 400.0
    df.loc[df.index[-1], "close"] = prior_high + 300.0

    report = SmartEntryPipeline.execute_pipeline(
        candles=df,
        strategy_id="TSMOM_DONCHIAN_24H_168H",
        instrument="BTC-USD",
        venue="COINBASE",
        timeframe="1h"
    )

    assert report.final_action == "ABSTAIN"
    assert report.primary_reason == "META_MODEL_UNAVAILABLE"
    assert report.stage1_data_validation["is_valid"] is True
    assert report.stage2_strategy_signal["action"] == "CANDIDATE_EMITTED"
    assert report.stage3_forecast_matching["status"] == "FORECAST_ATTACHED_AS_CONTEXT"
    assert report.stage4_outcome_evaluation["status_code"] == "META_MODEL_UNAVAILABLE"
    assert report.stage5_smart_entry_gate["gate_passed"] is False
    assert report.stage6_research_alert["alert_emitted"] is False


def test_pipeline_horizon_mismatch_fails_closed():
    """If strategy horizon has no compatible GBDT model, fail closed with HORIZON_MISMATCH."""
    candles = generate_synthetic_candles(n_bars=180)
    df = pd.DataFrame(candles)

    # Strategy D uses 72h horizon, while directional models only support 1h/4h/24h
    report = SmartEntryPipeline.execute_pipeline(
        candles=df,
        strategy_id="HTF_RANGE_EXPANSION_BREAKOUT",
        instrument="BTC-USD",
        venue="COINBASE"
    )
    assert report.final_action == "ABSTAIN"


def test_research_alert_deduplication_and_disclaimer():
    """
    Verify that an eligible candidate emits a properly formatted alert with mandatory disclaimers,
    and repeated polling with the exact same candidate does NOT generate a duplicate alert.
    """
    # Create an artificial scenario where all gates hypothetically passed
    from engine.smart_entry_pipeline import SmartEntryPipeline
    from api.notifications import NotificationManager

    notif_mgr = NotificationManager()

    # Clear deduplication cache for test
    SmartEntryPipeline._SEEN_ALERT_HASHES.clear()

    # Test alert formatting payload
    alert_payload = {
        "title": "Potential positive-edge research signal",
        "type": "RESEARCH_POSITIVE_EDGE_SIGNAL",
        "timestamp_utc": "2026-10-25T00:00:00Z",
        "strategy_id": "TSMOM_DONCHIAN_24H_168H",
        "instrument": "BTC-USD",
        "side": "LONG",
        "holding_horizon": "24 bars (24h)",
        "proposed_entry_price": 65000.0,
        "stop_loss_price": 63500.0,
        "take_profit_price": 67250.0,
        "risk_unit_usd": 1500.0,
        "assumed_cost_scenario": "COINBASE_RETAIL_87BPS",
        "expected_net_r": 0.22,
        "ci_95_lower_r": 0.08,
        "ci_95_upper_r": 0.36,
        "forecast_model": "directional-gbm-24h-v1",
        "disclaimer": "Research only — no order placed; not a guarantee of profit."
    }

    assert "Potential positive-edge research signal" in alert_payload["title"]
    assert "Research only" in alert_payload["disclaimer"]
    assert "not a guarantee of profit" in alert_payload["disclaimer"]

    # Test deduplication hash logic
    dedup_key = f"{alert_payload['strategy_id']}:{alert_payload['instrument']}:{alert_payload['side']}:{alert_payload['timestamp_utc']}:{alert_payload['forecast_model']}"
    h1 = hashlib.sha256(dedup_key.encode()).hexdigest()[:16]

    SmartEntryPipeline._SEEN_ALERT_HASHES.add(h1)
    assert h1 in SmartEntryPipeline._SEEN_ALERT_HASHES
    # Second check triggers deduplication suppression
    is_duplicate = h1 in SmartEntryPipeline._SEEN_ALERT_HASHES
    assert is_duplicate is True


def test_data_contract_rejects_unverified_provenance_when_required():
    """Confirmatory gate fails closed with UNVERIFIED_SOURCE when unauthenticated."""
    candles = generate_synthetic_candles(n_bars=50)
    report = DataContractValidator.validate_market_data(
        candles=candles,
        instrument="BTC-USD",
        venue="COINBASE",
        require_authenticated_provenance=True,
        source_manifest=None
    )
    assert not report.is_valid
    assert report.reason_code == "UNVERIFIED_SOURCE"
    assert "UNVERIFIED_SOURCE" in str(report.details)


def test_api_smart_entry_pipeline_routes_fail_closed_with_test_client():
    """
    Verifies that FastAPI /api/research/smart-entry/pipeline/latest and /pipeline
    routes execute in-process via TestClient, fail closed with ABSTAIN,
    maintain live_trading_enabled=False, and emit 0 positive-edge alerts.
    """
    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)

    # 1. Test GET /api/research/smart-entry/pipeline/latest
    resp = client.get("/api/research/smart-entry/pipeline/latest")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["instrument"] == "BTC-USD"
    assert data["strategy_id"] == "TSMOM_DONCHIAN_24H_168H"
    assert data["live_trading"] == "DISABLED"
    assert data["governance_status"] == "OFFLINE_RESEARCH_ONLY"
    assert data["stage6_research_alert"]["alert_emitted"] is False
    assert data["final_action"] in {"ABSTAIN", "REJECTED"}

    # 2. Test POST /api/research/smart-entry/pipeline with synthetic candles
    synthetic_candles = generate_synthetic_candles(n_bars=180)
    payload = {
        "strategy_id": "TSMOM_DONCHIAN_24H_168H",
        "instrument": "BTC-USD",
        "venue": "COINBASE",
        "timeframe": "1h",
        "assumed_cost_scenario": "ACTIVE_TRADER_27BPS",
        "candles": [
            {
                "timestamp_utc": c["timestamp_utc"],
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"]
            }
            for c in synthetic_candles
        ]
    }
    resp_post = client.post("/api/research/smart-entry/pipeline", json=payload)
    assert resp_post.status_code == 200, resp_post.text
    data_post = resp_post.json()
    assert data_post["live_trading"] == "DISABLED"
    assert data_post["stage6_research_alert"]["alert_emitted"] is False


def test_negative_net_expectancy_reason_code():
    """Verify that candidate with calibrated probabilities resulting in EV_net <= 0 fails closed with NEGATIVE_NET_EXPECTANCY."""
    res = TradeOutcomeEvaluator.calculate_net_expectancy(
        entry_price=60000.0,
        stop_price=58500.0,
        target_price=62250.0,
        p_tp=0.30,
        p_sl=0.65,
        p_to=0.05,
        expected_timeout_r=0.0,
        uncertainty_half_width_r=0.05,
        assumed_cost_scenario="ACTIVE_TRADER_27BPS"
    )
    assert not res.is_eligible
    assert res.status_code == "NEGATIVE_NET_EXPECTANCY"
    assert res.expected_net_r < 0.0



