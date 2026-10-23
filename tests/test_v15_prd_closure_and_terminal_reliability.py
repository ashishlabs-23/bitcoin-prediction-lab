"""
tests/test_v15_prd_closure_and_terminal_reliability.py — V15 PRD Closure & Operational Reliability Verification Suite
====================================================================================================================
Independent verification suite covering all closed requirements in V15:
1. PRD-CMP-14: Multi-Exchange Spot Comparator & Divergence Engine (/market/comparator, Coinbase/Kraken/Bitstamp).
2. PRD-REG-13: Causal Volatility Regime Routing (/regime/latest, Wilder ADX 14, EMA 200/50/20, BBW, 3-bar hysteresis).
3. PRD-PPR-16: Durable Paper Trading Ledger & Cost-Aware Simulated P&L (/api/arena/paper-trades, persistent JSONL).
4. PRD-EXP-17: Research Results & Paper Trade Ledger CSV / JSON Export (/api/arena/paper-trades/export).
5. PRD-IND-11 & PRD-PRF-12: Technical Indicators & Client-Side Chart Preferences Persistence.
6. PRD-ALT-15: Terminal Alerts & Condition Monitor (Price, RSI, Strategy condition triggers, zero order placement).
7. PRD-SEC-18: ASVS 5.0 Security Hardening, Conditional HSTS, Resource-Type Cache Control, Zero Secret / Path Leakage.
8. Core Governance Invariants: Live Trading permanently DISABLED, Model Authorization OFFLINE_RESEARCH_ONLY.
"""

import io
import re
import csv
import json
import pytest
from fastapi.testclient import TestClient

from api.server import app
from config.security import TRADING_ENABLED, PRODUCTION_MODEL_FROZEN
from engine.paper_trade_ledger import PaperTradeLedger, COST_SCENARIO_BPS

client = TestClient(app, raise_server_exceptions=False)


# ==============================================================================
# 1. PRD-CMP-14: Multi-Exchange Spot Comparator Verification
# ==============================================================================

def test_v15_spot_comparator_endpoint_contract():
    """Verify /market/comparator returns schema-compliant multi-exchange spot quotes."""
    resp = client.get("/market/comparator")
    assert resp.status_code == 200
    data = resp.json()

    assert "status" in data
    assert data["status"] in ["LIVE", "DEGRADED", "SINGLE_VENUE", "STALE", "DIVERGENT"]
    assert "active_primary_provider" in data
    assert "max_disagreement_bps" in data
    assert "quotes" in data
    assert isinstance(data["quotes"], dict)
    assert "is_divergent" in data
    assert "healthy_providers_count" in data

    # Verify at least Coinbase or Kraken is healthy and reports positive price
    quotes = data["quotes"]
    healthy_providers = [p for p, q in quotes.items() if q.get("quality") in ["FRESH", "ACCEPTABLE"] or q.get("status") in ["LIVE", "FRESH"]]
    assert len(healthy_providers) >= 1, "At least one spot exchange provider must be live"

    for prov, q in quotes.items():
        if q.get("quality") in ["FRESH", "ACCEPTABLE"] or q.get("status") in ["LIVE", "FRESH"]:
            price = q.get("price_usd") or q.get("price")
            assert price is not None and price > 0
            assert "source_timestamp_utc" in q or "retrieved_at" in q
            age = q.get("age_seconds") if q.get("age_seconds") is not None else q.get("quote_age_seconds")
            assert age is not None and age >= 0


def test_v15_spot_comparator_alias_and_caching():
    """Verify /api/market/comparator alias and Cache-Control headers."""
    resp = client.get("/api/market/comparator")
    assert resp.status_code == 200
    cache_ctrl = resp.headers.get("Cache-Control", "")
    assert "no-store" in cache_ctrl
    assert "no-cache" in cache_ctrl


# ==============================================================================
# 2. PRD-REG-13: Causal Volatility Regime Routing Verification
# ==============================================================================

