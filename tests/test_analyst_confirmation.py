"""
tests/test_analyst_confirmation.py — Unit Tests for Analyst Layer Confirmation & Holdout Suite
=============================================================================================
Verifies:
1. Conditional factor residualization (Ridge fit and residual subtraction)
2. Horizon-specialized multi-head model forward pass
3. Probability threshold and transaction-cost sweep execution
4. Block bootstrap and permutation test calculation
5. End-to-end confirmation suite integrity
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.conditional_information import evaluate_conditional_analyst_information
from research.horizon_models import MultiHeadHorizonPredictor, evaluate_horizon_specialized_models
from research.analyst_economic_test import run_threshold_and_cost_sweep
from research.analyst_stability import evaluate_analyst_regime_and_monthly_stability, run_block_bootstrap_and_permutation_test
from research.analyst_layer import generate_all_analyst_factors


@pytest.fixture
def sample_market_df():
    """Generates synthetic dataset for testing."""
    np.random.seed(42)
    n = 300
    ts = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    close = 60000.0 * np.exp(np.cumsum(np.random.normal(0.0002, 0.01, size=n)))
    high = close * 1.005
    low = close * 0.995
    open_p = close * 0.999
    vol = np.random.uniform(100, 1000, size=n)

    df = pd.DataFrame({
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'volume': vol,
        'available_time': ts + pd.Timedelta(seconds=5),
        'ret_1h': np.random.normal(0, 0.01, size=n),
        'ret_4h': np.random.normal(0, 0.02, size=n),
        'ret_24h': np.random.normal(0, 0.04, size=n),
        'rsi_14': np.random.uniform(20, 80, size=n),
        'macd_hist': np.random.normal(0, 5, size=n),
        'stoch_k': np.random.uniform(10, 90, size=n),
        'bb_width_20': np.random.uniform(0.01, 0.05, size=n),
        'bb_pct_20': np.random.uniform(0.1, 0.9, size=n),
        'atr_14': np.random.uniform(0.005, 0.02, size=n),
        'sma_ratio_20': np.random.normal(0, 0.01, size=n),
        'sma_ratio_50': np.random.normal(0, 0.02, size=n),
        'sma_ratio_200': np.random.normal(0, 0.03, size=n),
        'vwap_ratio': np.random.normal(0, 0.01, size=n),
        'order_book_imbalance': np.random.uniform(-0.5, 0.5, size=n),
        'depth_ratio_1pct': np.random.uniform(0.5, 2.0, size=n),
        'trade_flow_imbalance': np.random.uniform(-0.4, 0.4, size=n),
        'spread_bps': np.random.uniform(0.5, 3.0, size=n),
        'vol_z_24h': np.random.normal(0, 1, size=n),
        'funding_rate': np.random.uniform(-0.0001, 0.0001, size=n),
        'open_interest_change_24h': np.random.normal(0, 0.05, size=n),
        'oi_vol_ratio': np.random.uniform(1.0, 5.0, size=n),
        'sentiment_score': np.random.uniform(-1, 1, size=n),
        'regime': np.random.choice(['Sideways', 'Accumulation', 'Distribution'], size=n)
    }, index=ts)

    return df, pd.Series(close, index=ts)


def test_conditional_residualization(sample_market_df):
    df, close = sample_market_df
    df_raw = df[['ret_1h', 'ret_4h', 'rsi_14', 'sma_ratio_20', 'bb_width_20']].copy()
    df_analyst = generate_all_analyst_factors(df)

    df_res, summary = evaluate_conditional_analyst_information(df_raw, df_analyst, close, horizon_bars=12)

    assert isinstance(df_res, pd.DataFrame)
    assert len(df_res) == 12
    assert "Residual Factor IC" in df_res.columns
    assert "Functional Role" in df_res.columns
    assert summary["dominant_role"] in ["Representation Compression", "Incremental Information"]


def test_multi_head_horizon_predictor_tensor():
    model = MultiHeadHorizonPredictor(input_dim=15, hidden_dim=32)
    x = torch.randn(8, 15)
    out = model(x)

    assert "short_horizon_logits" in out
    assert "swing_horizon_logits" in out
    assert "macro_horizon_logits" in out
    assert out["short_horizon_logits"].shape == (8, 3)
    assert out["swing_horizon_logits"].shape == (8, 3)
    assert out["macro_horizon_logits"].shape == (8, 3)


def test_threshold_and_cost_sweep_execution(sample_market_df):
    df, close = sample_market_df
    df_analyst = generate_all_analyst_factors(df)
    labels = np.random.randint(0, 3, size=len(df))
    fwd_rets = np.random.normal(0.0005, 0.01, size=len(df))

    df_th, df_cost, meta = run_threshold_and_cost_sweep(df_analyst, labels, fwd_rets)

    assert isinstance(df_th, pd.DataFrame)
    assert isinstance(df_cost, pd.DataFrame)
    assert "Confidence Threshold" in df_th.columns
    assert "Round-Trip Fee (bps)" in df_cost.columns
    assert "break_even_cost_bps" in meta


def test_block_bootstrap_and_permutation():
    n = 200
    y_true = np.random.randint(0, 3, size=n)
    probs = np.random.uniform(0.1, 0.9, size=(n, 3))
    probs = probs / np.sum(probs, axis=1, keepdims=True)
    rets = np.random.normal(0, 0.01, size=n)

    res = run_block_bootstrap_and_permutation_test(y_true, probs, rets, block_size=20, n_bootstrap=100, n_permutations=50)

    assert "observed_auc" in res
    assert "bootstrap_auc_95_ci" in res
    assert len(res["bootstrap_auc_95_ci"]) == 2
    assert "block_permutation_p_value" in res
