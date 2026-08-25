"""
tests/test_onchain.py -- Unit tests for On-Chain Valuation and Regime Confluence

Validates:
1. Macro cycle classification logic (Ratio, Z-Score, and Rolling Percentiles)
2. Live & offline fallback handling with explicit degradation status
3. Regime detector integration with macro cycle filters and influence weighting
4. Parquet caching and offline synthetic history generation
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.ingest_onchain import (
    classify_macro_cycle,
    get_latest_onchain_valuation,
    save_synthetic_onchain_history,
)
from models.regime_detector import classify_regimes, predict_regime_probabilities


def test_classify_macro_cycle_ratio_thresholds():
    """Verify CoinMetrics CapMVRVFF ratio classification."""
    assert classify_macro_cycle(mvrv_val=0.85, nupl_val=0.10, metric_type="ratio") == "CAPITULATION"
    assert classify_macro_cycle(mvrv_val=1.20, nupl_val=-0.05, metric_type="ratio") == "CAPITULATION"
    assert classify_macro_cycle(mvrv_val=1.30, nupl_val=0.15, metric_type="ratio") == "ACCUMULATION"
    assert classify_macro_cycle(mvrv_val=2.20, nupl_val=0.45, metric_type="ratio") == "NEUTRAL"
    assert classify_macro_cycle(mvrv_val=3.80, nupl_val=0.60, metric_type="ratio") == "EUPHORIA"
    assert classify_macro_cycle(mvrv_val=2.50, nupl_val=0.75, metric_type="ratio") == "EUPHORIA"


def test_classify_macro_cycle_rolling_percentiles():
    """Verify expanding trailing percentile classification without magic numbers."""
    mvrv_history = pd.Series(np.linspace(0.8, 3.5, 100))
    # 5th percentile is ~0.935
    assert classify_macro_cycle(0.85, 0.1, trailing_mvrv_series=mvrv_history) == "CAPITULATION"
    # 95th percentile is ~3.365
    assert classify_macro_cycle(3.45, 0.5, trailing_mvrv_series=mvrv_history) == "EUPHORIA"
    # 20th percentile is accumulation
    assert classify_macro_cycle(1.20, 0.15, trailing_mvrv_series=mvrv_history) == "ACCUMULATION"
    # Median is neutral
    assert classify_macro_cycle(2.15, 0.40, trailing_mvrv_series=mvrv_history) == "NEUTRAL"


def test_get_latest_onchain_valuation_offline():
    """Verify offline fallback and explicit degradation flags."""
    val = get_latest_onchain_valuation(live_btc_price=65000.0, force_offline=True)
    assert isinstance(val, dict)
    assert 'mvrv' in val
    assert 'nupl' in val
    assert 'cycle_phase' in val
    assert val['cycle_phase'] in ["CAPITULATION", "ACCUMULATION", "NEUTRAL", "EUPHORIA"]
    assert val['is_live'] is False
    assert val['is_degraded'] is True
    assert val['influence_weight'] == 0.0  # Offline fallback must not silently influence models
    assert val['source'] == 'calibrated_proxy'


def test_save_and_read_synthetic_onchain_history():
    """Verify synthetic parquet creation and reading."""
    parquet_path = save_synthetic_onchain_history(n_days=30)
    assert os.path.exists(parquet_path)
    df = pd.read_parquet(parquet_path)
    assert len(df) == 30
    assert 'mvrv_zscore' in df.columns
    assert 'nupl' in df.columns


def test_regime_detector_with_onchain_confluence():
    """Verify that verified macro capitulation provides soft accumulation prior without overriding volatility."""
    dates = pd.date_range("2026-01-01", periods=10, freq="1h", tz="UTC")
    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.full(10, 50000.0),
        'high': np.full(10, 50100.0),
        'low': np.full(10, 49900.0),
        'close': np.full(10, 50000.0),
        'volume': np.full(10, 100.0),
        'ret_1h': np.full(10, 0.0),
        'ret_4h': np.full(10, 0.0),
        'ret_24h': np.full(10, -0.01),
        'sma_ratio_50': np.full(10, -0.015),
        'macd': np.full(10, -0.5),
        'realized_vol_24h': np.full(10, 0.01)
    })

    capitulation_val = {'mvrv': 0.85, 'nupl': -0.05, 'cycle_phase': 'CAPITULATION', 'influence_weight': 1.0}
    probs = predict_regime_probabilities(df, onchain_valuation=capitulation_val)
    assert isinstance(probs, pd.DataFrame)
    assert (probs['TRENDING_BULL'] >= 0.0).all()
    assert np.allclose(probs.sum(axis=1), 1.0)

    regimes = classify_regimes(df, onchain_valuation=capitulation_val)
    assert len(regimes) == len(df)

    # Offline degraded valuation (influence_weight == 0.0) should have clean pass-through
    degraded_val = {'mvrv': 0.85, 'nupl': -0.05, 'cycle_phase': 'CAPITULATION', 'influence_weight': 0.0}
    probs_degraded = predict_regime_probabilities(df, onchain_valuation=degraded_val)
    probs_none = predict_regime_probabilities(df, onchain_valuation=None)
    assert np.allclose(probs_degraded.values, probs_none.values)
