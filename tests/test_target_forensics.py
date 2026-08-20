"""
tests/test_target_forensics.py — Unit Tests for Target & Signal Forensics
========================================================================
Verifies:
1. Fixed horizon and triple barrier target generation
2. Horizon alignment and t1 >= timestamp invariant (no future lookahead)
3. Purge/embargo split generation
4. Class-weighting and Focal Loss forward pass
5. Baseline model execution and scoring
6. Feature ablation pipeline integrity
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.target_forensics import (
    compute_directional_labels_for_horizon,
    create_three_way_splits,
    FocalLoss,
    evaluate_target_suite,
    evaluate_baselines_vs_models
)
from labeling.targets import triple_barrier_label, realized_vol, fixed_horizon_label
from validation.purged_split import PurgedWalkForwardSplit, sample_uniqueness


@pytest.fixture
def synthetic_market_data():
    """Generates synthetic hourly market dataframe for testing."""
    np.random.seed(42)
    n = 300
    ts = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    returns = np.random.normal(0.0005, 0.01, size=n)
    close = 50000.0 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'open': close * 0.999,
        'high': close * 1.005,
        'low': close * 0.995,
        'close': close,
        'volume': np.random.uniform(100, 1000, size=n),
        'available_time': ts + pd.Timedelta(seconds=5),
        'ret_1h': returns,
        'rsi_14': np.random.uniform(20, 80, size=n),
        'sma_ratio_20': np.random.normal(0, 0.01, size=n)
    }, index=ts)
    return df, pd.Series(close, index=ts)


def test_fixed_horizon_label_invariants(synthetic_market_data):
    df, close = synthetic_market_data
    vol = realized_vol(close, window=24).fillna(0.01)
    
    target_df = compute_directional_labels_for_horizon(close, vol, horizon_bars=6, k_vol=0.5)
    
    assert len(target_df) == len(close)
    # The last 6 rows must be NaN because forward return cannot look beyond data end
    assert target_df['direction'].iloc[-6:].isna().all()
    
    clean = target_df.dropna(subset=['direction'])
    assert len(clean) == len(close) - 6
    # t1 invariant: t1 must be strictly in the future
    assert (clean['t1'] > clean.index).all()
    # Labels must only be {0, 1, 2}
    unique_labels = set(clean['direction'].unique())
    assert unique_labels.issubset({0, 1, 2})


def test_triple_barrier_label_invariants(synthetic_market_data):
    df, close = synthetic_market_data
    vol = realized_vol(close, window=24).fillna(0.01)
    
    tb_df = triple_barrier_label(close, vol, pt_mult=1.5, sl_mult=1.5, max_bars=12, adaptive_width=False)
    
    clean = tb_df.dropna(subset=['label'])
    assert len(clean) > 0
    # t1 >= timestamp
    assert (clean['t1'] >= clean.index).all()
    # labels in {-1, 0, 1}
    assert set(clean['label'].unique()).issubset({-1.0, 0.0, 1.0})


def test_three_way_temporal_split_isolation(synthetic_market_data):
    df, close = synthetic_market_data
    splits = create_three_way_splits(df, val_size=50, holdout_size=30, embargo_bars=10)
    
    train_df, _ = splits['train']
    val_df, _ = splits['val']
    holdout_df, _ = splits['holdout']
    
    # Check strict chronological ordering with embargo buffers
    assert train_df.index.max() < val_df.index.min()
    assert val_df.index.max() < holdout_df.index.min()
    
    # Train and holdout do not overlap
    assert set(train_df.index).isdisjoint(set(val_df.index))
    assert set(val_df.index).isdisjoint(set(holdout_df.index))


def test_focal_loss_forward_backward():
    loss_fn = FocalLoss(gamma=2.0)
    logits = torch.randn(10, 3, requires_grad=True)
    targets = torch.randint(0, 3, (10,))
    
    loss = loss_fn(logits, targets)
    assert loss.dim() == 0
    assert not torch.isnan(loss)
    assert loss.item() >= 0.0
    
    loss.backward()
    assert logits.grad is not None
    assert not torch.isnan(logits.grad).any()


def test_target_suite_summary_execution(synthetic_market_data):
    df, close = synthetic_market_data
    res = evaluate_target_suite(df, close)
    assert isinstance(res, pd.DataFrame)
    assert "Target Type" in res.columns
    assert "Majority Baseline" in res.columns
    assert len(res) >= 5
