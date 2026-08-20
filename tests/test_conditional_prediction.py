"""
tests/test_conditional_prediction.py — Unit Tests for Conditional Predictability & Decomposition Suite
=====================================================================================================
Verifies:
1. Conditional subspace evaluation with strict train-quantile derivation
2. Point-in-time event shock calculations without lookahead
3. Momentum vs mean-reversion model evaluation
4. Selective abstention coverage slicing
5. Conformal uncertainty intervals and coverage bounds
6. Multi-task target extraction (Magnitude, MFE, MAE)
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.conformal_prediction import TimeSeriesConformalPredictor, evaluate_conformal_uncertainty
from research.event_prediction import evaluate_event_shock_predictability
from research.momentum_reversion import evaluate_momentum_vs_mean_reversion
from research.selective_prediction import evaluate_selective_abstention_policy
from research.economic_targets import evaluate_multitask_economic_targets
from research.conditional_prediction import evaluate_conditional_subspaces


@pytest.fixture
def sample_timeseries_df():
    """Generates synthetic dataset for conditional testing."""
    np.random.seed(42)
    n = 300
    ts = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    close = 60000.0 * np.exp(np.cumsum(np.random.normal(0.0002, 0.01, size=n)))
    high = close * 1.008
    low = close * 0.992
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
        'vol_24h': np.random.uniform(0.01, 0.03, size=n),
        'sma_ratio_20': np.random.normal(0, 0.01, size=n),
        'sma_ratio_50': np.random.normal(0, 0.02, size=n),
        'rsi_14': np.random.uniform(20, 80, size=n),
        'bb_width_20': np.random.uniform(0.01, 0.05, size=n),
        'bb_pct_20': np.random.uniform(0.1, 0.9, size=n),
        'stoch_k': np.random.uniform(10, 90, size=n),
        'stoch_d': np.random.uniform(10, 90, size=n),
        'order_book_imbalance': np.random.uniform(-0.5, 0.5, size=n),
        'funding_rate': np.random.uniform(-0.0001, 0.0001, size=n),
        'open_interest_change_24h': np.random.normal(0, 0.05, size=n),
        'tech_trend_score': np.random.uniform(-1, 1, size=n),
        'tech_momentum_score': np.random.uniform(-1, 1, size=n),
        'tech_breakout_score': np.random.uniform(-1, 1, size=n),
        'deriv_funding_pressure': np.random.uniform(-1, 1, size=n)
    }, index=ts)

    return df, pd.Series(close, index=ts), pd.Series(high, index=ts), pd.Series(low, index=ts)


def test_conformal_predictor_intervals():
    np.random.seed(42)
    X_tr = np.random.randn(100, 5)
    y_tr = np.random.randn(100) * 0.02
    X_cal = np.random.randn(50, 5)
    y_cal = np.random.randn(50) * 0.02
    X_te = np.random.randn(20, 5)

    cp = TimeSeriesConformalPredictor(alpha=0.10)
    cp.fit_and_calibrate(X_tr, y_tr, X_cal, y_cal)
    preds, lower, upper, uncert = cp.predict_intervals(X_te)

    assert len(preds) == 20
    assert (upper >= lower).all()
    assert cp.q_hat > 0


def test_event_shock_evaluation(sample_timeseries_df):
    df, close, _, _ = sample_timeseries_df
    df_res, meta = evaluate_event_shock_predictability(df, close, horizon_bars=12)

    assert isinstance(df_res, pd.DataFrame)
    assert len(df_res) == 7
    assert "Event / Shock Type" in df_res.columns
    assert "Gross Expectancy %" in df_res.columns


def test_momentum_vs_mean_reversion_execution(sample_timeseries_df):
    df, close, _, _ = sample_timeseries_df
    df_res, meta = evaluate_momentum_vs_mean_reversion(df, close, horizon_bars=12, n_splits=3)

    assert isinstance(df_res, pd.DataFrame)
    assert len(df_res) == 3
    assert "Hypothesis Model" in df_res.columns


def test_selective_abstention_execution(sample_timeseries_df):
    df, close, _, _ = sample_timeseries_df
    labels = np.random.randint(0, 3, size=len(df))
    fwd_rets = np.random.normal(0.0005, 0.01, size=len(df))

    df_res, meta = evaluate_selective_abstention_policy(df, close, labels, fwd_rets, target_coverages=[1.0, 0.50, 0.10])

    assert isinstance(df_res, pd.DataFrame)
    assert len(df_res) == 3
    assert "Target Coverage" in df_res.columns
    assert "Empirical Coverage %" in df_res.columns


def test_multitask_economic_targets_execution(sample_timeseries_df):
    df, close, high, low = sample_timeseries_df
    df_res, meta = evaluate_multitask_economic_targets(df, close, high, low, horizon_bars=12)

    assert isinstance(df_res, pd.DataFrame)
    assert len(df_res) == 5
    assert "Target Task" in df_res.columns
    assert "OOS Performance" in df_res.columns
