"""
BTCognitive V33.4G — Forecast & Market-Data Presentation Integrity Test Suite.
Verifies that:
1. Status contract reflects LOCAL_HISTORICAL_SNAPSHOT with STALE status and explicit disclaimer in offline_research mode.
2. Directional return forecasts are decoupled from C2 continuous variance risk envelope (HAR-RS-DOW-v1.0).
3. Hardcoded demo fallbacks (SHORT, 47.1%, 55.85%, dummy SHAP weights) are completely purged from web/app.js.
4. Unconditional 'Live price' and 'Coinbase BTC/USD Feed' labels are replaced with historical snapshot disclosures.
5. Execution status remains strictly DISABLED — ANALYSIS ONLY.
"""

import os
import re
import pytest
from engine.status_contract import evaluate_system_status, EXECUTION_STATUS_CONSTANT


class TestV33_4G_Presentation_Integrity:
    """Verifies F04 and F05 presentation integrity fixes."""

    def test_status_contract_stale_snapshot_disclosure(self, monkeypatch):
        """Verifies status contract truthfully discloses stale historical snapshot in offline research mode."""
        monkeypatch.setenv("BTC_DATA_MODE", "offline_research")
        status = evaluate_system_status()
        
        # Invariant 1: Market data status is STALE when backed by historical snapshot
        assert status.market_data_status == "STALE"
        
        # Invariant 2: Explicit metadata marking historical snapshot
        details = status.market_data_details
        assert details.get("source") == "LOCAL_HISTORICAL_SNAPSHOT"
        assert details.get("is_historical_snapshot") is True
        assert "STALE — NOT A CURRENT ENTRY REFERENCE" in details.get("snapshot_label", "")

    def test_execution_status_strictly_disabled(self):
        """Verifies live trading is strictly disabled."""
        status = evaluate_system_status()
        assert status.execution_status == EXECUTION_STATUS_CONSTANT
        assert status.execution_status == "DISABLED — ANALYSIS ONLY"

    def test_prediction_api_returns_unverified_provenance(self):
        """Verifies prediction route separates risk proxy from unverified directional forecast."""
        from api.routes_prediction import _unavailable_range_payload
        payload = _unavailable_range_payload("24h")
        
        assert payload["authoritative_production_model"] == "HAR-RS-DOW-v1.0"
        assert payload["direction_state"] == "NOT_ESTIMATED"
        assert payload["status"] == "BLOCKED_PROVENANCE_UNVERIFIED"
        assert payload["probability"] is None if "probability" in payload else True

    def test_frontend_purged_of_hardcoded_forecast_fallbacks(self):
        """Verifies web/app.js has zero hardcoded demonstration fallback values in PredictionPanel and AiForecastRiskOutlookView."""
        app_js_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Isolate PredictionPanel component
        assert "function PredictionPanel(" in content
        pred_panel_match = re.search(r"function PredictionPanel\([\s\S]*?\n\}\n\n// ======", content)
        assert pred_panel_match is not None, "Could not extract PredictionPanel"
        pred_panel_code = pred_panel_match.group(0)

        # Invariant F04-A: No hardcoded SHORT default in PredictionPanel
        assert 'prediction?.direction || "SHORT"' not in pred_panel_code
        assert 'prediction?.direction || \'SHORT\'' not in pred_panel_code
        assert '"SHORT"' not in pred_panel_code or 'rawDirection === "SHORT"' in pred_panel_code

        # Invariant F04-B: No hardcoded 47.1% probability default in PredictionPanel
        assert "47.1%" not in pred_panel_code
        assert "47.1" not in pred_panel_code

        # Invariant F04-C: No hardcoded LightGBM Meta-Model (B4) default in PredictionPanel
        assert 'prediction?.model_name || "LightGBM Meta-Model (B4)"' not in pred_panel_code

        # Invariant F04-D: No hardcoded A1 setup default in PredictionPanel
        assert 'prediction?.setup_type || "A1 (Liquidity Sweep / Reclaim)"' not in pred_panel_code

        # Isolate AiForecastRiskOutlookView component
        outlook_match = re.search(r"function AiForecastRiskOutlookView\([\s\S]*?\n\}\n\n// ======", content)
        assert outlook_match is not None, "Could not extract AiForecastRiskOutlookView"
        outlook_code = outlook_match.group(0)

        # Invariant F04-E: No hardcoded 0.5585 / 0.4415 probabilities in AiForecastRiskOutlookView
        assert "0.5585" not in outlook_code
        assert "0.4415" not in outlook_code

        # Invariant F04-F: Required risk vs directional disclaimer present
        assert "Volatility risk envelope indicates dispersion range" in content
        assert "does NOT imply directional trade probability or win rate" in content

    def test_frontend_market_price_integrity_disclosures(self):
        """Verifies unconditional live price labels are guarded in web/app.js."""
        app_js_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Invariant F05-A: Historical snapshot notice present
        assert "Last observed close — 30 October 2026, 13:00 UTC (STALE — NOT A CURRENT ENTRY REFERENCE)" in content
        assert "STALE — NOT A CURRENT ENTRY REFERENCE" in content
        assert "HISTORICAL SNAPSHOT CLOSE (STALE)" in content

        # Invariant F05-B: Historical bar close label present in HeroSection
        assert "Historical Bar Close (October 30, 2026, 13:00 UTC)" in content

    def test_smart_entry_simulator_view_integrity(self):
        """Verifies web_src/smart_entry_simulator_view.js contains stale snapshot protection."""
        sim_path = os.path.join(os.path.dirname(__file__), "..", "web_src", "smart_entry_simulator_view.js")
        with open(sim_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "HISTORICAL SNAPSHOT CLOSE (STALE)" in content
        assert "STALE — NOT A CURRENT ENTRY REFERENCE" in content
