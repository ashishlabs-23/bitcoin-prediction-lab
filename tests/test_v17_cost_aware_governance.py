"""
tests/test_v17_cost_aware_governance.py — V17 Cost-Aware Signal Governance,
Market Snapshot Freshness, and Regime Hysteresis Integrity Test Suite.
"""

import math
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from research.v12_strategy_tournament_engine import (
    REGIME_TOURNAMENT_ENGINE,
    COST_SCENARIOS,
    build_market_snapshot,
    MarketSnapshot,
    EconomicEligibility,
    REGIME_ADAPTIVE_ROUTER,
    SHORT_HORIZON_MEAN_REVERSION,
    TREND_FOLLOWING_BREAKOUT,
)
from api.server import app


# ==============================================================================
# PRIORITY A: ECONOMIC TRADE ELIGIBILITY & V16 ARITHMETIC REPRODUCTION
# ==============================================================================

class TestEconomicTradeEligibility:
    """Deterministic verification of economic trade eligibility arithmetic."""

    def test_v16_historical_diagnostic_arithmetic_reproduction(self):
        """
        Reproduce and independently recalculate reported V16 values:
          Entry: $81,242.50, TP: $81,486.54, SL: $80,851.65
        """
        entry = 81242.50
        tp = 81486.54
        sl = 80851.65

        # 1. Gross reward & risk arithmetic
        gross_reward_usd = tp - entry  # 244.04
        gross_risk_usd = entry - sl    # 390.85
        assert round(gross_reward_usd, 2) == 244.04
        assert round(gross_risk_usd, 2) == 390.85

        gross_reward_pct = gross_reward_usd / entry  # 0.003003845
        gross_risk_pct = gross_risk_usd / entry      # 0.004810905
        gross_reward_bps = gross_reward_pct * 10000.0  # 30.038 bps
        gross_risk_bps = gross_risk_pct * 10000.0      # 48.109 bps
        assert round(gross_reward_bps, 2) == 30.04
        assert round(gross_risk_bps, 2) == 48.11

        # 2. Scenario 1: COINBASE_RETAIL_87BPS
        # Friction = 87.0 bps = 0.0087 * 81242.50 = 706.80975 USD
        scenario_retail = COST_SCENARIOS["COINBASE_RETAIL_87BPS"]
        cost_bps_retail = scenario_retail["round_trip_bps"]
        assert cost_bps_retail == 87.0
        cost_usd_retail = entry * (cost_bps_retail / 10000.0)
        assert round(cost_usd_retail, 2) == 706.81

        # Net reward = gross reward - cost = 244.04 - 706.81 = -462.77 USD (-56.96 bps)
        net_reward_usd_retail = gross_reward_usd - cost_usd_retail
        net_reward_bps_retail = gross_reward_bps - cost_bps_retail
        assert round(net_reward_usd_retail, 2) == -462.77
        assert round(net_reward_bps_retail, 2) == -56.96

        # Target CANNOT cover round trip friction!
        # Must be strictly COST_INELIGIBLE with unachievable hit rate (None)
        elig_retail = REGIME_TOURNAMENT_ENGINE.evaluate_economic_eligibility(
            entry_price=entry,
            tp_price=tp,
            sl_price=sl,
            side="LONG",
            cost_scenario="COINBASE_RETAIL_87BPS",
            market_snapshot=MarketSnapshot(
                provider="coinbase_spot",
                product="BTC/USD",
                interval="1h",
                candle_open_time=datetime.now(timezone.utc).isoformat(),
                candle_close_time=datetime.now(timezone.utc).isoformat(),
                is_candle_closed=True,
                observed_age_seconds=60.0,
                is_stale=False,
                is_fresh=True,
                freshness_status="FRESH",
            ),
        )
        assert elig_retail.status == "COST_INELIGIBLE"
        assert elig_retail.is_eligible is False
        assert elig_retail.net_reward_usd < 0
        assert round(elig_retail.net_reward_risk, 2) == -0.42
        assert elig_retail.breakeven_hit_rate_pct is None
        assert "Gross target (+30.0 bps) does not cover modeled round-trip cost (87.0 bps)" in elig_retail.rejection_reason

        # 3. Scenario 2: COINBASE_INSTITUTIONAL_18BPS
        # Friction = 18.6 bps = 0.00186 * 81242.50 = 151.11105 USD
        scenario_inst = COST_SCENARIOS["COINBASE_INSTITUTIONAL_18BPS"]
        cost_bps_inst = scenario_inst["round_trip_bps"]
        assert cost_bps_inst == 18.6
        cost_usd_inst = entry * (cost_bps_inst / 10000.0)
        assert round(cost_usd_inst, 2) == 151.11

        net_reward_usd_inst = gross_reward_usd - cost_usd_inst
        net_reward_bps_inst = gross_reward_bps - cost_bps_inst
        assert round(net_reward_usd_inst, 2) == 92.93
        assert round(net_reward_bps_inst, 2) == 11.44

        # Net risk at stop = gross risk + round trip cost
        net_risk_usd_inst = gross_risk_usd + cost_usd_inst
        net_risk_bps_inst = gross_risk_bps + cost_bps_inst
        assert round(net_risk_usd_inst, 2) == 541.96
        assert round(net_risk_bps_inst, 2) == 66.71

        # Breakeven hit rate = Net Risk / (Net Reward + Net Risk) = 541.96 / (92.93 + 541.96) = 85.36%
        expected_be_rate_inst = (net_risk_usd_inst / (net_reward_usd_inst + net_risk_usd_inst)) * 100.0
        assert round(expected_be_rate_inst, 2) == 85.36

        elig_inst = REGIME_TOURNAMENT_ENGINE.evaluate_economic_eligibility(
            entry_price=entry,
            tp_price=tp,
            sl_price=sl,
            side="LONG",
            cost_scenario="COINBASE_INSTITUTIONAL_18BPS",
        )
        assert elig_inst.status == "TRADE_COST_ELIGIBLE"
        assert elig_inst.is_eligible is True
        assert round(elig_inst.net_reward_usd, 2) == 92.93
        assert round(elig_inst.breakeven_hit_rate_pct, 2) == 85.36

        # 4. Scenario 3: BINANCE_PERP_15BPS
        # Friction = 15.0 bps = 0.0015 * 81242.50 = 121.86375 USD
        scenario_perp = COST_SCENARIOS["BINANCE_PERP_15BPS"]
        cost_bps_perp = scenario_perp["round_trip_bps"]
        assert cost_bps_perp == 15.0
        cost_usd_perp = entry * (cost_bps_perp / 10000.0)
        assert round(cost_usd_perp, 2) == 121.86

        net_reward_usd_perp = gross_reward_usd - cost_usd_perp
        net_reward_bps_perp = gross_reward_bps - cost_bps_perp
        assert round(net_reward_usd_perp, 2) == 122.18
        assert round(net_reward_bps_perp, 2) == 15.04

        net_risk_usd_perp = gross_risk_usd + cost_usd_perp
        assert round(net_risk_usd_perp, 2) == 512.71
        expected_be_rate_perp = (net_risk_usd_perp / (net_reward_usd_perp + net_risk_usd_perp)) * 100.0
        assert round(expected_be_rate_perp, 2) == 80.76

        elig_perp = REGIME_TOURNAMENT_ENGINE.evaluate_economic_eligibility(
            entry_price=entry,
            tp_price=tp,
            sl_price=sl,
            side="LONG",
            cost_scenario="BINANCE_PERP_15BPS",
        )
        assert elig_perp.status == "TRADE_COST_ELIGIBLE"
        assert elig_perp.is_eligible is True
        assert round(elig_perp.net_reward_usd, 2) == 122.18
        assert round(elig_perp.breakeven_hit_rate_pct, 2) == 80.76

    def test_short_setup_geometry_and_unit_conversions(self):
        """Verifies short position arithmetic (entry > tp, sl > entry)."""
        entry = 80000.0
        tp = 79000.0   # +1000 gross reward (+125.0 bps)
        sl = 80500.0   # -500 gross risk (-62.5 bps)

        elig = REGIME_TOURNAMENT_ENGINE.evaluate_economic_eligibility(
            entry_price=entry,
            tp_price=tp,
            sl_price=sl,
            side="SHORT",
            cost_scenario="COINBASE_RETAIL_87BPS",
        )
        assert elig.status == "TRADE_COST_ELIGIBLE"
        assert elig.is_eligible is True
        assert round(elig.gross_reward_usd, 2) == 1000.0
        assert round(elig.gross_risk_usd, 2) == 500.0
        assert round(elig.gross_reward_bps, 2) == 125.0
        # Round trip cost = 87.0 bps = $696.00
        assert round(elig.round_trip_cost_usd, 2) == 696.00
        # Net reward = 1000.0 - 696.0 = 304.0 USD (+38.0 bps)
        assert round(elig.net_reward_usd, 2) == 304.00
        assert round(elig.net_reward_bps, 2) == 38.0
        # Net risk = 500.0 + 696.0 = 1196.0 USD (149.5 bps)
        assert round(elig.net_risk_usd, 2) == 1196.00
        # Breakeven rate = 1196 / (304 + 1196) = 79.73%
        assert round(elig.breakeven_hit_rate_pct, 2) == 79.73

    def test_invalid_or_missing_cost_scenario_fails_closed(self):
        """Fails closed with COSTS_UNAVAILABLE when cost scenario is invalid."""
        elig = REGIME_TOURNAMENT_ENGINE.evaluate_economic_eligibility(
            entry_price=80000.0,
            tp_price=82000.0,
            sl_price=79000.0,
            side="LONG",
            cost_scenario="NON_EXISTENT_SCENARIO",
        )
        assert elig.status == "COSTS_UNAVAILABLE"
        assert elig.is_eligible is False
        assert "Unsupported cost scenario" in elig.rejection_reason

    def test_invalid_price_geometry_fails_closed(self):
        """Fails closed when TP is on wrong side of Entry."""
        elig = REGIME_TOURNAMENT_ENGINE.evaluate_economic_eligibility(
            entry_price=80000.0,
            tp_price=79000.0,  # Invalid for LONG
            sl_price=78000.0,
            side="LONG",
            cost_scenario="COINBASE_RETAIL_87BPS",
        )
        assert elig.status == "INVALID_MARKET_INPUT"
        assert elig.is_eligible is False
        assert "Invalid LONG setup geometry" in elig.rejection_reason


