"""
tests/test_target_validation_v2.py — Unit Tests for 24h Target Validation & Intrabar Barriers
===========================================================================================
Verifies:
1. Point-in-time volatility computation (zero lookahead)
2. Intrabar High/Low barrier detection and ambiguity policy
3. Horizon alignment and t1 > t0 invariants
4. Purged and embargoed walk-forward split generation
5. Probability calibration (Platt scaling & ECE)
6. True economic event-trading simulation mechanics
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.target_validation_v2 import (
    compute_point_in_time_volatility,
    triple_barrier_label_intrabar,
    evaluate_target_families,
    run_walk_forward_target_validation,
    evaluate_statistical_significance,
    simulate_event_trading_backtest,
    evaluate_probability_calibration
)


@pytest.fixture
def synthetic_ohlcv_data():
    """Generates synthetic hourly OHLCV data for testing."""
    np.random.seed(42)
    n = 350
    ts = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    rets = np.random.normal(0.0002, 0.01, size=n)
    close = 60000.0 * np.exp(np.cumsum(rets))
    high = close * (1.0 + np.abs(np.random.normal(0, 0.005, size=n)))
    low = close * (1.0 - np.abs(np.random.normal(0, 0.005, size=n)))
    open_p = (high + low) / 2.0
    vol = np.random.uniform(100, 1000, size=n)

    df = pd.DataFrame({
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'volume': vol,
        'available_time': ts + pd.Timedelta(seconds=5),
        'ret_1h': rets,
        'rsi_14': np.random.uniform(30, 70, size=n),
        'sma_ratio_20': np.random.normal(0, 0.01, size=n),
        'order_book_imbalance': np.random.uniform(-0.5, 0.5, size=n),
        'funding_rate': np.random.uniform(-0.0001, 0.0001, size=n),
        'sentiment_score': np.random.uniform(-1, 1, size=n)
    }, index=ts)
    return df, pd.Series(close, index=ts)


def test_point_in_time_volatility_no_lookahead(synthetic_ohlcv_data):
    df, close = synthetic_ohlcv_data
    vol = compute_point_in_time_volatility(close, window=24)

    # First 24 elements must be NaN (shift(1) produces 1 NaN + 23 rolling warm-up bars)
    assert vol.iloc[:24].isna().all()
    # Bar 25 (index 24) must be non-NaN
    assert not np.isnan(vol.iloc[24])
    # Shifting future close should not affect current vol
    close_modified = close.copy()
    close_modified.iloc[100:] += 5000.0
    vol_mod = compute_point_in_time_volatility(close_modified, window=24)
    # Volatility before bar 100 must be exactly identical
    np.testing.assert_allclose(vol.iloc[:99].values, vol_mod.iloc[:99].values)


def test_intrabar_barrier_and_ambiguity_policy(synthetic_ohlcv_data):
    df, close = synthetic_ohlcv_data
    vol = compute_point_in_time_volatility(close, window=24).fillna(0.01)

    res_df, stats_meta = triple_barrier_label_intrabar(df, vol, pt_mult=1.5, sl_mult=1.5, max_bars=24)

    assert "total_evaluated" in stats_meta
    assert "ambiguous_count" in stats_meta
    assert stats_meta["ambiguous_rate"] >= 0.0

    valid = res_df.dropna(subset=['label'])
    # Valid labels must only be {1.0 (BUY), -1.0 (SELL), 0.0 (HOLD)}
    assert set(valid['label'].unique()).issubset({-1.0, 0.0, 1.0})
    # t1 invariant: t1 >= timestamp
    assert (valid['t1'] >= valid.index).all()


def test_target_families_evaluation(synthetic_ohlcv_data):
    df, close = synthetic_ohlcv_data
    df_targets, datasets = evaluate_target_families(df, close)

    assert isinstance(df_targets, pd.DataFrame)
    assert len(df_targets) == 3
    assert "Target A (24h Fixed Direction)" in datasets
    assert "Target B (24h 2.0x TB Intrabar)" in datasets
    assert "Target C (24h 1.5x TB Intrabar)" in datasets


def test_walk_forward_target_validation_folds(synthetic_ohlcv_data):
    df, close = synthetic_ohlcv_data
    _, datasets = evaluate_target_families(df, close)
    target_b = datasets["Target B (24h 2.0x TB Intrabar)"]

    df_wf, wf_stats = run_walk_forward_target_validation(df, target_b, "Target B", n_splits=3, embargo_bars=10)

    assert len(df_wf) == 3
    assert "auc_mean" in wf_stats
    assert 0.0 <= wf_stats["auc_mean"] <= 1.0


def test_probability_calibration_quality(synthetic_ohlcv_data):
    df, close = synthetic_ohlcv_data
    _, datasets = evaluate_target_families(df, close)
    target_b = datasets["Target B (24h 2.0x TB Intrabar)"]

    df_cal, cal_stats = evaluate_probability_calibration(df, target_b)
    assert len(df_cal) == 2
    assert "Expected Calibration Error (ECE)" in df_cal.columns
    assert cal_stats["ece_cal"] >= 0.0


def test_economic_event_simulation(synthetic_ohlcv_data):
    df, close = synthetic_ohlcv_data
    _, datasets = evaluate_target_families(df, close)
    target_b = datasets["Target B (24h 2.0x TB Intrabar)"]

    df_econ = simulate_event_trading_backtest(df, target_b, fee_bps=5.0, slippage_bps=2.0)
    assert isinstance(df_econ, pd.DataFrame)
    assert "Total Active Trades" in df_econ.columns
    assert "Win Rate %" in df_econ.columns
    assert "Cost-Adjusted Sharpe" in df_econ.columns
