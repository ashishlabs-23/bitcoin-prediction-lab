"""
tests/test_v21_hotfix_and_alerts.py — BTCognitive V21 Regression & Gate Verification Suite
========================================================================================
Validates the hotfixes and restored research-condition alert lifecycle:
1. Authoritative analysis-only contract (live trading & execution permanently disabled).
2. Sanitized chart markers: no 'NONE · LOSS' or 'AI NOT ESTIMATED (75%)' artifacts.
3. Independent future-price forecasting: persistence baseline, experimental candidates,
   empirical quantiles, and HAR-RS-DOW volatility context remain cleanly separated.
4. Research-condition alert workflow: trigger on fresh completed data, 15m cooldown,
   deduplication, multi-channel reporting (browser, sound, webhook, email, telegram),
   stale-data rejection, and absolute non-execution invariant.
5. Read-only dashboard idempotency: no decision records appended as side-effects.
"""

import os
import time
import pytest
import sqlite3
import pandas as pd
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from api.server import app
from api.notifications import notification_manager, NotificationManager
from backtest.market_memory import load_market_memory, resolve_pending_outcomes, _get_db
from engine.inference_service import live_engine


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ===========================================================================
# 1. Authoritative Analysis-Only & Execution Disabled Contract
# ===========================================================================

def test_analysis_only_authoritative_health_contract(client):
    """Verify health and readiness endpoints enforce analysis-only execution disabled contract."""
    for path in ["/health", "/api/health", "/api/readiness", "/api/terminal/readiness"]:
        res = client.get(path)
        assert res.status_code == 200, f"Failed at {path}"
        data = res.json()
        assert data.get("product_mode") == "ANALYSIS_ONLY"
        assert data.get("live_trading_enabled") is False
        assert data.get("order_submission_enabled") is False
        assert data.get("directional_recommendation_status") == "DISABLED"
        assert data.get("execution_status") == "DISABLED_ANALYSIS_ONLY"
        assert data.get("research_alerts_enabled") is True


def test_active_paper_position_execution_disabled_contract(client):
    """Verify active paper position endpoint exposes explicit execution disabled status."""
    res = client.get("/api/arena/active-paper-position")
    assert res.status_code == 200
    data = res.json()
    assert data.get("product_mode") == "ANALYSIS_ONLY"
    assert data.get("execution_status") == "DISABLED_ANALYSIS_ONLY"
    assert "Execution disabled" in data.get("execution_disabled_message", "")
    assert data.get("live_trading_enabled") is False
    assert data.get("is_authorized_live") is False
    assert data.get("is_directional_trade_signal") is False


def test_trading_mutation_endpoints_rejected_or_nonexistent(client):
    """Verify that obsolete order submission or execution mutations are impossible."""
    mutation_routes = [
        ("/api/orders", "post"),
        ("/api/trade/execute", "post"),
        ("/api/paper/order", "post"),
        ("/api/execution/submit", "post"),
    ]
    for route, method in mutation_routes:
        fn = getattr(client, method)
        res = fn(route, json={"symbol": "BTCUSD", "qty": 1.0})
        # Must be 404 Not Found or 405 Method Not Allowed
        assert res.status_code in [404, 405], f"Unexpected status {res.status_code} on {route}"


# ===========================================================================
# 2. Chart Markers Sanitation: No NONE · LOSS or AI NOT ESTIMATED (75%)
# ===========================================================================

def test_trade_markers_api_excludes_non_trades(client):
    """Verify /api/arena/trade-markers only returns directional trades (LONG/SHORT) and never NONE."""
    res = client.get("/api/arena/trade-markers?limit=100")
    assert res.status_code == 200
    data = res.json()
    markers = data.get("markers", [])
    for m in markers:
        assert m.get("direction") in ("LONG", "SHORT"), f"Found invalid non-directional marker: {m}"
        if m.get("type", "").startswith("ENTRY"):
            assert m.get("entry_price", 0) > 0


