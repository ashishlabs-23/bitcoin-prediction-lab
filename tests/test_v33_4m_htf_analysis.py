"""
BTCognitive — V33.4M-R: Analysis Consistency, Freshness Closure & HTF Setup Acceptance Suite.
========================================================================================
Comprehensive verification covering all 10 mandatory acceptance gates:
1. API and dashboard regime consistency for one analysis_id.
2. TRENDING_BEARISH is blocked with REGIME_MISMATCH_BEARISH.
3. VOLATILITY_EXPANSION follows its compatible-regime rules.
4. RANGE_BOUND is blocked with REGIME_MISMATCH_RANGE_BOUND.
5. TRANSITION_UNSUPPORTED is blocked with REGIME_TRANSITION_UNSUPPORTED.
6. A compatible regime without a breakout returns NO_SETUP.
7. Stale market data cannot be reported as a fresh current setup.
8. A complete, fresh candle can be evaluated using the frozen rules.
9. NO_SETUP does not misleadingly expose an active stop.
10. Analysis remains read-only and creates zero trade attempts.
"""

import sys
if sys.platform == "win33":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import pytest
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from starlette.testclient import TestClient

from api.server import app
from engine.canonical_regime_map import (
    normalize_regime,
    check_htf_regime_compatibility,
    CANONICAL_REGIMES,
    REGIME_ALIASES
)
from engine.htf_setup_detector import HTFSetupDetector
from engine.regime_strategy_tournament import (
    analyse_current_market,
    execute_integrated_analyse_and_tournament,
    formulate_smart_entry_decision,
    MarketRegimeClassifier,
    VersionedStrategyRegistry
)
from engine.htf_prospective_shadow_runner import HTFProspectiveShadowProtocol
from engine.historical_evidence_loader import HistoricalEvidenceLoader


@pytest.fixture
def client():
    return TestClient(app)