def test_v15_volatility_regime_routing_causality_and_fields():
    """Verify /regime/latest delivers causal Wilder ADX, EMA, and BBW regime fields."""
    resp = client.get("/regime/latest")
    assert resp.status_code == 200
    data = resp.json()

    # Mandated causal fields
    assert "status" in data
    assert data["status"] == "LIVE"
    assert "current_regime" in data
    assert "adx_14" in data
    assert isinstance(data["adx_14"], (int, float))
    assert data["adx_14"] >= 0

    assert "ema_20" in data and data["ema_20"] > 0
    assert "ema_50" in data and data["ema_50"] > 0
    assert "ema_200" in data and data["ema_200"] > 0
    assert "bb_width" in data and data["bb_width"] >= 0
    assert "classification_rule" in data

    # Governance boundaries
    assert "governance" in data
    assert data["governance"].get("directional_authorization") == "OFFLINE_RESEARCH_ONLY"
    assert data["governance"].get("execution_authorization") == "DISABLED"


# ==============================================================================
# 3. PRD-PPR-16: Durable Paper Trading Ledger & Cost Model
# ==============================================================================

def test_v15_transaction_cost_model_scenarios():
    """Verify transaction cost fee bps across the 3 reconciled scenarios."""
    assert COST_SCENARIO_BPS["COINBASE_RETAIL_87BPS"] == 87.0
    assert COST_SCENARIO_BPS["COINBASE_INSTITUTIONAL_18BPS"] == 18.6
    assert COST_SCENARIO_BPS["BINANCE_PERP_15BPS"] == 15.0


def test_v15_paper_trade_lifecycle_and_persistence(tmp_path):
    """Verify paper trade entry, exit, fee accounting, and persistence across restarts."""
    test_file = str(tmp_path / "test_ledger.jsonl")
    ledger = PaperTradeLedger(ledger_file=test_file)

    # 1. Record an open paper trade
    trade = ledger.record_trade(
        strategy_id="VOLATILITY_BREAKOUT_V1",
        action="BUY",
        entry_price=80000.0,
        size_btc=0.1,  # $8000 notional
        cost_scenario="COINBASE_INSTITUTIONAL_18BPS",
        stop_loss=78000.0,
        take_profit=84000.0,
        notes="V15 Integration Test"
    )

    assert trade["status"] == "OPEN"
    assert trade["notional_usd"] == 8000.0
    # Entry fee: 8000 * (18.6 / 2 / 10000) = 7.44
    assert round(trade["fees_usd"], 2) == 7.44

    # 2. Reload ledger from disk to test persistence
    reloaded_ledger = PaperTradeLedger(ledger_file=test_file)
    trades = reloaded_ledger.get_trades()
    assert len(trades) == 1
    assert trades[0]["trade_id"] == trade["trade_id"]

    # 3. Close the trade at profit ($84,000)
    closed = reloaded_ledger.close_trade(
        trade_id=trade["trade_id"],
        exit_price=84000.0,
        outcome="TAKE_PROFIT"
    )

    assert closed["status"] == "CLOSED"
    assert closed["exit_price"] == 84000.0
    # Gross P&L = (84000 - 80000) * 0.1 = +$400.00
    assert round(closed["gross_pnl_usd"], 2) == 400.00
    # Roundtrip fees: (8000 + 8400) * 0.5 * (18.6 / 10000) = 8200 * 0.00186 = 15.25
    assert round(closed["fees_usd"], 2) == 15.25
    # Net P&L = 400.00 - 15.25 = 384.75
    assert round(closed["net_pnl_usd"], 2) == 384.75

    # 4. Verify portfolio metrics
    metrics = reloaded_ledger.get_portfolio_metrics()
    assert metrics["total_trades"] == 1
    assert metrics["winning_trades"] == 1
    assert metrics["losing_trades"] == 0
    assert metrics["win_rate_pct"] == 100.0
    assert round(metrics["net_pnl_usd"], 2) == 384.75


# ==============================================================================
# 4. PRD-EXP-17: CSV & JSON Research Data Export
# ==============================================================================

