"""
Unit tests for Replay Engine snapshot generation.
"""

import sys
import os
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backtest.market_memory import record_prediction, load_market_memory


def test_replay_mode_data_reconstruction(tmp_path, monkeypatch):
    """Verify that recorded Market Memory entries contain fields required by Replay Engine."""
    test_csv = str(tmp_path / "test_market_memory.csv")
    monkeypatch.setattr("backtest.market_memory.get_memory_file", lambda: test_csv)

    ts_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    record_prediction(
        timestamp=ts_now,
        price=64000.0,
        regime="TRENDING_BULL",
        raw_prob=0.68,
        calibrated_prob=0.71,
        decision="TAKE_LONG",
        direction="LONG",
        tp=64960.0,
        sl=63360.0,
        model_version="xgb_v2.1",
        feature_version="features_v3",
        regime_version="regime_v1"
    )

    mem_df = load_market_memory()
    assert not mem_df.empty
    latest = mem_df.iloc[-1]

    assert latest["price"] == 64000.0
    assert latest["direction"] == "LONG"
    assert latest["model_version"] == "xgb_v2.1"
