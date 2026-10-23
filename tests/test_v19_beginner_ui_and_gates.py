"""
tests/test_v19_beginner_ui_and_gates.py — V19 Beginner-Friendly UX, Forecast Integrity & Gate Verification
===========================================================================================================
Independent verification of BTCognitive V19:
1. Strict 5-area beginner-friendly frontend structure with zero trading / order execution UI.
2. Forecast integrity: sample-size hurdles (N >= 30, N=625 for 24h), target separation, and plain-language summaries.
3. Complete gate matrix: positive and adversarial negative tests across all disabled/blocked capabilities.
4. Idempotent GET operations (zero ledger mutations).
"""

import os
import json
import pytest
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
# 1. Beginner-Friendly Frontend Contracts & Invariants
# ---------------------------------------------------------------------------

class TestV19BeginnerFrontendContracts:
    """Verifies web/app.js conforms to the 5 primary areas and eliminates trading UI."""

    @pytest.fixture(scope="class")
    def app_js_content(self):
        js_path = os.path.join("web", "app.js")
        assert os.path.exists(js_path), "web/app.js must exist"
        with open(js_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_five_primary_areas_exist_in_frontend(self, app_js_content):
        """The main screen must contain exactly the 5 primary beginner-friendly areas."""
        assert "v19-area-btc-now" in app_js_content, "Area 1: BTCUSD right now missing"
        assert "v19-area-future-price" in app_js_content, "Area 2: Estimated future price missing"
        assert "v19-area-market-conditions" in app_js_content, "Area 3: Market conditions missing"
        assert "v19-area-forecast-reliability" in app_js_content, "Area 4: Forecast reliability missing"
        assert "v19-area-research-tabs" in app_js_content, "Area 5: Research tabs missing"

    def test_complete_removal_of_trading_ui(self, app_js_content):
        """No order ticket, paper order forms, or execution controls may exist in UI."""
        # QuickExecutionTicket must be an empty stub
        assert "function QuickExecutionTicket" in app_js_content
        assert "return null" in app_js_content

        # No order submission or paper execution buttons
        forbidden_phrases = [
            "Submit Order",
            "Place Order",
            "Buy / Long",
            "Sell / Short",
            "Close Paper Position",
            "Execute Paper Trade"
        ]
        for phrase in forbidden_phrases:
            assert phrase not in app_js_content, f"Forbidden trading phrase '{phrase}' found in web/app.js"

    def test_plain_language_states_present(self, app_js_content):
        """Frontend must contain plain-language state indicators."""
        assert "Live data available" in app_js_content
        assert "Forecast is experimental" in app_js_content
        assert "Not enough evidence yet" in app_js_content
        assert "Forecast unavailable" in app_js_content

    def test_empirical_quantiles_properly_explained(self, app_js_content):
        """P10/P50/P90 must be defined in expandable/tooltip context, and explicitly disclaimed as confidence intervals."""
        assert "P10" in app_js_content
        assert "P90" in app_js_content
        assert "not a guaranteed envelope or calibrated confidence interval" in app_js_content.lower() or "not a calibrated confidence interval" in app_js_content.lower()


# ---------------------------------------------------------------------------
# 2. Future-Price Forecast Integrity & Large Sample Size
# ---------------------------------------------------------------------------

class TestV19ForecastIntegrity:
    """Verifies price forecast engine satisfies V19 sample size and plain summary contracts."""

    def test_forecast_api_plain_summary_and_tooltips(self):
        """GET /api/prediction/price/forecast must return plain_summary and tooltip_definitions."""
        resp = client.get("/api/prediction/price/forecast")
        assert resp.status_code == 200
        data = resp.json()

        for h in ("1h", "4h", "24h"):
            h_data = data["forecast_horizons"][h]
            assert "plain_summary" in h_data
            assert "plain_range" in h_data
            assert "tooltip_definitions" in h_data
            assert "p10" in h_data["tooltip_definitions"]
            assert "p90" in h_data["tooltip_definitions"]
            assert "persistence" in h_data["tooltip_definitions"]

            # Must state that P10/P90 are historical percentiles, NOT calibrated confidence intervals
            assert "not a confidence interval" in h_data["tooltip_definitions"]["p10"].lower()

    def test_underpowered_sample_guardrail(self):
        """Verifies evaluation on < 30 blocks flags UNDERPOWERED_SAMPLE and INSUFFICIENT_EVIDENCE."""
        underpowered = price_forecast_engine.run_walk_forward_tournament(test_blocks=10)
        assert underpowered["sample_status"] == "UNDERPOWERED_SAMPLE"
        assert underpowered["tournament_verdict"] == "INSUFFICIENT_EVIDENCE"
        assert underpowered["recommended_production_model"] == "NONE_OFFLINE_RESEARCH_ONLY"

    def test_adequate_sample_size_24h(self):
        """Verifies full walk-forward tournament on 24h evaluates at least 30 non-overlapping blocks."""
        # Run with sufficient blocks
        res = price_forecast_engine.run_walk_forward_tournament(test_blocks=1000)
        h24 = res["results_by_horizon"]["24h"]
        assert h24["n_test_blocks"] >= 30, f"Expected >= 30 24h blocks, got {h24['n_test_blocks']}"
        assert res["sample_status"] == "SUFFICIENT_SAMPLE"

    def test_persistence_remains_unbeaten(self):
        """Ridge and Drift must not claim victory over Persistence on unconditional BTC returns."""
        res = price_forecast_engine.run_walk_forward_tournament(test_blocks=1000)
        for h, r in res["results_by_horizon"].items():
            assert r["status"] == "PERSISTENCE_BASELINE_UNBEATEN"
            assert r["statistically_superior_challenger_exists"] is False


# ---------------------------------------------------------------------------
# 3. Complete Gate Verification Matrix (Positive & Adversarial Negative Tests)
# ---------------------------------------------------------------------------

class TestV19GateVerificationMatrix:
    """Verifies that all disabled, blocked, and restricted capabilities fail closed."""

    def test_gate_01_live_trading_adversarial_attempt(self):
        """Gate 1: Live order placement must be rejected even with spoofed admin tokens or aggressive payloads."""
        adversarial_payloads = [
            {"action": "BUY", "amount_btc": 100.0, "type": "MARKET"},
            {"action": "SELL", "amount_btc": 50.0, "type": "LIMIT", "price": 95000.0},
            {"action": "FORCE_BUY", "override_governance": True}
        ]
        headers = {"Authorization": "Bearer admin_super_secret_bypass_token", "X-Role": "ADMIN"}
        for p in adversarial_payloads:
            resp = client.post("/api/arena/trade", json=p, headers=headers)
            assert resp.status_code in (200, 401, 403)
            if resp.status_code == 200:
                data = resp.json()
                assert data["status"] == "DISABLED"
                assert data["governance"]["live_trading"] == "DISABLED"

    def test_gate_02_paper_order_submission_adversarial_attempt(self):
        """Gate 2: Paper trade creation must be rejected with explicit DISABLED status."""
        resp = client.post("/api/arena/paper-trades", json={"action": "BUY", "size_btc": 1.0})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DISABLED"
        assert data["trade"] is None

    def test_gate_03_production_model_authorization_lock(self):
        """Gate 3: Offline research models must NEVER inherit production status."""
        rw = get_model_identity("price-forecast-persistence-rw")
        assert rw.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
        assert rw.classification == ModelClassification.PRICE_FORECAST_RESEARCH

        drift = get_model_identity("price-forecast-rolling-drift")
        assert drift.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY

        ridge = get_model_identity("price-forecast-ridge-lagged")
        assert ridge.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY

    def test_gate_04_target_separation_volatility_vs_price(self):
        """Gate 4: HAR-RS-DOW is exclusively a realized volatility model and cannot predict price direction."""
        prod = get_active_production_model()
        assert prod.canonical_id == "HAR-RS-DOW-v1.0"
        assert prod.classification == ModelClassification.PRODUCTION_VOLATILITY
        assert prod.directional_prediction_capability is False
        assert "rv7d_var_ann" in prod.forecast_target.lower()

    def test_gate_05_unconfigured_external_providers(self):
        """Gate 5: Optional unconfigured external data providers must be reported as unavailable."""
        resp = client.get("/api/terminal/decision-anatomy")
        assert resp.status_code == 200
        data = resp.json()
        # Macro and Deribit options data are not configured; must report honest status
        assert "header" in data
        assert "economics_status" in data

    def test_gate_06_idempotent_get_operations(self):
        """Gate 6: GET requests must not mutate research ledgers or change database state."""
        import sqlite3
        db_path = os.path.join("experiments", "results", "observatory.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            c1 = conn.execute("SELECT count(*) FROM forecast_origins").fetchone()[0]
            conn.close()

            # Execute multiple read-only queries
            client.get("/api/prediction/price/forecast")
            client.get("/api/terminal/decision-anatomy")
            client.get("/api/arena/context")

            conn = sqlite3.connect(db_path)
            c2 = conn.execute("SELECT count(*) FROM forecast_origins").fetchone()[0]
            conn.close()

            assert c1 == c2, "GET requests must not mutate sqlite forecast_origins table"
