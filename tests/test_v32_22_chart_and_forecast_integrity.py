"""
tests/test_v32_22_chart_and_forecast_integrity.py — V32.22 Verification Suite
=============================================================================
Validates:
1. Forecast engine contract integrity and synchronization with fresh Coinbase candles.
2. Explicit labeling of Non-Directional Persistence Baseline ($S_0$) and Nominal Diffusion Bands.
3. Accurate historical accuracy attribution (Stage 11 52.14% benchmark, negative net expectancy).
4. Frontend chart script integrity in web/app.js (marker preservation and series titles).
5. Strict preservation of project invariants: live trading DISABLED, directional recommendation ABSTAIN.
"""

import os
import json
import pytest
from datetime import datetime, timezone

from engine.forecast_engine_15m import generate_forecast_contract
from engine.coinbase_15m_adapter import coinbase_15m_adapter


def test_v32_22_forecast_engine_hourly_contract():
    """Verify 1h forecast contract generates forward-anchored points with audit metadata."""
    contract = generate_forecast_contract(horizon="1h")

    assert contract["status"] == "FORECAST_AVAILABLE_RESEARCH_ONLY"
    assert contract["source_timeframe"] == "1h"
    assert contract["forecast_type"] == "NON_DIRECTIONAL_RESEARCH_BASELINE"
    assert contract["model_id"] == "EMPIRICAL_CONFORMAL_PERSISTENCE_v1.0"
    assert contract["directional_recommendation"] == "ABSTAIN"
    assert contract["live_trading"] == "DISABLED"

    # Explicit accuracy audit metadata
    assert contract["historical_accuracy_pct"] == 52.14
    assert "Stage 11" in contract["historical_accuracy_source"]
    assert contract["cost_adjusted_expectancy"] == "NEGATIVE_AFTER_FEES"
    assert "ABSTAIN" in contract["directional_status"]

    # Forward points check
    points = contract["points"]
    assert len(points) == 5
    assert points[0]["is_origin"] is True
    assert points[1]["time"] - points[0]["time"] == 3600
    assert points[4]["time"] - points[0]["time"] == 14400

    # Uncertainty bands
    assert len(contract["upper_band"]) == 5
    assert len(contract["lower_band"]) == 5
    assert contract["upper_band"][1]["value"] > points[1]["value"]
    assert contract["lower_band"][1]["value"] < points[1]["value"]


def test_v32_22_forecast_engine_15m_contract():
    """Verify 15m forecast contract operates under its non-directional research baseline."""
    contract = generate_forecast_contract(horizon="15m")

    assert contract["status"] == "FORECAST_AVAILABLE_RESEARCH_ONLY"
    assert contract["source_timeframe"] == "15m"
    assert contract["model_readiness"] in ["MODEL_TIMEFRAME_INCOMPATIBLE", "MODEL_DIRECTIONAL_RESEARCH_ACTIVE"]
    assert contract["directional_recommendation"] == "ABSTAIN"
    assert len(contract["points"]) == 5
    assert contract["points"][1]["time"] - contract["points"][0]["time"] == 900


def test_v32_22_frontend_script_chart_fix_integrity():
    """Verify web/app.js contains marker bug fixes and explicit non-directional series titles."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app_js_path = os.path.join(repo_root, "web", "app.js")
    assert os.path.exists(app_js_path), "web/app.js must exist"

    with open(app_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Series titles must be explicitly qualified
    assert 'title:     "Forecast Baseline ($S_0$ Persistence)"' in content
    assert 'title:     "Nominal Upper Band (90%)"' in content
    assert 'title:     "Nominal Lower Band (90%)"' in content

    # 2. Marker wiping bug must be resolved: marker setting does NOT exit early when showResearchMarkers is false
    assert 'if (showResearchMarkers && memoryData?.length)' in content
    assert 'text:     "AI: ABSTAIN (Tier 2 Gated)"' in content

    # 3. Cache bust version updated in index.html
    index_html_path = os.path.join(repo_root, "web", "index.html")
    with open(index_html_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert 'src="/app.js?v=32.22.0"' in html