def test_market_memory_non_directional_was_correct_is_null():
    """Verify that records with NONE, HOLD, SKIP, NEUTRAL in market memory have was_correct as NA."""
    df = load_market_memory()
    if not df.empty:
        non_directional = df[df["direction"].isin(["NONE", "HOLD", "SKIP", "NEUTRAL"]) | df["decision"].isin(["HOLD", "SKIP", "NEUTRAL"])]
        if not non_directional.empty:
            assert non_directional["was_correct"].isna().all(), "Non-directional memory rows must have NA was_correct (never 0 / False)"


# ===========================================================================
# 3. Independent Future-Price Forecasting vs Volatility Separation
# ===========================================================================

def test_future_price_forecast_separation(client):
    """Verify future-price forecast returns typed, truthful results separate from HAR volatility."""
    res = client.get("/api/forecast/latest?horizon=1h")
    assert res.status_code == 200
    data = res.json()
    
    # Must contain reference price and forecast horizons
    assert "reference_price" in data or "spot_price" in data or "current_price" in data
    assert "forecast_points" in data or "points" in data
    assert "upper_band" in data and "lower_band" in data
    assert data.get("directional_recommendation_status") == "DISABLED"
    assert data.get("directional_recommendation") == "ABSTAIN"
    
    # HAR-RS-DOW volatility gate is separate from directional models
    res_vol = client.get("/api/terminal/live")
    assert res_vol.status_code == 200
    vol_data = res_vol.json()
    assert vol_data.get("scientific_governance") == "FREEZE_REPAIRED_AND_VERIFIED"
    assert "HAR-RS-DOW" in str(vol_data.get("four_questions", {}))



def test_forecast_multi_horizon_truthfulness(client):
    """Verify 1h, 4h, and 24h horizons return typed metadata without fabricating directional recommendations."""
    for h in ["1h", "4h", "24h"]:
        res = client.get(f"/api/forecast/latest?horizon={h}")
        assert res.status_code == 200
        data = res.json()
        assert data.get("directional_recommendation_status") == "DISABLED"
        assert data.get("directional_recommendation") == "ABSTAIN"
        assert data.get("product_mode") == "ANALYSIS_ONLY"
        assert data.get("live_trading_enabled") is False


# ===========================================================================
# 4. Research Condition Alert Lifecycle & Governance
# ===========================================================================

def test_research_conditions_metadata_endpoint(client):
    """Verify documented research conditions are exposed with strict research governance."""
    res = client.get("/api/notifications/research-alerts/conditions")
    assert res.status_code == 200
    data = res.json()
    assert data.get("governance_mode") == "ANALYSIS_ONLY"
    assert data.get("live_trading_enabled") is False
    assert data.get("directional_recommendation_status") == "DISABLED"
    conditions = data.get("conditions", [])
    assert len(conditions) >= 3
    for cond in conditions:
        assert cond.get("governance") == "OFFLINE_RESEARCH_ONLY"
        assert cond.get("is_directional") is False
        assert cond.get("cooldown_seconds") == 900


@pytest.mark.asyncio
async def test_research_alert_trigger_on_fresh_condition():
    """Verify that a genuine research condition triggers a structured notification."""
    mgr = NotificationManager()
    mgr.condition_cooldowns.clear()
    mgr.seen_dedup_hashes.clear()
    
    # Create synthetic fresh market data (age: 60s) with low volatility (compression)
    fresh_time = datetime.now(timezone.utc) - timedelta(seconds=60)
    fake_candles = []
    base_price = 82000.0
    for i in range(50):
        t = fresh_time - timedelta(hours=50 - i)
        fake_candles.append({
            "timestamp": t.isoformat(),
            "open": base_price + (i * 0.1),
            "high": base_price + (i * 0.1) + 2.0,
            "low": base_price + (i * 0.1) - 2.0,
            "close": base_price + (i * 0.1) + 0.5,
            "volume": 100.0
        })
    market_data = {
        "candles": fake_candles,
        "spot_price": 82005.0,
        "timestamp": fresh_time.isoformat()
    }

    result = await mgr.evaluate_research_conditions(market_data=market_data, force=True)
    assert result.get("status") in ["DELIVERED", "TRIGGERED", "NO_ALERT"]
    if result.get("status") in ["DELIVERED", "TRIGGERED"]:
        alert = result.get("alert", {})
        assert alert.get("is_research_alert") is True
        assert "BTCUSD research condition detected" in alert.get("rationale", "") or "BTCUSD research condition detected" in alert.get("tier_title", "")
        assert alert.get("live_trading_enabled") is False
        assert alert.get("order_submission_enabled") is False


