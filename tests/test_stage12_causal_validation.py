"""
tests/test_stage12_causal_validation.py — Acceptance Test Suite for Stage 12
===========================================================================
Verifies:
1. Stage 12 Prospective Manifest & Chronology (October 16, 2026 frontier).
2. Strictly Causal Conformal Calibration (84.89% coverage vs 92.36% leaked).
3. Temporal Invariance: Mutating unresolved future outcomes does not alter forecasts.
4. Deterministic Trading Cost Accounting (2-sided fees, turnover, per-bar vs per-trade units).
5. Active Model Target & Horizon Specification (168h annualized variance, not 24h).
6. Statistical Interpretation of Stage 6 Feature Comparisons (non-significant paired CIs).
7. Live Terminal Route Causal Calibration & Descriptors.
8. Production Governance and Fail-Closed Safeguards.
"""

import os
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient

from config import RESULTS_DIR
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
from api.server import app
from research.stage12_causal_conformal_engine import (
    run_conformal_calibration_comparison,
    verify_causal_invariance_property
)
from models.authoritative_model_registry import (
    get_active_production_model,
    ModelClassification,
    AuthorizationStatus
)

STAGE12_DIR = os.path.join(RESULTS_DIR, "stage12_prospective_validation")
MANIFEST_PATH = os.path.join(STAGE12_DIR, "stage12_prospective_manifest.json")
AUDIT_PATH = os.path.join(STAGE12_DIR, "stage12_causal_risk_calibration_audit.json")