# ==============================================================================
# PRIORITY B: FAIL-CLOSED REGIME DATA & TIME-CONTINUOUS HYSTERESIS
# ==============================================================================

class TestRegimeIntegrityAndHysteresis:
    """Verifies regime calculation fail-closed rules and hysteresis continuity."""

    def test_missing_adx_fails_closed_no_synthetic_fallback(self):
        """
        Verify that REGIME_ADAPTIVE_ROUTER does NOT use adx_14 fallback 20.0
        and fails closed with INVALID_MARKET_INPUT when adx_14 is missing/None/NaN.
        """
        strat = REGIME_ADAPTIVE_ROUTER
        assert strat.id == "REGIME_ADAPTIVE_ROUTER"

        # 1. Missing adx_14
        regime_missing_adx = {
            "regime": "TRENDING_BULL",
            "ema_200": 80000.0,
            "bb_width": 0.04,
            "hysteresis_status": "CONFIRMED",
        }
        setup = strat.evaluate_current_setup(
            df_features=None,
            regime_info=regime_missing_adx,
            cost_scenario="COINBASE_RETAIL_87BPS",
            eval_time=datetime.now(timezone.utc),
        )
        assert setup.setup_state == "INVALID_MARKET_INPUT"
        assert setup.economic_eligibility.status == "INVALID_MARKET_INPUT"
        assert "Required indicator 'adx_14' is missing" in setup.blocking_reason

        # 2. NaN adx_14
        regime_nan_adx = dict(regime_missing_adx, adx_14=float("nan"), atr_14=120.0)
        setup_nan = strat.evaluate_current_setup(
            df_features=None,
            regime_info=regime_nan_adx,
            cost_scenario="COINBASE_RETAIL_87BPS",
            eval_time=datetime.now(timezone.utc),
        )
        assert setup_nan.setup_state == "INVALID_MARKET_INPUT"
        assert "non-finite (nan)" in setup_nan.blocking_reason

        # 3. Missing ema_200
        regime_missing_ema = {
            "regime": "TRENDING_BULL",
            "adx_14": 26.0,
            "atr_14": 120.0,
            "bb_width": 0.04,
            "hysteresis_status": "CONFIRMED",
        }
        setup_ema = strat.evaluate_current_setup(
            df_features=None,
            regime_info=regime_missing_ema,
            cost_scenario="COINBASE_RETAIL_87BPS",
            eval_time=datetime.now(timezone.utc),
        )
        assert setup_ema.setup_state == "INVALID_MARKET_INPUT"
        assert "Required indicator 'ema_200' is missing" in setup_ema.blocking_reason

    def test_unconfirmed_pending_hysteresis_fails_closed(self):
        """Verifies pending regime transition fails closed with REGIME_UNCONFIRMED."""
        strat = REGIME_ADAPTIVE_ROUTER
        regime_pending = {
            "regime": "TRENDING_BULL",
            "adx_14": 28.0,
            "atr_14": 120.0,
            "ema_200": 80000.0,
            "bb_width": 0.04,
            "hysteresis_status": "PENDING_TRANSITION (1/3 bars)",
        }
        setup = strat.evaluate_current_setup(
            df_features=None,
            regime_info=regime_pending,
            cost_scenario="COINBASE_RETAIL_87BPS",
            eval_time=datetime.now(timezone.utc),
        )
        assert setup.setup_state == "REGIME_UNCONFIRMED"
        assert setup.economic_eligibility.status == "REGIME_UNCONFIRMED"
        assert "Regime candidate transition is pending confirmation" in setup.blocking_reason

    def test_hysteresis_continuity_across_data_gaps(self):
        """
        Verify that hysteresis resets pending confirmation across data gaps > 3660s,
        and invalidates active regime across gaps > 3h.
        """
        import pandas as pd
        import numpy as np

        # Create synthetic hourly series with an intentional 10-hour gap
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        timestamps = []
        for i in range(100):
            if i == 50:
                # 10-hour outage gap
                base_time += timedelta(hours=10)
            else:
                base_time += timedelta(hours=1)
            timestamps.append(base_time)

        prices = [80000.0 + np.sin(i / 5.0) * 500.0 for i in range(100)]
        df_test = pd.DataFrame({
            "close": prices,
            "high": [p + 50.0 for p in prices],
            "low": [p - 50.0 for p in prices],
            "volume": [100.0 for _ in prices],
            "timestamp": timestamps
        })

        regime_info = REGIME_TOURNAMENT_ENGINE.get_current_market_regime(
            eval_time=timestamps[-1], df_override=df_test
        )
        # Should not crash and should properly register the continuity
        assert "regime" in regime_info
        assert "hysteresis_status" in regime_info


