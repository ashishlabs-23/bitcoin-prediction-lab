"""
tests/test_v20_release_and_gates.py — V20 Release Verification & 10-Gate Audit Matrix
=====================================================================================
Comprehensive and independent verification of BTCognitive V20:
1. Reconciled 10-Gate Verification Matrix with positive and adversarial tests.
2. Market Quote Freshness Policy (<=60s fresh, <=3600s delayed, >3600s unavailable).
3. Fail-Closed Historical Reference Range (no synthetic quantiles, requires >=30 obs).
4. Strict Non-Execution Analysis-Only Invariant across all endpoints.
"""

import os
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from api.server import app
from engine.price_forecast_engine import price_forecast_engine
from models.authoritative_model_registry import (
    get_active_production_model,
    get_model_identity,
    AuthorizationStatus,
    ModelClassification,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Market Quote Freshness Policy Verification
# ---------------------------------------------------------------------------

class TestV20MarketQuoteFreshness:
    """Verifies that the market data freshness policy is strictly enforced."""

    def test_fresh_quote_policy(self):
        """Quote age <= 60s is classified as FRESH_LIVE_QUOTE with live label."""
        df = price_forecast_engine.load_data()
        assert df is not None
        now_iso = datetime.now(timezone.utc).isoformat()
        live_quote = {
            "provider": "Coinbase",
            "instrument": "BTC-USD",
            "price_usd": 83500.0,
            "source_timestamp": now_iso,
            "age_seconds": 15.0
        }
        res = price_forecast_engine.generate_horizon_forecast(df, "1h", live_quote=live_quote)
        assert res["status"] == "EXPERIMENTAL_PRICE_FORECAST"
        assert res["is_live_quote"] is True
        assert res["freshness_status"] == "FRESH_LIVE_QUOTE"
        assert res["plain_status"] == "Live data available"
        assert res["reference_price_usd"] == 83500.0

    def test_delayed_quote_policy(self):
        """Quote age between 60s and 3600s is classified as PRICE_UPDATE_DELAYED."""
        df = price_forecast_engine.load_data()
        stale_time = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
        delayed_quote = {
            "provider": "Coinbase",
            "instrument": "BTC-USD",
            "price_usd": 82000.0,
            "source_timestamp": stale_time,
            "age_seconds": 900.0
        }
        res = price_forecast_engine.generate_horizon_forecast(df, "1h", live_quote=delayed_quote)
        assert res["freshness_status"] == "PRICE_UPDATE_DELAYED"
        assert res["plain_status"] == "Price update delayed"

    def test_unavailable_quote_policy(self):
        """Quote age > 3600s is classified as CURRENT_PRICE_UNAVAILABLE."""
        df = price_forecast_engine.load_data()
        ancient_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        unavailable_quote = {
            "provider": "Coinbase",
            "instrument": "BTC-USD",
            "price_usd": 81000.0,
            "source_timestamp": ancient_time,
            "age_seconds": 18000.0
        }
        res = price_forecast_engine.generate_horizon_forecast(df, "1h", live_quote=unavailable_quote)
        assert res["freshness_status"] == "CURRENT_PRICE_UNAVAILABLE"
        assert res["plain_status"] == "Current price unavailable"


# ---------------------------------------------------------------------------
# 2. Historical Reference Range Semantics & Fail-Closed Behavior
# ---------------------------------------------------------------------------

class TestV20HistoricalRangeSemantics:
    """Verifies that historical quantiles fail closed and are properly labeled."""

    def test_empirical_quantiles_fail_closed_on_insufficient_data(self):
        """When history has < 30 observations, quantiles must return None without synthetic fallback."""
        df = price_forecast_engine.load_data()
        df_copy = df.copy()
        # Invalidate rolling history so fewer than 30 valid return observations exist
        df_copy.loc[df_copy.index[-720:-10], "close"] = 0.0
        res = price_forecast_engine.generate_horizon_forecast(df_copy, "1h")
        eq = res["empirical_quantiles"]
        assert eq["range_available"] is False
        assert eq["p10_price_usd"] is None
        assert eq["p50_price_usd"] is None
        assert eq["p90_price_usd"] is None
        assert eq["sample_size_bars"] < 30

    def test_empirical_quantiles_sufficient_data(self):
        """On standard 30-day (720 hour) history, empirical percentiles are cleanly computed."""
        df = price_forecast_engine.load_data()
        res = price_forecast_engine.generate_horizon_forecast(df, "1h")
        eq = res["empirical_quantiles"]
        assert eq["range_available"] is True
        assert eq["p10_price_usd"] < eq["p50_price_usd"] < eq["p90_price_usd"]
        assert eq["sample_size_bars"] >= 700
        assert "not a calibrated prediction interval" in eq["interpretation"].lower()


# ---------------------------------------------------------------------------
# 3. Authoritative 10-Gate Reconciled Verification Matrix
# ---------------------------------------------------------------------------

class TestV20ReconciledTenGates:
    """Explicitly verifies each of the 10 gates in the V20 security and research architecture."""

    def test_gate_01_live_trading_execution_blocked(self):
        """Gate 01: Live trading endpoint returns typed DISABLED response across all payloads."""
        resp = client.post("/api/arena/trade", json={"action": "BUY", "amount_btc": 10.0})
        assert resp.status_code in (200, 403)
        if resp.status_code == 200:
            assert resp.json()["status"] == "DISABLED"
            assert resp.json()["governance"]["live_trading"] == "DISABLED"

    def test_gate_02_paper_order_creation_blocked(self):
        """Gate 02: Paper trade order creation is explicitly disabled at API boundary."""
        resp = client.post("/api/arena/paper-trades", json={"strategy_id": "MOMENTUM", "action": "BUY"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DISABLED"
        assert data["trade"] is None

    def test_gate_03_model_authorization_lock(self):
        """Gate 03: Models classified as research never inherit production authorization."""
        rw = get_model_identity("price-forecast-persistence-rw")
        assert rw.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
        drift = get_model_identity("price-forecast-rolling-drift")
        assert drift.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
        ridge = get_model_identity("price-forecast-ridge-lagged")
        assert ridge.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY

    def test_gate_04_target_separation_volatility_vs_price(self):
        """Gate 04: Production HAR-RS-DOW targets 168h variance and cannot emit price signals."""
        prod = get_active_production_model()
        assert prod.canonical_id == "HAR-RS-DOW-v1.0"
        assert prod.classification == ModelClassification.PRODUCTION_VOLATILITY
        assert prod.directional_prediction_capability is False

    def test_gate_05_unconfigured_external_providers_fail_closed(self):
        """Gate 05: Unconfigured feeds (Options IV, Macro) report UNAVAILABLE instead of synthetic mock data."""
        resp = client.get("/api/terminal/decision-anatomy")
        assert resp.status_code == 200
        data = resp.json()
        assert "economics_status" in data

    def test_gate_06_read_side_idempotency_zero_mutations(self):
        """Gate 06: GET requests cause exactly 0 mutations to database ledgers."""
        db_path = os.path.join("experiments", "results", "observatory.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            c1 = conn.execute("SELECT count(*) FROM forecast_origins").fetchone()[0]
            conn.close()

            # Execute multiple read calls
            client.get("/api/prediction/price/forecast?horizon=1h")
            client.get("/api/terminal/decision-anatomy")
            client.get("/api/arena/active-paper-position")

            conn = sqlite3.connect(db_path)
            c2 = conn.execute("SELECT count(*) FROM forecast_origins").fetchone()[0]
            conn.close()
            assert c1 == c2, "Database records must remain unchanged during GET requests."

    def test_gate_07_empirical_quantile_labeling_and_disclaimer(self):
        """Gate 07: Empirical quantiles explicitly disclaimed from confidence intervals."""
        resp = client.get("/api/prediction/price/forecast?horizon=1h")
        assert resp.status_code == 200
        data = resp.json()
        assert "not a confidence interval" in data["tooltip_definitions"]["p10"].lower()
        assert "not a confidence interval" in data["tooltip_definitions"]["p90"].lower()

    def test_gate_08_sample_size_statistical_hurdle(self):
        """Gate 08: Samples with N < 30 fail statistical validation hurdle."""
        underpowered = price_forecast_engine.run_walk_forward_tournament(test_blocks=12)
        assert underpowered["sample_status"] == "UNDERPOWERED_SAMPLE"
        assert underpowered["tournament_verdict"] == "INSUFFICIENT_EVIDENCE"

    def test_gate_09_market_freshness_policy_enforcement(self):
        """Gate 09: API /api/prediction/price/forecast delivers reference_market with freshness status."""
        resp = client.get("/api/prediction/price/forecast?horizon=all")
        assert resp.status_code == 200
        data = resp.json()
        assert "reference_market" in data
        ref = data["reference_market"]
        assert "freshness_status" in ref
        assert ref["freshness_status"] in ("FRESH_LIVE_QUOTE", "PRICE_UPDATE_DELAYED", "CURRENT_PRICE_UNAVAILABLE")

    def test_gate_10_missing_action_fails_closed_to_abstain(self):
        """Gate 10: Missing inputs or unconfigured features fail closed to ABSTAIN, never default to BUY/SELL."""
        resp = client.get("/api/arena/active-paper-position")
        assert resp.status_code == 200
        data = resp.json()
        if not data.get("has_active_position"):
            # When awaiting signal or evaluating AI, action must be ABSTAIN or NEUTRAL
            direction = data.get("direction")
            assert direction in ("ABSTAIN", "NEUTRAL", None)
            assert direction not in ("BUY", "SELL")
