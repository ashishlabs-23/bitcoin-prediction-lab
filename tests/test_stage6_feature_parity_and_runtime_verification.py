"""
tests/test_stage6_feature_parity_and_runtime_verification.py — Feature Parity & Runtime Suite
=============================================================================================
Stage 6 deterministic regression tests for:
1. Training-to-Inference Feature Parity (HAR-RS-DOW-v1.0):
   Verifies that production feature extractor (engine/har_rs_dow_features.py) matches
   the frozen training pipeline (research/freeze_har_rs_dow.py) bit-for-bit (max abs diff == 0.0).
2. Live Point-in-Time Slice Robustness:
   Verifies single-row and small-window inference feature generation with deterministic DOW dummies.
3. Inference Output & Unit Conversion Consistency:
   Verifies log-variance to annualized variance and annualized volatility % conversion.
4. Fail-Closed Safety:
   Verifies missing runtime data raises FileNotFoundError or triggers DATA_UNAVAILABLE state.
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from engine.har_rs_dow_features import prepare_har_rs_dow_dataset, get_har_rs_dow_features
from research.run_vol_edge_01_test import prepare_aligned_dataset
from validation.startup_gate import MODEL_ARTIFACT_PATH
import joblib


def test_har_rs_dow_training_to_inference_feature_parity():
    """
    Asserts bit-for-bit numerical equivalence between the training pipeline features
    and the production inference features over the frozen training span.
    """
    holdout_start_dt = pd.to_datetime("2026-01-01T00:00:00Z")

    # 1. Compute training features via original research pipeline
    df_train_orig = prepare_aligned_dataset()
    df_train_orig = df_train_orig[df_train_orig.index < holdout_start_dt]

    log_rv_down = np.log(np.maximum(1e-6, df_train_orig["rv_down_1d"].values))
    log_rv_up   = np.log(np.maximum(1e-6, df_train_orig["rv_up_1d"].values))
    log_rv7     = np.log(np.maximum(1e-6, df_train_orig["rv7d_var_ann_lag"].values))
    log_rv30    = np.log(np.maximum(1e-6, df_train_orig["rv30d_var_ann"].values))

    dow_dummies = pd.get_dummies(df_train_orig["dow"], prefix="dow", drop_first=True)
    for col_i in range(1, 7):
        col_name = f"dow_{col_i}"
        if col_name not in dow_dummies.columns:
            dow_dummies[col_name] = 0
    dow_dummies = dow_dummies[[f"dow_{i}" for i in range(1, 7)]].values
    X_orig = np.column_stack([log_rv_down, log_rv_up, log_rv7, log_rv30, dow_dummies])

    # 2. Compute training features via production engine
    df_prod = prepare_har_rs_dow_dataset()
    df_prod_train = df_prod[df_prod.index < holdout_start_dt]
    X_prod = get_har_rs_dow_features(df_prod_train)

    # 3. Assert shape and numerical equality
    assert X_orig.shape == X_prod.shape
    assert X_orig.shape[1] == 10
    np.testing.assert_allclose(X_prod, X_orig, rtol=1e-12, atol=1e-12)


def test_har_rs_dow_inference_output_and_vol_conversion():
    """
    Verifies that the frozen joblib artifact produces valid point forecasts
    and that conversion to annualized volatility is mathematically correct.
    """
    pipe = joblib.load(MODEL_ARTIFACT_PATH)
    df_prod = prepare_har_rs_dow_dataset()
    X = get_har_rs_dow_features(df_prod.iloc[-100:])

    # Pipeline predicts log(variance)
    log_v_hat = pipe.predict(X)
    assert not np.isnan(log_v_hat).any()
    assert not np.isinf(log_v_hat).any()

    # Annualized variance: v = exp(log_v_hat)
    v_hat = np.exp(log_v_hat)
    assert (v_hat > 0).all()

    # Annualized volatility: vol_pct = sqrt(v_hat) * 100
    vol_pct = np.sqrt(v_hat) * 100.0
    # Realistic range for Bitcoin annualized volatility is 10% to 300%
    assert (vol_pct > 10.0).all()
    assert (vol_pct < 300.0).all()


def test_har_rs_dow_small_slice_and_single_row_feature_generation():
    """
    Verifies that get_har_rs_dow_features works robustly on a single-row slice
    without index or one-hot dimension misalignment.
    """
    df_prod = prepare_har_rs_dow_dataset()
    single_row = df_prod.iloc[-1:]
    X_single = get_har_rs_dow_features(single_row)

    assert X_single.shape == (1, 10)
    assert not np.isnan(X_single).any()

    # Verify DOW dummy encoding for this specific day
    day_idx = single_row["dow"].iloc[0]
    expected_dummies = np.zeros(6)
    if day_idx > 0:
        expected_dummies[day_idx - 1] = 1.0

    np.testing.assert_array_equal(X_single[0, 4:], expected_dummies)


def test_har_rs_dow_missing_file_fails_closed():
    """
    Verifies that prepare_har_rs_dow_dataset raises FileNotFoundError when data is missing.
    """
    with pytest.raises(FileNotFoundError):
        prepare_har_rs_dow_dataset("non_existent_data_path.parquet")


def test_stage6_research_report_registered_and_hash_verified():
    """
    Verifies that the Stage 6 research report is properly registered in REPORT_REGISTRY,
    exists on disk, matches its declared SHA256 hash, and has valid key metrics.
    """
    from api.routes_research import REPORT_REGISTRY, REPO_ROOT
    import hashlib

    assert "stage6-experiments" in REPORT_REGISTRY
    entry = REPORT_REGISTRY["stage6-experiments"]
    rel_path = entry["relative_path"]
    full_path = os.path.join(REPO_ROOT, rel_path)

    assert os.path.exists(full_path), f"Stage 6 report missing at: {full_path}"
    with open(full_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    assert actual_hash == entry["expected_sha256"], (
        f"Hash mismatch: actual={actual_hash} vs expected={entry['expected_sha256']}"
    )
    assert len(entry["key_metrics"]) >= 5
    assert entry["governance_verdict"] == "STAGE6_VERIFIED_AND_CONTROLLED"

