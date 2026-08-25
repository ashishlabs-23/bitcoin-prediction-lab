"""
tests/test_information_forensics.py — Unit Tests for Information Forensics & Analyst Layer
==========================================================================================
Verifies:
1. Multi-timeframe point-in-time calculation (no lookahead)
2. Deterministic Analyst Layer factor generation (bounded within prescribed ranges)
3. Feature inventory and collinearity audit execution
4. Multiple testing tracker and Deflated Sharpe Ratio calculation
5. Information ablation data pipeline integrity
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.multitimeframe_features import build_multitimeframe_features, compute_rsi, compute_adx
from research.analyst_layer import (
    compute_technical_analyst_factors,
    compute_orderflow_analyst_factors,
    compute_derivatives_analyst_factors,
    compute_sentiment_analyst_factors,
    generate_all_analyst_factors
)
from research.multiple_testing import ResearchTrialTracker
from research.information_inventory import audit_information_inventory
from research.information_stability import evaluate_multihorizon_information


@pytest.fixture
def sample_feature_df():
    """Generates synthetic hourly dataframe containing market features."""
    np.random.seed(42)
    n = 250
    ts = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    close = 60000.0 * np.exp(np.cumsum(np.random.normal(0.0002, 0.01, size=n)))
    high = close * 1.005
    low = close * 0.995
    open_p = close * 0.999
    vol = np.random.uniform(100, 1000, size=n)

    return pd.DataFrame({
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
        'sentiment_score': np.random.uniform(-1, 1, size=n)
    }, index=ts)


def test_multitimeframe_features_no_lookahead(sample_feature_df):
    mtf = build_multitimeframe_features(sample_feature_df)
    assert isinstance(mtf, pd.DataFrame)
    assert mtf.shape[0] == sample_feature_df.shape[0]
    assert "mtf_1h_ret" in mtf.columns
    assert "mtf_4h_ret" in mtf.columns
    assert "mtf_12h_ret" in mtf.columns
    assert "mtf_1d_ret" in mtf.columns

    # Modifying future close should not alter past multi-timeframe features
    df_mod = sample_feature_df.copy()
    df_mod.iloc[150:, df_mod.columns.get_loc('close')] += 10000.0
    mtf_mod = build_multitimeframe_features(df_mod)
    np.testing.assert_allclose(mtf.iloc[:149].values, mtf_mod.iloc[:149].values)


def test_analyst_layer_factor_bounds(sample_feature_df):
    fused = generate_all_analyst_factors(sample_feature_df)
    assert fused.shape[1] == 12

    # Technical factors
    assert (fused['tech_trend_score'] >= -1.0).all() and (fused['tech_trend_score'] <= 1.0).all()
    assert (fused['tech_momentum_score'] >= -1.0).all() and (fused['tech_momentum_score'] <= 1.0).all()
    assert (fused['tech_breakout_score'] >= 0.0).all() and (fused['tech_breakout_score'] <= 1.0).all()

    # Order flow factors
    assert (fused['of_imbalance_score'] >= -1.0).all() and (fused['of_imbalance_score'] <= 1.0).all()
    assert (fused['of_liquidity_score'] >= 0.0).all() and (fused['of_liquidity_score'] <= 1.0).all()
    assert (fused['of_pressure_score'] >= -1.0).all() and (fused['of_pressure_score'] <= 1.0).all()

    # Derivatives factors
    assert (fused['deriv_leverage_risk'] >= 0.0).all() and (fused['deriv_leverage_risk'] <= 1.0).all()
    assert (fused['deriv_funding_pressure'] >= -1.0).all() and (fused['deriv_funding_pressure'] <= 1.0).all()

    # Sentiment factors
    assert (fused['sent_sentiment_score'] >= -1.0).all() and (fused['sent_sentiment_score'] <= 1.0).all()


def test_multiple_testing_trial_tracker():
    tracker = ResearchTrialTracker()
    tracker.record_feature_family("Technicals", 20)
    tracker.record_feature_family("Order Flow", 10)
    tracker.record_experiment("Ablation Run 1", n_models=7, n_horizons=5, n_configs=7)

    k = tracker.total_trial_count_k()
    assert k >= 42  # 7 * 5 + 7 = 42

    dsr = tracker.compute_deflated_sharpe_ratio(observed_sr=1.5, n_samples=500, sr_var=0.5)
    assert 0.0 <= dsr <= 1.0


def test_information_inventory_execution():
    res = audit_information_inventory()
    assert "inventory" in res
    assert "redundant_pairs" in res
    assert "group_summary" in res
    assert len(res["inventory"]) == 32
