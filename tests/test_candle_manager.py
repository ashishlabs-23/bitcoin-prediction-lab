"""
Unit tests for CandleStateManager in api/candle_manager.py.
"""

import sys
import os
import pytest
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.candle_manager import CandleStateManager


def test_candle_state_manager_forming_vs_closed():
    """Verify that ticks update forming candle, and predictions run ONLY on closed candles."""
    manager = CandleStateManager(interval_seconds=60)

    start_ms = 1786636800000  # Even 1-minute boundary
    
    # First tick at start_ms
    tick1, pred1 = manager.process_tick(price=118000.0, volume=1.0, timestamp_ms=start_ms)
    assert tick1["type"] == "tick"
    assert tick1["price"] == 118000.0
    assert pred1 is None  # Forming candle: NO prediction generated

    # Second tick 30 seconds later (in same candle)
    tick2, pred2 = manager.process_tick(price=118500.0, volume=2.0, timestamp_ms=start_ms + 30000)
    assert tick2["high"] == 118500.0
    assert tick2["low"] == 118000.0
    assert pred2 is None  # Still forming candle: NO prediction generated

    # Third tick 61 seconds later (candle interval HAS CLOSED!)
    tick3, pred3 = manager.process_tick(price=118200.0, volume=0.5, timestamp_ms=start_ms + 61000)
    assert pred3 is not None  # Candle CLOSED: prediction WAS generated!
    assert pred3["type"] == "prediction"
    assert pred3["price"] == 118500.0  # Close price of closed candle
    assert "prediction_id" in pred3
    assert "model_version" in pred3
    assert "feature_version" in pred3
    assert "regime_version" in pred3
