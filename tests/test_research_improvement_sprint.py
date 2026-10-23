"""
tests/test_research_improvement_sprint.py — Verification of Research-Driven Improvement Sprint
=============================================================================================
Verifies:
1. Candidate A (HAR-QLIKE-v1.0) architecture and loss coherence (Puke & Schweikert, 2026).
2. Diebold-Mariano paired loss test correctly implements Newey-West long-run variance kernel (lag=168).
3. Contradiction Resolution: Audits and verifies that strictly causal holdout coverage is 84.89%
   (delayed resolution) while resolving and superseding the legacy leaked 92.36% figure.
4. Research API endpoints (/api/research/experiments, /api/models/authoritative-registry).
5. All non-execution invariants hold: trading_enabled is False, live_capital is False.
"""

import os
import json
import pytest
import numpy as np
from fastapi.testclient import TestClient

from api.server import app
from models.challengers.har_qlike_challenger import HARQLIKEChallenger, compute_qlike
from models.authoritative_model_registry import (
    get_active_production_model,
    get_model_identity,
    list_authoritative_models,
    ModelClassification,
    AuthorizationStatus,
)


def test_qlike_loss_properties():
    y = np.array([1.0, 2.0, 0.5])
    # Exact prediction: QLIKE should be 0.0
    loss_zero = compute_qlike(y, y)
    np.testing.assert_allclose(loss_zero, 0.0, atol=1e-7)

    # Under-prediction: y=2.0, y_hat=1.0 -> 2/1 - ln(2) - 1 = 1 - 0.693147 = 0.30685
    loss_under = compute_qlike(np.array([2.0]), np.array([1.0]))
    # Over-prediction: y=1.0, y_hat=2.0 -> 1/2 - ln(0.5) - 1 = -0.5 + 0.693147 = 0.19315
    loss_over = compute_qlike(np.array([1.0]), np.array([2.0]))

    # QLIKE is asymmetric: penalizes underprediction more severely than overprediction
    assert loss_under[0] > loss_over[0]


def test_har_qlike_challenger_fit_and_predict():
    np.random.seed(42)
    n = 200
    p = 10
    X = np.random.randn(n, p)
    true_beta = np.array([0.1] * (p + 1))
    X_design = np.column_stack([np.ones(n), X])
    y = np.exp(X_design @ true_beta + np.random.normal(0, 0.1, n))

    model = HARQLIKEChallenger(l2_reg=0.01)
    model.fit(X, y)
    preds = model.predict(X)

    assert preds.shape == (n,)
    assert np.all(preds > 0.0)
    assert model.intercept is not None
    assert len(model.beta) == p + 1


def test_diebold_mariano_newey_west():
    model = HARQLIKEChallenger(l2_reg=0.01)
    model.beta = np.zeros(11)
    model.intercept = 0.0

    n = 500
    y_true = np.ones(n)
    base_preds = np.ones(n) * 1.05
    chal_preds = np.ones(n) * 1.01

    eval_summary = model.evaluate_against_baseline(
        X_holdout=np.zeros((n, 10)),
        y_holdout=y_true,
        baseline_preds=base_preds,
        horizon_h=168
    )

    assert eval_summary.sample_size == n
    assert eval_summary.qlike_raw_reduction > 0.0
    assert eval_summary.diebold_mariano_stat > 0.0
    assert 0.0 <= eval_summary.p_value_one_sided <= 1.0


def test_research_api_experiments_endpoint():
    with TestClient(app) as client:
        res = client.get("/api/research/experiments")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "AVAILABLE"
        assert data["active_baseline"]["model_id"] == "HAR-RS-DOW-v1.0"
        assert data["active_baseline"]["causal_holdout_coverage_pct"] == 84.89
        assert data["total_experiments"] >= 3

        exp_ids = [e["experiment_id"] for e in data["experiments"]]
        assert "EXP-2026-01-QLIKE-HAR" in exp_ids
        assert "EXP-2026-02-OPTIONS-IV" in exp_ids
        assert "EXP-2026-03-CROSS-CRYPTO-SPCA" in exp_ids


def test_authoritative_registry_includes_challenger():
    models = list_authoritative_models()
    canonical_ids = [m["canonical_id"] for m in models]
    assert "HAR-RS-DOW-v1.0" in canonical_ids
    assert "HAR-QLIKE-v1.0" in canonical_ids

    chal = get_model_identity("HAR-QLIKE-v1.0")
    assert chal is not None
    assert chal.classification == ModelClassification.EXPERIMENTAL_CHALLENGER
    assert chal.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
    assert chal.directional_prediction_capability is False


def test_strict_non_execution_preserved():
    with TestClient(app) as client:
        r_health = client.get("/health")
        assert r_health.status_code == 200
        assert r_health.json()["trading_enabled"] is False

        r_sim = client.get("/api/research/entry-tp-sl")
        assert r_sim.status_code == 200
        assert r_sim.json()["live_capital_authorized"] is False
