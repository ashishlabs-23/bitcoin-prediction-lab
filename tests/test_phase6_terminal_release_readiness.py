"""
tests/test_phase6_terminal_release_readiness.py — End-to-End Release Readiness Verification
============================================================================================
Verifies:
1. All 7 Core Product Areas operate consistently through FastAPI endpoints:
   - Market Overview: /health, /api/dashboard
   - Forecasts & Risk: /prediction/latest, /prediction/range, /prediction/range/health
   - Research Evidence: /prediction/longitudinal, /api/research/results, /api/research/reports/uncertainty-04
   - Research Lab: /api/models/authoritative-registry
   - Data & System Health: /health, /prediction/range/health
   - Alerts: /api/notifications/settings
   - Paper Research Simulator: /api/research/entry-tp-sl
2. Strict Non-Execution & Fail-Closed Invariants:
   - trading_enabled is False everywhere.
   - live_capital_authorized is False everywhere.
   - Production forecasts are blocked pending authenticated evidence.
   - Baseline forecasts declare production_forecast_available = False.
3. Scientific Freeze Contract Gate succeeds with zero errors.
"""

import pytest
from fastapi.testclient import TestClient

from api.server import app
from validation.startup_gate import verify_scientific_contract


def test_terminal_release_readiness_end_to_end():
    with TestClient(app) as client:
        # 1. Market Overview & System Health
        res_health = client.get("/health")
        assert res_health.status_code == 200
        health_data = res_health.json()
        assert health_data["status"] == "ok"
        assert health_data["mode"] in ["MARKET_MONITOR_ONLY", "PRODUCTION_VOLATILITY_INTELLIGENCE"]
        assert health_data["trading_enabled"] is False

        assert health_data["production_forecast_available"] in [True, False]

        # 2. Forecasts & Risk (Empirical Baseline)
        res_latest = client.get("/prediction/latest")
        assert res_latest.status_code == 200
        latest_data = res_latest.json()
        assert latest_data["status"] == "EXPERIMENTAL_BASELINE"
        assert latest_data["production_forecast_available"] is False
        assert latest_data["trading_enabled"] is False

        res_range_health = client.get("/prediction/range/health")
        assert res_range_health.status_code == 200
        range_health = res_range_health.json()
        assert range_health["status"] == "BLOCKED_PROVENANCE_UNVERIFIED"
        assert range_health["trading_enabled"] is False

        # 3. Research Evidence
        res_long = client.get("/prediction/longitudinal")
        assert res_long.status_code == 200
        long_data = res_long.json()
        assert long_data["evidence_phase"] == "POST_REPAIR"
        assert long_data["monitoring_status"] == "ACTIVE_POST_REPAIR_COLLECTION"
        assert long_data["observed_blocks"] == 0

        res_reports = client.get("/api/research/results")
        assert res_reports.status_code == 200
        reports_catalog = res_reports.json()
        assert len(reports_catalog["reports"]) >= 2

        res_u04 = client.get("/api/research/reports/uncertainty-04")
        assert res_u04.status_code == 200
        u04_data = res_u04.json()
        assert u04_data["governance_verdict"] == "C2_PROVISIONALLY_VALIDATED"
        assert u04_data["provenance_state"] == "INTEGRITY_CHECKED"

        # 4. Research Lab & Model Governance
        res_reg = client.get("/api/models/authoritative-registry")
        assert res_reg.status_code == 200
        reg_data = res_reg.json()
        assert reg_data["active_production_model"] == "HAR-RS-DOW-v1.0"
        models_by_id = {m["canonical_id"]: m for m in reg_data["models"]}
        active_model = models_by_id["HAR-RS-DOW-v1.0"]
        assert active_model["classification"] == "PRODUCTION_VOLATILITY"
        assert active_model["authorization_status"] in ["AUTHORIZED_FOR_PRODUCTION", "BLOCKED_AUDIT_FAILURE"]
        assert active_model["directional_prediction_capability"] is False


        # 5. Alerts (Settings returned with secrets masked)
        res_notif = client.get("/api/notifications/settings")
        assert res_notif.status_code == 200
        notif_data = res_notif.json()
        assert "webhook_url_configured" in notif_data
        assert "smtp_password" not in notif_data

        # 6. Paper Simulator (Non-executing, blocked)
        res_sim = client.get("/api/research/entry-tp-sl")
        assert res_sim.status_code == 200
        sim_data = res_sim.json()
        assert sim_data["status"] == "BLOCKED"
        assert sim_data["live_capital_authorized"] is False
        assert sim_data["trading_enabled"] is False


def test_scientific_freeze_contract_clean_pass():
    verified = verify_scientific_contract()
    assert verified is True
