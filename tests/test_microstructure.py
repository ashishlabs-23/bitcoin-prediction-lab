"""
Unit tests for data/ingest_microstructure.py module.
"""

import pytest
import pandas as pd
import numpy as np
from data.ingest_microstructure import compute_microstructure_features


def test_microstructure_features_empty_df():
    empty_ohlcv = pd.DataFrame()
    res = compute_microstructure_features(empty_ohlcv)
    assert res.empty
    expected_cols = ['timestamp', 'available_time', 'order_book_imbalance', 'bid_ask_spread_pct', 'taker_buy_ratio', 'vpin']
    assert list(res.columns) == expected_cols


def test_microstructure_features_synthetic_data():
    dates = pd.date_range("2026-01-01", periods=50, freq="1h", tz="UTC")
    synthetic_ohlcv = pd.DataFrame({
        'timestamp': dates,
        'open': 50000 + np.random.randn(50) * 100,
        'high': 50200 + np.abs(np.random.randn(50) * 100),
        'low': 49800 - np.abs(np.random.randn(50) * 100),
        'close': 50050 + np.random.randn(50) * 100,
        'volume': 100.0 + np.abs(np.random.randn(50) * 10),
        'available_time': dates + pd.Timedelta(hours=1)
    })

    res = compute_microstructure_features(synthetic_ohlcv)
    assert len(res) == len(synthetic_ohlcv)
    assert 'order_book_imbalance' in res.columns
    assert 'bid_ask_spread_pct' in res.columns
    assert 'taker_buy_ratio' in res.columns
    assert 'vpin' in res.columns

    # Verify range bounds
    assert (res['bid_ask_spread_pct'] >= 0.0).all()
    assert (res['taker_buy_ratio'] >= 0.0).all() and (res['taker_buy_ratio'] <= 1.0).all()
    assert (res['order_book_imbalance'] >= -1.0).all() and (res['order_book_imbalance'] <= 1.0).all()