def generate_synthetic_1h_bars(
    num_bars: int = 120,
    base_price: float = 70000.0,
    trend_type: str = "bull",
    breakout_on_last_bar: bool = False,
    last_candle_age_seconds: float = 60.0
) -> pd.DataFrame:
    """Generates synthetic causal 1h OHLCV bars for scenario testing."""
    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    aligned_hour = (now_utc.hour // 4) * 4
    # Anchor start_time to a 4h boundary so complete buckets are cleanly formed
    start_time = now_utc.replace(hour=aligned_hour) - timedelta(hours=(num_bars // 4) * 4)

    timestamps = [start_time + timedelta(hours=i) for i in range(num_bars)]
    rows = []
    price = base_price

    for i in range(num_bars):
        if trend_type == "bull":
            drift = 50.0 + (i * 0.5)
        elif trend_type == "bear":
            drift = -50.0 - (i * 0.5)
        elif trend_type == "flat":
            drift = np.sin(i / 5.0) * 20.0
        else:
            drift = 0.0

        open_p = price
        close_p = open_p + drift
        high_p = max(open_p, close_p) + 40.0
        low_p = min(open_p, close_p) - 40.0

        # Inject breakout on final completed 4h candle if requested, or pullback inside range if not breakout
        if breakout_on_last_bar and i >= (num_bars - 4):
            high_p += 1500.0
            close_p += 1200.0
        elif (not breakout_on_last_bar) and i >= (num_bars - 8):
            # Controlled pullback so price is well inside the 20-bar channel (< 99% of range high)
            close_p = open_p - 150.0
            low_p = close_p - 50.0
            high_p = open_p + 10.0

        rows.append({
            "timestamp": timestamps[i].isoformat(),
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": 100.0 + (i % 20) * 5.0
        })
        price = close_p

    return pd.DataFrame(rows)


# =============================================================================
# Mandatory Acceptance Gate 1: API and Dashboard Regime Consistency
# =============================================================================
def test_acceptance_1_api_and_dashboard_regime_consistency(client):
    """Gate 1: An actual Analysis request returns identical canonical regime across API and dashboard."""
    resp = client.post("/api/tournament/analyse", json={
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "data_source": "SERVER_HISTORICAL_DATA",
        "auto_tournament": True
    })
    if resp.status_code == 503:
        from unittest.mock import patch
        from engine.bitstamp_market_data_service import BitstampMarketDataService
        mock_df = generate_synthetic_1h_bars(num_bars=200, trend_type="bull", breakout_on_last_bar=False)
        mock_meta = {
            "status": "VALID",
            "provider": "BITSTAMP",
            "symbol": "BTCUSD",
            "timeframe": "1h",
            "bar_count": len(mock_df),
            "data_freshness_status": "FRESH",
            "data_age_seconds": 120.0,
            "is_stale": False,
            "first_timestamp_utc": str(mock_df.index[0]),
            "last_completed_candle_utc": str(mock_df.index[-1]),
            "storage_mode": "PARQUET_AUDITED"
        }
        with patch.object(BitstampMarketDataService, "get_or_refresh_bitstamp_data", return_value=(True, mock_df, mock_meta)):
            resp = client.post("/api/tournament/analyse", json={
                "instrument": "BTC-USD",
                "timeframe": "1h",
                "data_source": "SERVER_HISTORICAL_DATA",
                "auto_tournament": True
            })
    assert resp.status_code == 200
    data = resp.json()

    # Capture and verify required trace parameters
    analysis_id = data.get("analysis_id")
    assert analysis_id is not None and analysis_id.startswith("ana_")

    timestamp_utc = data.get("timestamp_utc")
    assert timestamp_utc is not None

    watermark = data.get("candle_watermark")
    assert watermark is not None
    assert watermark.get("candle_watermark_hash") is not None

    raw_regime = data.get("market_regime", {}).get("regime")
    canonical_regime = data.get("regime")
    assert raw_regime is not None
    assert canonical_regime == raw_regime
    assert data["htf_setup"]["regime"] == canonical_regime

    if canonical_regime == "TRENDING_BEARISH":
        # Incompatible bearish regime must be BLOCKED
        assert data["setup_status"] == "BLOCKED"
        assert data["htf_setup"]["setup_status"] == "BLOCKED"
        assert "REGIME_MISMATCH_BEARISH" in data["reason_codes"]
        assert "REGIME_MISMATCH_BEARISH" in data["htf_setup"]["reason_codes"]

    # Active stop reference must be None for blocked setup
    assert data["stop_reference"] is None
    assert data["htf_setup"]["stop_reference"] is None


# =============================================================================
# Mandatory Acceptance Gate 2: TRENDING_BEARISH is Blocked
# =============================================================================
def test_acceptance_2_trending_bearish_is_blocked():
    """Gate 2: TRENDING_BEARISH is strictly BLOCKED with REGIME_MISMATCH_BEARISH and stop_reference is None."""
    df_1h = generate_synthetic_1h_bars(num_bars=120, trend_type="bear", breakout_on_last_bar=True)
    res = HTFSetupDetector.detect_setup(
        df_1h=df_1h,
        observed_regime="TRENDING_BEARISH",
        is_data_stale=False,
        enforce_stale_blocking=False
    )

    assert res["setup_status"] == "BLOCKED"
    assert res["regime"] == "TRENDING_BEARISH"
    assert res["regime_confirmed"] is False
    assert "REGIME_MISMATCH_BEARISH" in res["reason_codes"]
    assert "BLOCKED_BY_REGIME_TRENDING_BEARISH" in res["reason_codes"]
    assert res["stop_reference"] is None
    assert res["entry_reference"] is None
    assert res["target_reference"] is None


# =============================================================================
# Mandatory Acceptance Gate 3: VOLATILITY_EXPANSION Follows Compatible Rules
# =============================================================================
def test_acceptance_3_volatility_expansion_compatible_rules():
    """Gate 3: VOLATILITY_EXPANSION is compatible: breakout returns SHADOW_CANDIDATE, inside range returns NO_SETUP."""
    # Sub-case A: With Breakout
    df_breakout = generate_synthetic_1h_bars(num_bars=120, trend_type="bull", breakout_on_last_bar=True)
    res_breakout = HTFSetupDetector.detect_setup(
        df_1h=df_breakout,
        observed_regime="VOLATILITY_EXPANSION",
        is_data_stale=False,
        enforce_stale_blocking=False
    )
    assert res_breakout["setup_status"] == "SHADOW_CANDIDATE"
    assert res_breakout["trigger_status"] == "TRIGGER_CONFIRMED"
    assert res_breakout["regime"] == "VOLATILITY_EXPANSION"
    assert res_breakout["regime_confirmed"] is True
    assert res_breakout["entry_reference"] is not None and res_breakout["entry_reference"] > 0
    assert res_breakout["stop_reference"] is not None and res_breakout["stop_reference"] < res_breakout["entry_reference"]
    assert res_breakout["target_reference"] is not None and res_breakout["target_reference"] > res_breakout["entry_reference"]
    assert "HTF_BREAKOUT_TRIGGER_CONFIRMED" in res_breakout["reason_codes"]

    # Sub-case B: Inside Range without Breakout
    df_inside = generate_synthetic_1h_bars(num_bars=120, trend_type="bull", breakout_on_last_bar=False)
    res_inside = HTFSetupDetector.detect_setup(
        df_1h=df_inside,
        observed_regime="VOLATILITY_EXPANSION",
        is_data_stale=False,
        enforce_stale_blocking=False
    )
    assert res_inside["setup_status"] == "NO_SETUP"
    assert res_inside["trigger_status"] == "UNBREACHED"
    assert res_inside["regime_confirmed"] is True
    assert res_inside["stop_reference"] is None
    assert res_inside["entry_reference"] is None
    assert "NO_HTF_BREAKOUT_CONDITION" in res_inside["reason_codes"]


# =============================================================================
# Mandatory Acceptance Gate 4: RANGE_BOUND is Blocked
# =============================================================================
def test_acceptance_4_range_bound_is_blocked():
    """Gate 4: RANGE_BOUND is strictly BLOCKED with REGIME_MISMATCH_RANGE_BOUND and stop_reference is None."""
    df_1h = generate_synthetic_1h_bars(num_bars=120, trend_type="flat", breakout_on_last_bar=True)
    res = HTFSetupDetector.detect_setup(
        df_1h=df_1h,
        observed_regime="RANGE_BOUND",
        is_data_stale=False,
        enforce_stale_blocking=False
    )

    assert res["setup_status"] == "BLOCKED"
    assert res["regime"] == "RANGE_BOUND"
    assert res["regime_confirmed"] is False
    assert "REGIME_MISMATCH_RANGE_BOUND" in res["reason_codes"]
    assert "BLOCKED_BY_REGIME_RANGE_BOUND" in res["reason_codes"]
    assert res["stop_reference"] is None
    assert res["entry_reference"] is None


# =============================================================================
# Mandatory Acceptance Gate 5: TRANSITION_UNSUPPORTED is Blocked
# =============================================================================
def test_acceptance_5_transition_unsupported_is_blocked():
    """Gate 5: TRANSITION_UNSUPPORTED is strictly BLOCKED with REGIME_TRANSITION_UNSUPPORTED."""
    df_1h = generate_synthetic_1h_bars(num_bars=120, trend_type="bull", breakout_on_last_bar=True)
    res = HTFSetupDetector.detect_setup(
        df_1h=df_1h,
        observed_regime="TRANSITION_UNSUPPORTED",
        is_data_stale=False,
        enforce_stale_blocking=False
    )

    assert res["setup_status"] == "BLOCKED"
    assert res["regime"] == "TRANSITION_UNSUPPORTED"
    assert res["regime_confirmed"] is False
    assert "REGIME_TRANSITION_UNSUPPORTED" in res["reason_codes"]
    assert "BLOCKED_BY_REGIME_TRANSITION_UNSUPPORTED" in res["reason_codes"]
    assert res["stop_reference"] is None
    assert res["entry_reference"] is None


# =============================================================================
# Mandatory Acceptance Gate 6: Compatible Regime Without Breakout Returns NO_SETUP
# =============================================================================
def test_acceptance_6_compatible_regime_without_breakout_returns_no_setup():
    """Gate 6: A compatible regime (TRENDING_BULLISH) without breakout returns NO_SETUP."""
    df_1h = generate_synthetic_1h_bars(num_bars=120, trend_type="bull", breakout_on_last_bar=False)
    res = HTFSetupDetector.detect_setup(
        df_1h=df_1h,
        observed_regime="TRENDING_BULLISH",
        is_data_stale=False,
        enforce_stale_blocking=False
    )

    assert res["setup_status"] == "NO_SETUP"
    assert res["trigger_status"] == "UNBREACHED"
    assert res["regime"] == "TRENDING_BULLISH"
    assert res["regime_confirmed"] is True
    assert "NO_HTF_BREAKOUT_CONDITION" in res["reason_codes"]
    assert res["entry_reference"] is None
    assert res["stop_reference"] is None
    assert res["target_reference"] is None


# =============================================================================
# Mandatory Acceptance Gate 7: Stale Market Data Cannot Be Reported as Fresh
# =============================================================================
def test_acceptance_7_stale_market_data_cannot_be_reported_as_fresh():
    """Gate 7: Stale market data (> 2.0h old) is strictly BLOCKED with STALE_MARKET_DATA_BLOCKED."""
    df_1h = generate_synthetic_1h_bars(num_bars=120, trend_type="bull", breakout_on_last_bar=True)
    res = HTFSetupDetector.detect_setup(
        df_1h=df_1h,
        observed_regime="TRENDING_BULLISH",
        is_data_stale=True,
        observed_age_hours=72.3,
        enforce_stale_blocking=True
    )

    assert res["setup_status"] == "BLOCKED"
    assert res["trigger_status"] == "STALE_DATA_BLOCKED"
    assert res["data_freshness_status"] == "MARKET_DATA_STALE"
    assert res["data_age_hours"] == 72.3
    assert res["last_observed_timestamp_utc"] is not None
    assert "STALE_MARKET_DATA_BLOCKED" in res["reason_codes"]
    assert res["entry_reference"] is None
    assert res["stop_reference"] is None
    assert res["target_reference"] is None


# =============================================================================
# Mandatory Acceptance Gate 8: Complete Fresh Candle Evaluated under Frozen Rules
# =============================================================================
def test_acceptance_8_complete_fresh_candle_evaluated_using_frozen_rules():
    """Gate 8: Complete fresh 4h candle under TRENDING_BULLISH evaluates valid breakout under frozen rules."""
    df_1h = generate_synthetic_1h_bars(num_bars=120, trend_type="bull", breakout_on_last_bar=True)
    res = HTFSetupDetector.detect_setup(
        df_1h=df_1h,
        observed_regime="TRENDING_BULLISH",
        is_data_stale=False,
        observed_age_hours=0.5,
        enforce_stale_blocking=True
    )

    assert res["setup_status"] == "SHADOW_CANDIDATE"
    assert res["trigger_status"] == "TRIGGER_CONFIRMED"
    assert res["data_freshness_status"] == "FRESH"
    assert res["entry_reference"] is not None
    assert res["stop_reference"] is not None
    assert res["target_reference"] is not None
    assert res["risk_reward_ratio"] == 1.5
    assert res["holding_horizon_bars"] == 18
    assert res["holding_horizon_hours"] == 72.0
    assert "HTF_BREAKOUT_TRIGGER_CONFIRMED" in res["reason_codes"]
    assert "SHADOW_RESEARCH_QUALIFIED" in res["reason_codes"]


# =============================================================================
# Mandatory Acceptance Gate 9: NO_SETUP Does Not Misleadingly Expose Active Stop
# =============================================================================
def test_acceptance_9_no_setup_does_not_misleadingly_expose_active_stop():
    """Gate 9: NO_SETUP does not expose active stop_reference; Donchian bounds are clearly named."""
    df_1h = generate_synthetic_1h_bars(num_bars=120, trend_type="bull", breakout_on_last_bar=False)
    res = HTFSetupDetector.detect_setup(
        df_1h=df_1h,
        observed_regime="TRENDING_BULLISH",
        is_data_stale=False,
        enforce_stale_blocking=False
    )

    assert res["setup_status"] == "NO_SETUP"
    # Stop reference must be strictly None (NOT Donchian low)
    assert res["stop_reference"] is None
    assert res["entry_reference"] is None
    assert res["target_reference"] is None

    # Donchian channel bounds must be explicitly and clearly named in completed_4h_bar
    bar = res["completed_4h_bar"]
    assert "donchian_channel_high_20_4h" in bar
    assert "donchian_channel_low_20_4h" in bar
    assert bar["donchian_channel_high_20_4h"] > bar["donchian_channel_low_20_4h"]


# =============================================================================
# Mandatory Acceptance Gate 10: Analysis Remains Read-Only with Zero Trade Attempts
# =============================================================================
def test_acceptance_10_analysis_remains_readonly_zero_trade_attempts(client):
    """Gate 10: Analysis creates zero trade attempts, is_read_only is True, and live trading is disabled."""
    resp = client.post("/api/tournament/analyse", json={
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "data_source": "SERVER_HISTORICAL_DATA",
        "auto_tournament": True
    })
    if resp.status_code == 503:
        from unittest.mock import patch
        from engine.bitstamp_market_data_service import BitstampMarketDataService
        mock_df = generate_synthetic_1h_bars(num_bars=200, trend_type="bull", breakout_on_last_bar=False)
        mock_meta = {
            "status": "VALID",
            "provider": "BITSTAMP",
            "symbol": "BTCUSD",
            "timeframe": "1h",
            "bar_count": len(mock_df),
            "data_freshness_status": "FRESH",
            "data_age_seconds": 120.0,
            "is_stale": False,
            "first_timestamp_utc": str(mock_df.index[0]),
            "last_completed_candle_utc": str(mock_df.index[-1]),
            "storage_mode": "PARQUET_AUDITED"
        }
        with patch.object(BitstampMarketDataService, "get_or_refresh_bitstamp_data", return_value=(True, mock_df, mock_meta)):
            resp = client.post("/api/tournament/analyse", json={
                "instrument": "BTC-USD",
                "timeframe": "1h",
                "data_source": "SERVER_HISTORICAL_DATA",
                "auto_tournament": True
            })
    assert resp.status_code == 200
    data = resp.json()

    assert data["attempts_created"] == 0
    assert data["is_read_only"] is True
    assert data["authorization_status"] == "OFFLINE_RESEARCH_ONLY"

    health = client.get("/health").json()
    assert health["live_trading_enabled"] is False
    assert health["order_submission_enabled"] is False
    assert health["execution_status"] == "DISABLED_ANALYSIS_ONLY"
    assert health["trading_enabled"] is False


# =============================================================================
# Incomplete 4h Candle and Market Intelligence Independence
# =============================================================================
def test_incomplete_4h_candle_aggregation():
    """Verify that incomplete 4h bucket (e.g. 2/4 bars) is causally segregated."""
    df_1h = generate_synthetic_1h_bars(num_bars=122, trend_type="bull", breakout_on_last_bar=False)
    df_4h, incomplete_info = HTFSetupDetector.aggregate_completed_4h_candles(df_1h)

    assert df_4h is not None
    assert len(df_4h) == 30
    assert incomplete_info is not None
    assert incomplete_info["bars_present"] == 2
    assert incomplete_info["bars_required"] == 4


def test_market_intelligence_success_independent():
    """Market Intelligence succeeds independently and distinguishes calculation from freshness."""
    df_1h = generate_synthetic_1h_bars(num_bars=200, trend_type="flat", breakout_on_last_bar=False)
    res = execute_integrated_analyse_and_tournament(df_1h=df_1h, live_price=70000.0, enforce_freshness=False)

    assert "market_intelligence" in res
    mi = res["market_intelligence"]
    assert mi["status"] == "SUCCESS"
    assert mi["calculation_status"] == "SUCCESS"
    assert mi["volatility_term_structure"] is not None
    assert res["setup_status"] in ["NO_SETUP", "SETUP_FORMING", "BLOCKED"]


def test_canonical_regime_taxonomy():
    """Verify bidirectional normalization and compatibility of the canonical regime taxonomy."""
    assert normalize_regime("TRENDING_BULL") == "TRENDING_BULLISH"
    assert normalize_regime("TRENDING_BULLISH") == "TRENDING_BULLISH"
    is_compat, canon, _ = check_htf_regime_compatibility("TRENDING_BULL")
    assert is_compat is True
    assert canon == "TRENDING_BULLISH"

    assert normalize_regime("TRENDING_BEAR") == "TRENDING_BEARISH"
    is_compat, canon, _ = check_htf_regime_compatibility("TRENDING_BEAR")
    assert is_compat is False

    assert normalize_regime("CONSOLIDATION_RANGE") == "RANGE_BOUND"
    is_compat, canon, _ = check_htf_regime_compatibility("CONSOLIDATION_RANGE")
    assert is_compat is False

    assert normalize_regime("TRANSITION_PENDING") == "TRANSITION_UNSUPPORTED"
    is_compat, canon, _ = check_htf_regime_compatibility("TRANSITION_UNSUPPORTED")
    assert is_compat is False