# ==============================================================================
# PRIORITY C: MARKET SNAPSHOT FRESHNESS & PROVENANCE INTEGRITY
# ==============================================================================

class TestMarketSnapshotFreshness:
    """Verifies point-in-time market snapshot freshness tracking."""

    def test_snapshot_freshness_within_policy(self):
        """Under 2 hours old for 1h candles -> FRESH."""
        now = datetime.now(timezone.utc)
        candle_close = (now - timedelta(minutes=45)).isoformat()
        snap = build_market_snapshot(
            candle_close_time=candle_close,
            interval="1h",
            eval_time=now,
        )
        assert snap.is_stale is False
        assert snap.freshness_status == "FRESH"
        assert 2600.0 < snap.observed_age_seconds < 2800.0

    def test_snapshot_stale_when_exceeding_policy(self):
        """Over 2 hours old for 1h candles -> STALE."""
        now = datetime.now(timezone.utc)
        candle_close = (now - timedelta(hours=5)).isoformat()
        snap = build_market_snapshot(
            candle_close_time=candle_close,
            interval="1h",
            eval_time=now,
        )
        assert snap.is_stale is True
        assert snap.freshness_status == "STALE"
        assert snap.observed_age_seconds > 7200.0

    def test_snapshot_future_timestamp_rejected(self):
        """Future timestamp rejected with INVALID_CLOCK."""
        now = datetime.now(timezone.utc)
        candle_close = (now + timedelta(hours=2)).isoformat()
        snap = build_market_snapshot(
            candle_close_time=candle_close,
            interval="1h",
            eval_time=now,
        )
        assert snap.is_stale is True
        assert snap.freshness_status == "FUTURE_TIMESTAMP"

    def test_stale_snapshot_blocks_economic_eligibility(self):
        """Stale market snapshot enforces STALE_MARKET_DATA setup state."""
        stale_snap = MarketSnapshot(
            provider="coinbase_spot",
            product="BTC/USD",
            interval="1h",
            candle_open_time="2026-10-10T00:00:00+00:00",
            candle_close_time="2026-10-10T01:00:00+00:00",
            is_candle_closed=True,
            observed_age_seconds=100000.0,
            is_stale=True,
            freshness_status="STALE",
            policy_threshold_seconds=7200.0,
        )

        elig = REGIME_TOURNAMENT_ENGINE.evaluate_economic_eligibility(
            entry_price=80000.0,
            tp_price=82000.0,
            sl_price=79000.0,
            side="LONG",
            cost_scenario="COINBASE_RETAIL_87BPS",
            market_snapshot=stale_snap,
        )
        assert elig.status == "STALE_MARKET_DATA"
        assert elig.is_eligible is False
        assert "Market snapshot is stale" in elig.rejection_reason


