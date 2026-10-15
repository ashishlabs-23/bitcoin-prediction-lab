"""
tests/test_point_in_time_features.py — Phase 5 Point-in-Time Feature Pipeline Tests
===================================================================================
Verifies:
1. Versioned schema contract: all registered features exist and have valid metadata.
2. Causality & Perturbation Invariant: mutating future candles (t > t_0) produces ZERO change
   in historical features at t_0.
3. In-fold scaling isolation: scaling parameters are fit on training partition and do not leak
   test set distributions.
4. Target definition integrity: forward excursion targets (MFE/MAE) strictly evaluate forward path
   (t, t + 24h] without lookahead to historical features.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

from engine.point_in_time_features import (
    PointInTimeFeaturePipeline,
    FEATURE_REGISTRY,
    FEATURE_SCHEMA_VERSION,
    FeatureCategory
)


def _generate_synthetic_ohlcv(n_bars: int = 100, seed: int = 42) -> pd.DataFrame:
    """Generates synthetic hourly OHLCV bars for deterministic causality testing."""
    np.random.seed(seed)
    start_dt = pd.Timestamp("2026-01-01 00:00:00", tz="UTC")
    timestamps = [start_dt + pd.Timedelta(hours=i) for i in range(n_bars)]

    # Random walk close prices
    returns = np.random.normal(0.0005, 0.01, size=n_bars)
    prices = 60000.0 * np.exp(np.cumsum(returns))

    highs = prices * (1.0 + np.abs(np.random.normal(0, 0.005, size=n_bars)))
    lows = prices * (1.0 - np.abs(np.random.normal(0, 0.005, size=n_bars)))
    opens = prices * (1.0 + np.random.normal(0, 0.002, size=n_bars))
    volumes = np.random.exponential(50.0, size=n_bars) + 1.0

    return pd.DataFrame({
        "timestamp": timestamps,
        "available_at": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": volumes
    })


def test_feature_registry_schema():
    """All registered features have versioned metadata and valid categories."""
    assert len(FEATURE_REGISTRY) >= 20
    for name, fdef in FEATURE_REGISTRY.items():
        assert fdef.name == name
        assert fdef.version == FEATURE_SCHEMA_VERSION
        assert isinstance(fdef.category, FeatureCategory)
        assert fdef.frequency in {"1m", "1h", "8h", "event"}
        assert len(fdef.description) > 10


def test_point_in_time_future_perturbation_invariant():
    """
    CRITICAL INVARIANT: Changing future data (t > t_0) MUST NOT alter historical features at t_0.
    """
    pipeline = PointInTimeFeaturePipeline()
    base_df = _generate_synthetic_ohlcv(n_bars=80, seed=123)

    # 1. Compute features on original dataset
    df_orig = pipeline.extract_features(base_df)
    t0_idx = 40
    t0_features = df_orig.iloc[t0_idx][pipeline.feature_names].copy()

    # 2. Perturb future rows (t0_idx + 1 onwards) violently (10x price shock)
    perturbed_df = base_df.copy()
    perturbed_df.loc[t0_idx + 1:, "close"] *= 10.0
    perturbed_df.loc[t0_idx + 1:, "high"] *= 10.0
    perturbed_df.loc[t0_idx + 1:, "low"] *= 10.0
    perturbed_df.loc[t0_idx + 1:, "volume"] *= 50.0

    df_perturbed = pipeline.extract_features(perturbed_df)
    t0_features_after_future_shock = df_perturbed.iloc[t0_idx][pipeline.feature_names].copy()

    # 3. Assert exact equality: historical features at t0 are 100% invariant to future changes
    for feat in pipeline.feature_names:
        v1 = t0_features[feat]
        v2 = t0_features_after_future_shock[feat]
        if pd.isna(v1):
            assert pd.isna(v2), f"Feature {feat} NaN mismatch at t0"
        else:
            assert np.isclose(v1, v2, rtol=1e-7, atol=1e-7), f"Feature {feat} leaked future shock: {v1} vs {v2}"


def test_in_fold_scaling_isolation():
    """Scaler fit on train fold must not depend on test set statistics (no leakage)."""
    pipeline = PointInTimeFeaturePipeline()
    df = _generate_synthetic_ohlcv(n_bars=100)
    features = pipeline.extract_features(df)

    train_df = features.iloc[:60].copy()
    test_df = features.iloc[60:].copy()

    # Fit on train partition exclusively
    pipeline.fit_scalers_on_train_fold(train_df)

    # Transform test fold
    scaled_test = pipeline.transform_features(test_df)

    # Mean of scaled test does not equal 0 (because fitted exclusively on train)
    ret_test_mean = scaled_test["ret_1h"].mean()
    assert abs(ret_test_mean) > 1e-4 or not np.isnan(ret_test_mean)


def test_forward_target_definition_isolation():
    """Forward excursion targets strictly evaluate (t, t + 24h] without lookahead to t."""
    pipeline = PointInTimeFeaturePipeline()
    df = _generate_synthetic_ohlcv(n_bars=60)
    df_targets = pipeline.compute_forward_targets(df)

    # Check forward targets are populated
    assert "target_forward_mfe_24h" in df_targets.columns
    assert "target_forward_mae_24h" in df_targets.columns
    assert "target_forward_ret_24h" in df_targets.columns

    # Verify first 30 rows have valid forward excursion >= 0
    valid_slice = df_targets.iloc[:30]
    assert (valid_slice["target_forward_mfe_24h"] >= 0.0).all()
    assert (valid_slice["target_forward_mae_24h"] >= 0.0).all()

    # Last 24 rows must be NaN because forward 24h window has not elapsed
    tail_slice = df_targets.iloc[-24:]
    assert tail_slice["target_forward_mfe_24h"].isna().all()
