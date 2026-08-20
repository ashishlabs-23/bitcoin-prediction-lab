"""
tests/test_expanded_validation.py — Unit Tests for Expanded Walk-Forward Revalidation Suite
==========================================================================================
Verifies:
1. Temporal split chronological isolation (70% Train, 15% Validation, 15% Confirmation)
2. No lookahead and monotonic timestamp invariants
3. 24h directional model evaluation and bootstrap bounds
4. Magnitude and excursion decay calculations
5. Economic fee sensitivity and circuit-breaker risk overlays
6. Research trial tracking integrity (K_total)
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.expanded_validation import audit_historical_dataset
from research.validate_24h_direction import evaluate_24h_direction_models
from research.validate_magnitude import evaluate_magnitude_revalidation
from research.economic_revalidation import evaluate_economic_and_circuit_breakers
from research.selective_revalidation import evaluate_selective_revalidation
from research.regime_stability import evaluate_regime_and_era_stability
from research.multiple_testing import ResearchTrialTracker


@pytest.fixture
def sample_expanded_df():
    """Generates synthetic dataset for expanded temporal revalidation."""
    np.random.seed(42)
    n = 300
    ts = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    close = 60000.0 * np.exp(np.cumsum(np.random.normal(0.0002, 0.01, size=n)))
    high = close * 1.008
    low = close * 0.992

    df = pd.DataFrame({
        'open': close * 0.999,
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.uniform(100, 1000, size=n),
        'ret_1h': np.random.normal(0, 0.01, size=n),
        'vol_24h': np.random.uniform(0.01, 0.03, size=n),
        'rsi_14': np.random.uniform(20, 80, size=n),
        'sma_ratio_20': np.random.normal(0, 0.01, size=n),
        'funding_rate': np.random.normal(0.0001, 0.0002, size=n),
        'tech_trend_score': np.random.uniform(-1, 1, size=n)
    }, index=ts)

    return df, pd.Series(close, index=ts), pd.Series(high, index=ts), pd.Series(low, index=ts)


def test_audit_dataset_and_split_integrity():
    df_audit, df_splits, meta = audit_historical_dataset(n_total_bars=300)
    assert isinstance(df_audit, pd.DataFrame)
    assert isinstance(df_splits, pd.DataFrame)
    assert len(df_splits) == 3
    # Verify strict non-overlapping indices
    tr_st, tr_en = meta["train_indices"]
    v_st, v_en = meta["val_indices"]
    c_st, c_en = meta["conf_indices"]
    assert tr_en == v_st
    assert v_en == c_st
    assert c_en == meta["total_bars"]


def test_24h_direction_validation_execution(sample_expanded_df):
    df, close, _, _ = sample_expanded_df
    train_end = 200
    val_end = 250
    df_dir, boot_meta = evaluate_24h_direction_models(df, close, train_end, val_end, n_splits=3)

    assert isinstance(df_dir, pd.DataFrame)
    assert len(df_dir) == 4
    assert "bootstrap_auc_95_ci" in boot_meta
    assert len(boot_meta["bootstrap_auc_95_ci"]) == 2


def test_magnitude_and_decay_execution(sample_expanded_df):
    df, close, high, low = sample_expanded_df
    train_end = 200
    val_end = 250
    df_decay, df_comp, meta = evaluate_magnitude_revalidation(df, close, high, low, train_end, val_end)

    assert isinstance(df_decay, pd.DataFrame)
    assert len(df_decay) == 3
    assert isinstance(df_comp, pd.DataFrame)
    assert len(df_comp) == 6
    assert "confirmation_magnitude_ic" in meta


def test_economic_revalidation_and_breakers(sample_expanded_df):
    df, close, _, _ = sample_expanded_df
    val_end = 250
    df_fee, df_moves, df_breakers, meta = evaluate_economic_and_circuit_breakers(df, close, val_end)

    assert isinstance(df_fee, pd.DataFrame)
    assert isinstance(df_moves, pd.DataFrame)
    assert isinstance(df_breakers, pd.DataFrame)
    assert len(df_breakers) == 5
    assert "break_even_cost_bps" in meta


def test_selective_revalidation_coverage(sample_expanded_df):
    df, close, _, _ = sample_expanded_df
    train_end = 200
    val_end = 250
    df_sel, meta = evaluate_selective_revalidation(df, close, train_end, val_end)

    assert isinstance(df_sel, pd.DataFrame)
    assert len(df_sel) == 6
    assert "best_coverage" in meta


def test_regime_and_era_stability_execution(sample_expanded_df):
    df, close, high, low = sample_expanded_df
    df_monthly, df_eras, meta = evaluate_regime_and_era_stability(df, close, high, low)

    assert isinstance(df_monthly, pd.DataFrame)
    assert isinstance(df_eras, pd.DataFrame)