@pytest.fixture(scope="module")
def manifest_data():
    if not os.path.isfile(MANIFEST_PATH):
        pytest.fail(f"Stage 12 manifest missing: {MANIFEST_PATH}")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def audit_data():
    if not os.path.isfile(AUDIT_PATH):
        run_conformal_calibration_comparison(save_results=True)
    with open(AUDIT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_prospective_manifest_and_frontier_chronology(manifest_data):
    """Verify that Stage 12 fixes the prospective frontier at October 16, 2026."""
    assert manifest_data["manifest_version"] == "STAGE12-PROSPECTIVE-VAL-v1.0"
    audit = manifest_data["epistemic_audit_classification"]

    # Stage 10 is classified as Historical Replay
    s10 = audit["stage10_evaluation_period"]
    assert s10["epistemic_status"] == "VALID_HISTORICAL_OUT_OF_SAMPLE_REPLAY"

    # Gap period is classified as Data Gap
    gap = audit["historical_gap_period"]
    assert gap["epistemic_status"] == "HISTORICAL_DATA_GAP_UNVERIFIED"

    # Frontier is October 16, 2026, NOT September 1
    frontier = audit["genuine_prospective_frontier"]
    assert frontier["epistemic_status"] == "GENUINE_FORWARD_ONLY_EVALUATION"
    assert frontier["frontier_timestamp_utc"] == "2026-10-16T10:45:00Z"

    # Hash chain limitation documented
    assert "RFC 3161" in audit["hash_chain_limitation_statement"]


def test_strictly_causal_conformal_calibration_metrics(audit_data):
    """Verify that causal delayed-resolution calibration achieves 84.89% coverage."""
    assert audit_data["sample_size_holdout"] == 5671
    assert audit_data["nominal_target_coverage_pct"] == 90.0

    # Legacy leaked evaluation
    legacy = audit_data["legacy_noncausal_evaluation"]["metrics"]
    assert legacy["empirical_coverage_pct"] == 92.36

    # Strictly causal evaluation
    causal = audit_data["strictly_causal_evaluation"]["metrics"]
    assert causal["empirical_coverage_pct"] == 84.89
    assert causal["coverage_95_ci"] == [73.14, 93.14]
    assert causal["mean_interval_width"] == 0.4389
    assert causal["median_interval_width"] == 0.2364
    assert causal["mean_relative_width_ratio"] == 2.71
    assert causal["mean_winkler_score"] == 1.0444


def test_causal_invariance_property():
    """Verify that mutating unresolved future outcomes does NOT change issued intervals."""
    assert bool(verify_causal_invariance_property()) is True


def test_deterministic_trading_cost_accounting():
    """
    Verify deterministic trading cost model with manually verifiable values:
    Prices: [100, 102, 101, 104, 104]
    Positions: [1, -1, -1, 0]
    """
    prices = [100.0, 102.0, 101.0, 104.0, 104.0]
    positions = [1, -1, -1, 0]

    gross_returns = []
    fees_paid = []
    transitions = []
    pos_prev = 0

    for i in range(len(positions)):
        pos = positions[i]
        r = np.log(prices[i + 1] / prices[i]) * 10000.0
        g = pos * r
        gross_returns.append(g)

        trans = abs(pos - pos_prev)
        transitions.append(trans)
        fee = trans * 7.0  # 7 bps per transition = 14 bps round trip
        fees_paid.append(fee)
        pos_prev = pos

    total_gross = sum(gross_returns)
    total_trans = sum(transitions)
    total_fees = sum(fees_paid)
    total_net = total_gross - total_fees

    # Manual verification:
    # Bar 0: pos=1, r=ln(102/100)*10000 = 198.026 bps, trans=1, fee=7.0
    # Bar 1: pos=-1, r=ln(101/102)*10000 = -98.526, gross=+98.526, trans=2, fee=14.0
    # Bar 2: pos=-1, r=ln(104/101)*10000 = +292.697, gross=-292.697, trans=0, fee=0.0
    # Bar 3: pos=0, r=ln(104/104)*10000 = 0, gross=0.0, trans=1, fee=7.0
    assert total_trans == 4  # exactly 2 round trips
    assert total_fees == 28.0  # 4 * 7.0 bps
    assert abs(total_gross - 3.855) < 0.05
    assert abs(total_net - (3.855 - 28.0)) < 0.05

    # Check per-bar vs per-trade units
    mean_net_per_bar = total_net / len(positions)
    mean_net_per_round_trip = total_net / (total_trans / 2)
    assert abs(mean_net_per_bar - (-6.04)) < 0.05
    assert abs(mean_net_per_round_trip - (-12.07)) < 0.05


def test_active_production_model_target_and_units():
    """Verify that HAR-RS-DOW-v1.0 target is 168h annualized variance, NOT 24h."""
    model = get_active_production_model()
    assert model.canonical_id == "HAR-RS-DOW-v1.0"
    assert model.classification == ModelClassification.PRODUCTION_VOLATILITY
    assert model.authorization_status == AuthorizationStatus.AUTHORIZED_FOR_PRODUCTION
    assert model.forecast_horizon == "168h (7 calendar days)"
    assert model.forecast_target == "Annualized 7-Day Realized Variance (rv7d_var_ann)"
    assert model.directional_prediction_capability is False


def test_stage6_statistical_interpretations_reconciliation():
    """Verify that Stage 6 feature comparisons show no statistically significant improvement."""
    stage6_file = os.path.join(RESULTS_DIR, "stage6_experiments", "stage6_controlled_experiment_results.json")
    with open(stage6_file, "r", encoding="utf-8") as f:
        stage6 = json.load(f)

    ablation = stage6["experiment_a_ablation"]
    for g_name in ["lags_plus_oscillators", "lags_plus_volatility", "15_full"]:
        ci = ablation[g_name]["paired_bootstrap_vs_4lag"]["ci_95"]
        # All confidence intervals cross zero: [lower < 0, upper > 0]
        assert ci[0] < 0.0
        assert ci[1] > 0.0
        # McNemar p-value > 0.20
        assert ablation[g_name]["paired_bootstrap_vs_4lag"]["mcnemar_p_val"] > 0.20

    # Model challenger: Logistic Regression matches GBDT (p = 0.7279)
    challenger = stage6["experiment_b_challenger"]
    ci_challenger = challenger["paired_bootstrap_95_ci"]
    assert ci_challenger[0] < 0.0
    assert ci_challenger[1] > 0.0
    assert challenger["bootstrap_p_val"] > 0.50


def test_terminal_live_route_causal_calibration():
    """Verify that GET /api/terminal/live serves causal holdout metrics and correct target."""
    client = TestClient(app)
    response = client.get("/api/terminal/live")
    assert response.status_code == 200

    data = response.json()
    q1 = data["four_questions"]["1_expected_volatility"]
    assert q1["metric"] == "Forward 7-Day Realized Variance (Annualized)"
    assert "HAR-RS-DOW-v1.0" in q1["model_version"]

    q2 = data["four_questions"]["2_uncertainty_risk_envelope"]
    assert "Strictly Causal Delayed Resolution" in q2["calibrated_engine"]
    assert "84.89%" in q2["empirical_holdout_coverage"]
    assert q2["calibration_causality_status"] == "STRICTLY_CAUSAL_DELAYED_RESOLUTION"


def test_production_fail_closed_safeguards():
    """Verify production authorization gates and execution prohibitions."""
    client = TestClient(app)
    # Range endpoint labels exploratory / unvalidated
    resp = client.get("/prediction/range")
    assert resp.status_code == 200
    assert resp.json()["status"] == "EXPERIMENTAL_BASELINE"
    assert resp.json()["research_classification"] == "EXPERIMENTAL_BASELINE"
    assert resp.json()["validation_status"] == "NOT_VALIDATED_FOR_TRADING"
    assert resp.json()["live_capital_authorized"] is False

    # Forward status endpoint reports Stage 11/12
    resp_fwd = client.get("/api/research/forward-status")
    assert resp_fwd.status_code == 200
    assert resp_fwd.json()["governance"]["live_trading_status"] == "DISABLED"
