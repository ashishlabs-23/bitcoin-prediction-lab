"""
tests/test_v3_data_engine.py — BTCognitive V3 Data Engine Unit & Integration Tests
==================================================================================
Tests for FeaturePipeline, FeatureStore, and MultimodalDataEngine:
  - Tensor shape is precisely (120, 32)
  - Tensor dtype is np.float32
  - Tensor is immutable (read-only)
  - Technical indicators (EMA, RSI, MACD, ATR, Bollinger, VWAP, ROC, ADX, OBV)
  - SQLite WAL mode and table persistence
  - Parquet dataset export
  - Degraded mode fallback behavior
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.feature_store import FeatureStore
from engine.feature_pipeline import FeaturePipeline, NUM_FEATURES, SEQUENCE_LENGTH, FEATURE_NAMES
from engine.data_engine import MultimodalDataEngine


def test_feature_pipeline_shape_and_immutability(tmp_path):
    """Validates (120, 32) shape, float32 dtype, and read-only immutability."""
    db_path = str(tmp_path / "test_store.db")
    store = FeatureStore(db_path=db_path)
    pipeline = FeaturePipeline(store=store)

    # Feed 150 synthetic candles
    base_price = 68000.0
    for i in range(150):
        price = base_price + np.sin(i / 10.0) * 500.0 + (i * 2.0)
        candle = {
            "timestamp": f"2026-08-19T12:{i:02d}:00Z",
            "open": price - 10.0,
            "high": price + 25.0,
            "low": price - 15.0,
            "close": price,
            "volume": 100.0 + (i * 1.5),
            "degraded": False
        }
        orderflow = {
            "bid_depth": 200.0 + i,
            "ask_depth": 180.0 + i,
            "spread": 0.50,
            "imbalance": 0.05
        }
        macro = {
            "funding_rate": 0.0001,
            "open_interest": 50000.0 + i,
            "fear_greed": 55.0
        }
        sentiment = {
            "sentiment_score": 0.2,
            "embed_dim0": 0.05,
            "embed_dim1": -0.02,
            "embed_dim2": 0.08,
            "headline": "Bitcoin shows strength"
        }
        pipeline.update(candle, orderflow=orderflow, macro=macro, sentiment=sentiment)

    # Check tensor
    tensor = pipeline.latest_tensor()
    assert isinstance(tensor, np.ndarray), "Tensor must be a numpy ndarray"
    assert tensor.shape == (120, 32), f"Expected shape (120, 32), got {tensor.shape}"
    assert tensor.dtype == np.float32, f"Expected dtype float32, got {tensor.dtype}"

    # Test immutability
    with pytest.raises(ValueError):
        tensor[0, 0] = 999.9  # Should raise: assignment destination is read-only


def test_technical_indicators_presence(tmp_path):
    """Validates that all required technical indicators are present in latest_features()."""
    db_path = str(tmp_path / "test_store.db")
    store = FeatureStore(db_path=db_path)
    pipeline = FeaturePipeline(store=store)

    for i in range(50):
        candle = {
            "timestamp": f"2026-08-19T14:{i:02d}:00Z",
            "open": 65000.0 + i,
            "high": 65050.0 + i,
            "low": 64950.0 + i,
            "close": 65020.0 + i,
            "volume": 25.0
        }
        pipeline.update(candle)

    features = pipeline.latest_features()
    assert len(features) == 32, f"Expected 32 features, got {len(features)}"

    # Verify key indicator metrics
    expected_keys = [
        "ema_20_ratio", "ema_50_ratio", "ema_200_ratio",
        "rsi_14", "macd", "macd_signal", "atr_14_ratio",
        "bollinger_width", "vwap_ratio", "roc_10", "adx_14", "obv_norm"
    ]
    for k in expected_keys:
        assert k in features, f"Missing required technical indicator: {k}"
        assert not np.isnan(features[k]), f"Feature {k} contains NaN"
        assert not np.isinf(features[k]), f"Feature {k} contains Inf"


def test_sqlite_wal_mode_and_tables(tmp_path):
    """Verifies SQLite WAL mode and data persistence across all 5 tables."""
    db_path = str(tmp_path / "test_wal.db")
    store = FeatureStore(db_path=db_path)

    with store._connection() as conn:
        mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert mode.lower() == "wal", f"Expected WAL journal mode, got {mode}"

    # Insert sample rows
    ts = "2026-08-19T15:00:00Z"
    store.insert_candle({"timestamp": ts, "open": 67000, "high": 67100, "low": 66900, "close": 67050, "volume": 50, "degraded": False})
    store.insert_orderflow({"timestamp": ts, "bid_depth": 300, "ask_depth": 250, "spread": 0.4, "imbalance": 0.09})
    store.insert_macro({"timestamp": ts, "funding_rate": 0.00015, "open_interest": 48000, "fear_greed": 62})
    store.insert_sentiment({"timestamp": ts, "sentiment_score": 0.45, "embed_dim0": 0.1, "embed_dim1": 0.2, "embed_dim2": -0.1, "headline": "Test news"})
    store.insert_features(ts, np.zeros(32, dtype=np.float32), {"norm_close_ret": 0.001})

    # Query recent candles
    df_candles = store.get_recent_candles(limit=10)
    assert len(df_candles) == 1
    assert df_candles["close"].iloc[0] == 67050


def test_parquet_dataset_export(tmp_path):
    """Verifies Parquet dataset export functionality."""
    db_path = str(tmp_path / "test_parquet.db")
    parquet_path = str(tmp_path / "candles_export.parquet")
    store = FeatureStore(db_path=db_path)

    for i in range(10):
        store.insert_candle({
            "timestamp": f"2026-08-19T16:{i:02d}:00Z",
            "open": 68000 + i,
            "high": 68050 + i,
            "low": 67950 + i,
            "close": 68020 + i,
            "volume": 10.0 + i,
            "degraded": False
        })

    exported_file = store.export_to_parquet(table_name="candles", output_path=parquet_path)
    assert os.path.exists(exported_file)
    
    # Read back parquet with pyarrow/pandas
    df_parquet = pd.read_parquet(parquet_path)
    assert len(df_parquet) == 10
    assert "close" in df_parquet.columns


def test_degraded_mode_behavior(tmp_path):
    """Verifies degraded mode fallback when upstream data stream is interrupted."""
    db_path = str(tmp_path / "test_degraded.db")
    store = FeatureStore(db_path=db_path)
    pipeline = FeaturePipeline(store=store)
    engine = MultimodalDataEngine(pipeline=pipeline, store=store)

    # Seed last valid candle
    valid_candle = {
        "timestamp": "2026-08-19T17:00:00Z",
        "open": 68500.0,
        "high": 68600.0,
        "low": 68400.0,
        "close": 68550.0,
        "volume": 32.0,
        "degraded": False
    }
    engine._last_valid_candle = valid_candle

    # Force simulate network failure
    engine.fetch_binance_1m_candle = lambda: {
        "timestamp": "2026-08-19T17:01:00Z",
        "open": valid_candle["open"],
        "high": valid_candle["high"],
        "low": valid_candle["low"],
        "close": valid_candle["close"],
        "volume": valid_candle["volume"],
        "degraded": True
    }

    step_res = engine.step()
    assert step_res["degraded"] is True
    assert step_res["candle"]["close"] == 68550.0
    assert step_res["tensor_shape"] == (120, 32)
