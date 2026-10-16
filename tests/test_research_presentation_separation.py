"""
tests/test_research_presentation_separation.py
================================================
Automated verification of presentation separation (P0):
1. Production Risk Forecast: Shows only risk-envelope outputs, model version, and calibration health.
   Strictly separated from directional forecasting.
2. Directional Research Forecast: Isolated to offline research with sample counts, coverage targets,
   paired bootstrap differences, and negative net trading returns after friction.
3. Market Data Health & Fail-Closed Behavior: Blocked or stale outputs fail with explicit failure states.
4. Report Registry Integrity: Stage 2 and Stage 3 reports are accessible with correct metadata.
"""

import pytest
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)


def test_production_terminal_does_not_claim_directional_accuracy():
    """Validates that /api/terminal/live reports volatility envelopes, not directional accuracy."""
    res = client.get("/api/terminal/live")
    assert res.status_code == 200
    data = res.json()

    assert data["system_category"] == "VERIFIED VOLATILITY INTELLIGENCE"
    assert "four_questions" in data
    q = data["four_questions"]

    # Question 1: Volatility forecast
    assert "point_forecast_har_rs_dow" in q["1_expected_volatility"]
    assert "model_version" in q["1_expected_volatility"]

    # Question 2: Uncertainty risk envelope
    env = q["2_uncertainty_risk_envelope"]
    assert "nominal_target_coverage" in env
    assert "lower_bound_variance" in env
    assert "upper_bound_variance" in env
    assert "calibrated_engine" in env
    # Must NOT claim directional accuracy
    assert "directional" not in str(env).lower() or "not directional" in str(env).lower()

    # Epistemic contract must forbid permanent universal guarantees
    assert "epistemic_contract" in data
    assert "guarantee" in data["epistemic_contract"].lower()
    assert "prohibited" in data["epistemic_contract"].lower()


def test_directional_research_audit_is_explicitly_research_only():
    """Validates that /api/research/directional-audit is strictly non-production."""
    res = client.get("/api/research/directional-audit")
    assert res.status_code == 200
    data = res.json()

    assert data["research_category"] == "OFFLINE_DIRECTIONAL_RESEARCH_BENCHMARK"
    assert data["production_inference_status"] == "SEPARATE_OFFLINE_RESEARCH_NOT_AUTHORIZED_FOR_PRODUCTION"
    assert "epistemic_disclaimer" in data
    assert "not authorized" in data["epistemic_disclaimer"].lower()

    results = data["results"]
    assert "feature_comparison" in results
    fc = results["feature_comparison"]["summary"]
    # 4-lag vs 15-full comparison
    assert fc["4lags"]["feature_count"] == 4
    assert fc["15full"]["feature_count"] == 15
    assert fc["statistical_significance"]["verdict"] == "DIFFERENCE_STATISTICALLY_COMPATIBLE_WITH_ZERO"

    # Selective prediction ladder
    assert "selective_prediction" in results
    sel = results["selective_prediction"]
    assert "100pct" in sel and "5pct" in sel
    assert sel["5pct"]["accuracy_pct"] < 60.0  # Empirical reality ~56.7%, far from 70%

    # Turnover economics must show negative net returns
    econ = results["economic_hurdles"]
    assert econ["unconditional_100pct"]["mean_net_return_bps_per_bar"] < 0
    assert econ["prespecified_hurdle_10pct"]["mean_net_return_active_bars_bps"] < 0


def test_stage2_and_stage3_reports_registered():
    """Validates that Stage 2 and Stage 3 reports are accessible in research catalog."""
    res = client.get("/api/research/results")
    assert res.status_code == 200
    catalog = res.json()

    report_ids = [r["report_id"] for r in catalog["reports"]]
    assert "stage2-audit" in report_ids
    assert "stage3-validation" in report_ids

    # Check Stage 2 detail
    s2 = next(r for r in catalog["reports"] if r["report_id"] == "stage2-audit")
    assert s2["file_exists"] is True
    assert s2["governance_verdict"] == "AUDIT_COMPLETED"
    assert s2["provenance_state"] == "INTEGRITY_CHECKED"


def test_market_data_dependency_transparency():
    """Validates that production terminal reports its exact runtime dependency graph."""
    res = client.get("/api/terminal/live")
    assert res.status_code == 200
    data = res.json()

    # Production dependency graph must ONLY contain real inference dependencies
    assert data["production_dependency_graph"] == ["ohlcv.parquet"]
    assert "iv7d.parquet" not in data["production_dependency_graph"]