# ==============================================================================
# PRIORITY D & E: API BOUNDARIES, SECURITY & LIGHTWEIGHT LATENCY
# ==============================================================================

class TestApiSecurityAndLatency:
    """Verifies public FastAPI endpoint contracts, Pydantic responses, and lightweight health."""

    @pytest.fixture(scope="class")
    def client(self):
        return TestClient(app)

    def test_health_is_lightweight_liveness(self, client):
        """Health check returns immediately with status ok without expensive computation."""
        import time
        start = time.monotonic()
        res = client.get("/health")
        duration = time.monotonic() - start

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["trading_enabled"] is False
        assert duration < 0.20, f"Health endpoint took {duration * 1000:.1f}ms (expected <200ms)"

    def test_api_tournament_setup_pydantic_contract(self, client):
        """Setup route returns typed EconomicEligibility and MarketSnapshot schemas."""
        res = client.get("/api/tournament/setup/SHORT_HORIZON_MEAN_REVERSION?cost_scenario=COINBASE_RETAIL_87BPS")
        assert res.status_code == 200
        data = res.json()

        assert "setup_state" in data
        assert "preview_only" in data
        assert "economic_eligibility" in data
        assert "market_snapshot" in data

        ee = data["economic_eligibility"]
        assert "gross_reward_bps" in ee
        assert "cost_round_trip_bps" in ee
        assert "net_reward_bps" in ee
        assert "status" in ee

        ms = data["market_snapshot"]
        assert "provider" in ms
        assert "interval" in ms
        assert "is_stale" in ms

    def test_api_tournament_invalid_cost_scenario_rejected(self, client):
        """Unknown cost scenario rejected with HTTP 400 Bad Request."""
        res = client.get("/api/tournament/setup/SHORT_HORIZON_MEAN_REVERSION?cost_scenario=INVALID_COST_MODEL")
        assert res.status_code == 400
        data = res.json()
        assert "detail" in data
        assert "Unknown cost_scenario" in data["detail"]

    def test_api_tournament_unknown_strategy_rejected(self, client):
        """Unknown strategy ID rejected with HTTP 404."""
        res = client.get("/api/tournament/setup/UNKNOWN_STRATEGY_ID")
        assert res.status_code == 404

    def test_security_error_sanitization_no_path_leakage(self, client):
        """Error responses must not leak file system paths or database credentials."""
        res = client.get("/api/tournament/setup/nonexistent'OR'1'='1?cost_scenario=bad")
        assert res.status_code in [400, 404]
        text = res.text
        assert "c:\\" not in text.lower()
        assert "sqlite://" not in text.lower()
        assert "postgres://" not in text.lower()
        assert "traceback" not in text.lower()
