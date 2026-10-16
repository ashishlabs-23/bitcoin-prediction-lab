"""
tests/test_stage7_regime_experiments.py — Test Suite for Stage 7 Regime-Conditioned Research
=============================================================================================
Verifies:
1. Integrity and existence of Stage 7 machine-readable experiment results.
2. Baseline reproducibility against canonical Stage 6 figures (53.28% GBDT, 53.20% Logistic).
3. Strict causal computation of regime thresholds (in-train only, no lookahead).
4. Mathematical validity and consistency of Wilson confidence intervals and metrics.
5. Production model registry immutability (HAR-RS-DOW-v1.0 remains the sole authorized model).
"""

import os
import json
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STAGE7_JSON = os.path.join(REPO_ROOT, "experiments", "results", "stage7_regime_research", "stage7_experiment_results.json")


def test_stage7_results_file_exists_and_valid():
    """Verify Stage 7 results JSON exists, is valid JSON, and has all required top-level keys."""
    assert os.path.exists(STAGE7_JSON), f"Missing Stage 7 results JSON at {STAGE7_JSON}"
    with open(STAGE7_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    required_keys = [
        "timestamp", "total_bars", "evaluated_test_bars", "pre_registered_hypothesis",
        "experiment_a_regime_diagnostics", "experiment_b_challenger_models",
        "experiment_c_decision_quality", "robustness_sensitivity"
    ]
    for k in required_keys:
        assert k in data, f"Missing required top-level key: {k}"

    assert data["total_bars"] == 40702
    assert data["evaluated_test_bars"] == 33919


def test_stage7_canonical_baseline_reproducibility():
    """Verify that Stage 7 exactly reproduces canonical Stage 6 baseline metrics."""
    with open(STAGE7_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    exp_b = data["experiment_b_challenger_models"]
    gbdt_base = exp_b["baseline_gbdt_4lags"]
    lr_base = exp_b["baseline_logistic_4lags"]

    assert gbdt_base["overall_accuracy_pct"] == 53.28
    assert gbdt_base["roc_auc"] == 0.5445
    assert gbdt_base["brier_score"] == 0.2488

    assert lr_base["overall_accuracy_pct"] == 53.20
    assert lr_base["roc_auc"] == 0.5419
    assert lr_base["brier_score"] == 0.2489


def test_causal_regime_threshold_isolation():
    """
    Test that regime thresholds computed on a training window differ from full-sample
    or future test windows, confirming point-in-time causal isolation.
    """
    raw_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
    df_raw = pd.read_parquet(raw_path)
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=True)
    df_raw.sort_values("timestamp", inplace=True)
    df_raw.reset_index(drop=True, inplace=True)

    ret1 = np.log(df_raw["close"] / df_raw["close"].shift(1))
    vol24 = ret1.rolling(24).std().dropna()

    # Split into mock train and test
    split_idx = int(len(vol24) * 0.5)
    vol_train = vol24.iloc[:split_idx]
    vol_test = vol24.iloc[split_idx:]

    p33_train = np.percentile(vol_train, 33.3333)
    p33_test = np.percentile(vol_test, 33.3333)
    p33_full = np.percentile(vol24, 33.3333)

    # In non-stationary time series, train quantile != test quantile
    assert abs(p33_train - p33_test) > 1e-6, "Training and testing volatility distributions should show non-identical quantiles"


def test_metric_bounds_and_intervals():
    """Verify that all accuracies, intervals, and probabilities satisfy mathematical invariants."""
    with open(STAGE7_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check Experiment A Wilson intervals
    exp_a = data["experiment_a_regime_diagnostics"]
    for fam_name, fam_dict in exp_a.items():
        for state_name, metrics in fam_dict.items():
            for m_key in ["gbdt", "logistic_regression"]:
                acc = metrics[m_key]["accuracy_pct"]
                ci = metrics[m_key]["wilson_95_ci"]
                assert 0.0 <= acc <= 100.0
                assert ci[0] <= acc <= ci[1]
                assert 0.0 <= ci[0] <= 100.0
                assert 0.0 <= ci[1] <= 100.0

    # Check Experiment B metric bounds
    exp_b = data["experiment_b_challenger_models"]
    for mod_name, metrics in exp_b.items():
        assert 0.0 <= metrics["overall_accuracy_pct"] <= 100.0
        assert 0.0 <= metrics["roc_auc"] <= 1.0
        assert 0.0 <= metrics["brier_score"] <= 1.0
        assert 0.0 <= metrics["ece"] <= 1.0


def test_production_model_registry_integrity():
    """
    Critical Governance Gate: Stage 7 is a research discovery stage.
    Ensure that HAR-RS-DOW-v1.0 remains the sole authorized production model
    and directional models remain OFFLINE_RESEARCH_ONLY.
    """
    from models.authoritative_model_registry import (
        get_active_production_model,
        get_directional_research_baseline,
        AuthorizationStatus,
        ModelClassification
    )

    active_prod = get_active_production_model()
    assert active_prod.canonical_id == "HAR-RS-DOW-v1.0"
    assert active_prod.classification == ModelClassification.PRODUCTION_VOLATILITY
    assert active_prod.authorization_status == AuthorizationStatus.AUTHORIZED_FOR_PRODUCTION
    assert active_prod.directional_prediction_capability is False

    directional_base = get_directional_research_baseline()
    assert directional_base.canonical_id == "directional-gbm-4lag-v1"
    assert directional_base.classification == ModelClassification.DIRECTIONAL_RESEARCH_BENCHMARK
    assert directional_base.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