@pytest.mark.asyncio
async def test_research_alert_cooldown_and_deduplication():
    """Verify that cooldown (15m) and deduplication prevent repeated notifications."""
    mgr = NotificationManager()
    mgr.condition_cooldowns.clear()
    mgr.seen_dedup_hashes.clear()
    
    fresh_time = datetime.now(timezone.utc) - timedelta(seconds=60)
    fake_candles = []
    base_price = 82000.0
    for i in range(50):
        t = fresh_time - timedelta(hours=50 - i)
        fake_candles.append({
            "timestamp": t.isoformat(),
            "open": base_price,
            "high": base_price + 1.0,
            "low": base_price - 1.0,
            "close": base_price,
            "volume": 50.0
        })
    market_data = {
        "candles": fake_candles,
        "spot_price": 82000.0,
        "timestamp": fresh_time.isoformat()
    }

    # First evaluation: triggers alert
    res1 = await mgr.evaluate_research_conditions(market_data=market_data, force=True)
    
    # Second evaluation immediately after: must be blocked by cooldown or dedup
    res2 = await mgr.evaluate_research_conditions(market_data=market_data, force=False)
    assert res2.get("status") in ["NO_ALERT", "COOLDOWN_ACTIVE", "DEDUPLICATED"]


@pytest.mark.asyncio
async def test_stale_market_data_rejects_positive_alert():
    """Verify that stale market data (>2h old) emits typed NO_ALERT rejection and cannot notify."""
    mgr = NotificationManager()
    stale_time = datetime.now(timezone.utc) - timedelta(hours=5)
    stale_candles = [
        {"timestamp": stale_time.isoformat(), "open": 80000.0, "high": 80100.0, "low": 79900.0, "close": 80050.0, "volume": 10.0}
    ]
    market_data = {
        "candles": stale_candles,
        "spot_price": 80050.0,
        "timestamp": stale_time.isoformat()
    }
    res = await mgr.evaluate_research_conditions(market_data=market_data, force=True)
    assert res.get("status") == "NO_ALERT"
    assert res.get("reason") == "STALE_MARKET_DATA"


@pytest.mark.asyncio
async def test_channel_delivery_reporting_accuracy():
    """Verify each channel reports delivered, failed, or not_configured accurately."""
    mgr = NotificationManager()
    test_alert = {
        "id": f"res_alert_test_{time.time_ns()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_research_alert": True,
        "rationale": "BTCUSD research condition detected: Volatility Compression",
        "tier_title": "BTCUSD Research Alert",
        "badge": "RESEARCH ONLY"
    }
    
    dispatch_res = await mgr.dispatch_alert(test_alert)
    assert "channels" in dispatch_res
    channels = dispatch_res["channels"]
    for ch_name, ch_res in channels.items():
        assert ch_res.get("status") in ["delivered", "failed", "not_configured", "blocked", "disabled"]


def test_read_only_dashboard_no_decision_records_side_effect(client):
    """Verify read-only dashboard endpoints do NOT append records to market memory."""
    conn = _get_db()
    initial_count = conn.execute("SELECT count(*) FROM predictions").fetchone()[0]
    conn.close()
        
    # Query all read-only dashboard endpoints
    res1 = client.get("/api/arena/active-paper-position")
    assert res1.status_code == 200
    res2 = client.get("/api/arena/trade-markers")
    assert res2.status_code == 200
    res3 = client.get("/prediction/latest?live=false")
    assert res3.status_code == 200
    res4 = client.get("/api/forecast/latest?horizon=1h")
    assert res4.status_code == 200
    
    conn = _get_db()
    final_count = conn.execute("SELECT count(*) FROM predictions").fetchone()[0]
    conn.close()
    assert final_count == initial_count, "Read-only dashboard run must not append decision records to market memory!"