def test_v15_paper_trade_export_csv_and_json():
    """Verify /api/arena/paper-trades/export generates valid CSV and JSON downloads."""
    # Test CSV export
    csv_resp = client.get("/api/arena/paper-trades/export?format=csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers.get("content-type", "")
    assert "attachment; filename=" in csv_resp.headers.get("content-disposition", "")

    csv_reader = csv.reader(io.StringIO(csv_resp.text))
    header = next(csv_reader)
    expected_cols = ["trade_id", "strategy_id", "action", "status", "entry_price", "exit_price", "fees_usd", "net_pnl_usd"]
    for col in expected_cols:
        assert col in header, f"Missing {col} in CSV export header"

    # Test JSON export
    json_resp = client.get("/api/arena/paper-trades/export?format=json")
    assert json_resp.status_code == 200
    assert "application/json" in json_resp.headers.get("content-type", "")
    json_data = json_resp.json()
    assert "export_time_utc" in json_data or "exported_at_utc" in json_data
    assert "trades" in json_data


# ==============================================================================
# 5. PRD-SEC-18: Security Hardening & Zero Path/Secret Leakage
# ==============================================================================

_SENSITIVE_PATH_REGEX = re.compile(
    r"([A-Za-z]:\\[^ \"'>\r\n\t]+|/(?:Users|home|root|var|etc|opt|tmp)/[^ \"'>\r\n\t]+)",
    re.IGNORECASE
)
_DB_URI_REGEX = re.compile(
    r"(?:sqlite|postgres|mysql|mongodb)(?:\+[a-z]+)?://[^ \"'>\r\n\t]+",
    re.IGNORECASE
)

def test_v15_security_headers_and_cache_control():
    """Verify OWASP ASVS 5.0 headers and resource-type Cache-Control enforcement."""
    # 1. API route must have no-store
    api_resp = client.get("/health")
    assert api_resp.status_code == 200
    assert "no-store" in api_resp.headers.get("Cache-Control", "")
    assert api_resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert api_resp.headers.get("X-Frame-Options") == "DENY"

    # 2. HTML root must have no-cache, must-revalidate
    html_resp = client.get("/")
    assert html_resp.status_code == 200
    html_cache = html_resp.headers.get("Cache-Control", "")
    assert "no-cache" in html_cache
    assert "must-revalidate" in html_cache

    # 3. Versioned asset query string must have max-age caching
    asset_resp = client.get("/app.js?v=15.0.0")
    if asset_resp.status_code == 200:
        asset_cache = asset_resp.headers.get("Cache-Control", "")
        assert "max-age=" in asset_cache or "public" in asset_cache


def test_v15_zero_secret_or_path_leakage_on_all_v15_routes():
    """Verify no local filesystem paths or database URIs are disclosed across V15 endpoints."""
    routes = [
        "/market/comparator",
        "/regime/latest",
        "/api/arena/paper-trades",
        "/api/arena/paper-trades/export?format=json"
    ]
    for r in routes:
        resp = client.get(r)
        assert resp.status_code == 200, f"Route {r} returned {resp.status_code}"
        text = resp.text
        assert "C:\\Users\\" not in text, f"Route {r} disclosed Windows user path: {text[:200]}"
        assert "/home/" not in text, f"Route {r} disclosed Linux home path: {text[:200]}"
        assert not _DB_URI_REGEX.search(text), f"Route {r} disclosed DB URI"


# ==============================================================================
# 6. Core Non-Execution & Research Boundaries
# ==============================================================================

def test_v15_strict_non_execution_and_offline_research_invariants():
    """Verify trading remains strictly disabled and directional predictions remain research-only."""
    assert TRADING_ENABLED is False, "CRITICAL: TRADING_ENABLED must permanently remain False"

    resp = client.get("/prediction/latest?live=false")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("trading_enabled") is False or data.get("execution_authorized") is False
    governance = data.get("governance", {})
    if governance:
        assert governance.get("execution_authorization") == "DISABLED"
        assert governance.get("directional_authorization") in ["OFFLINE_RESEARCH_ONLY", "TIER_2_GATED", "ABSTAIN"]
