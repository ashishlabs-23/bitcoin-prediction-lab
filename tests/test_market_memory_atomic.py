"""
Unit tests for atomic Market Memory writes and prediction versioning in backtest/market_memory.py.
"""

import sys
import os
import pytest
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backtest.market_memory import record_prediction, load_market_memory


def test_market_memory_versioning_and_atomic_writes(tmp_path, monkeypatch):
    """Verify that predictions are recorded with version metadata and read cleanly."""
    test_csv = str(tmp_path / "test_market_memory.csv")
    monkeypatch.setattr("backtest.market_memory.get_memory_file", lambda: test_csv)
    
    ts_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    df = record_prediction(
        timestamp=ts_now,
        price=64000.0,
        regime="TRENDING_BULL",
        raw_prob=0.70,
        calibrated_prob=0.74,
        decision="TAKE_LONG",
        direction="LONG",
        tp=64960.0,
        sl=63360.0,
        model_version="xgb_v2.1",
        feature_version="features_v3",
        regime_version="regime_v1"
    )

    loaded_df = load_market_memory()
    assert not loaded_df.empty
    latest = loaded_df.iloc[-1]

    assert "prediction_id" in loaded_df.columns
    assert "model_version" in loaded_df.columns
    assert "feature_version" in loaded_df.columns
    assert "regime_version" in loaded_df.columns
    assert "candle_time" in loaded_df.columns

    assert latest["model_version"] == "xgb_v2.1"
    assert latest["feature_version"] == "features_v3"
    assert latest["regime_version"] == "regime_v1"
