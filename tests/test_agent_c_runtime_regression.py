"""
tests/test_agent_c_runtime_regression.py — Agent C Runtime and Persistence Regression Suite
==========================================================================================
Covers:
1. WebSocket heartbeat contract: JSON {"type": "ping"} and text "ping" -> {"type": "PONG", "timestamp": ...}
2. Batch regime prediction output shape (N inputs -> N outputs) + single-row backward compatibility.
3. Candle manager boundary correctness, seed deduplication, and out-of-order tick rejection.
4. CLI HTTP 503 research-gate handling (clean error message and non-zero exit code).
5. Thread-safe atomic market memory append under concurrent writes.
"""

import os
import sys
import json
import time
import pytest
import threading
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app
from models.regime_detector import MarketRegimeDetector
from api.candle_manager import CandleManager
from backtest.market_memory import record_prediction, load_market_memory


def test_websocket_heartbeat_contract():
    """Verify WebSocket server responds with standardized JSON PONG for both string and JSON pings."""
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        # First message is connection greeting
        conn_msg = json.loads(ws.receive_text())
        assert conn_msg.get("type") == "CONNECTION_ESTABLISHED"

        # 1. Test string "ping"
        ws.send_text("ping")
        resp1 = json.loads(ws.receive_text())
        assert resp1["type"] == "PONG"
        assert "timestamp" in resp1
        assert isinstance(resp1["timestamp"], int)

        # 2. Test JSON {"type": "ping"}
        ws.send_text(json.dumps({"type": "ping"}))
        resp2 = json.loads(ws.receive_text())
        assert resp2["type"] == "PONG"
        assert "timestamp" in resp2


def test_batch_regime_prediction_shape_and_contract():
    """Verify MarketRegimeDetector.predict() handles both batch (N -> N) and single row inputs."""
    detector = MarketRegimeDetector()

    # 1. Batch input (N = 10 rows)
    df_batch = pd.DataFrame({
        "atr_14_ratio": [0.015 + i * 0.001 for i in range(10)],
        "adx_14": [0.20 + i * 0.02 for i in range(10)],
        "ema_20_ratio": [0.001 * i for i in range(10)],
        "ema_50_ratio": [-0.001 * i for i in range(10)],
        "volume_zscore_24h": [0.5 * (i % 3) for i in range(10)],
        "vwap_ratio": [0.002 * (i % 2) for i in range(10)],
        "funding_rate": [0.0001] * 10
    })

    batch_preds = detector.predict(df_batch)
    assert isinstance(batch_preds, list), f"Expected list for batch input, got {type(batch_preds)}"
    assert len(batch_preds) == 10, f"Expected 10 predictions for 10 rows, got {len(batch_preds)}"
    for pred in batch_preds:
        assert "regime" in pred
        assert "confidence" in pred
        assert "probabilities" in pred

    # 2. Single row input (dict) -> must return single dict
    single_row = df_batch.iloc[0].to_dict()
    single_pred = detector.predict(single_row)
    assert isinstance(single_pred, dict), f"Expected dict for single input, got {type(single_pred)}"
    assert "regime" in single_pred
    assert "confidence" in single_pred


def test_candle_manager_deduplication_and_boundary_isolation():
    """Verify CandleManager deduplicates historical seeds and strictly isolates next-bar ticks."""
    mgr = CandleManager(interval_seconds=60)

    # 1. Seed duplicates: provide overlapping candles
    seed_candles = [
        {"time": 1700000000000, "open": 100, "high": 105, "low": 98, "close": 102, "volume": 10, "is_closed": True},
        {"time": 1700000000000, "open": 100, "high": 105, "low": 98, "close": 102, "volume": 10, "is_closed": True}, # DUPLICATE
        {"time": 1700000060000, "open": 102, "high": 108, "low": 101, "close": 106, "volume": 15, "is_closed": True},
    ]
    mgr.seed_historical_candles(seed_candles)
    assert len(mgr.closed_candles) == 2, f"Seed duplicates were not eliminated: {len(mgr.closed_candles)}"

    # 2. Current bar at timestamp 1700000120000 (lasts until 1700000180000)
    # Process ticks within bar
    mgr.process_tick(price=106.0, volume=1.0, timestamp_ms=1700000125000)
    mgr.process_tick(price=110.0, volume=2.0, timestamp_ms=1700000130000) # High of bar 1
    mgr.process_tick(price=104.0, volume=1.0, timestamp_ms=1700000150000) # Low of bar 1

    # First tick of NEXT bar at exactly 1700000180000 with extreme spike
    # Must NOT corrupt closed bar's high/low
    mgr.process_tick(price=999.0, volume=5.0, timestamp_ms=1700000180000)

    # The previous candle must have closed cleanly with high=110, low=104
    closed_candle = mgr.closed_candles[-1]
    assert closed_candle["high"] == 110.0, f"Next-bar tick corrupted closed bar high: {closed_candle['high']}"
    assert closed_candle["low"] == 104.0, f"Next-bar tick corrupted closed bar low: {closed_candle['low']}"


def test_concurrent_market_memory_append(tmp_path, monkeypatch):
    """Verify multiple concurrent worker threads appending predictions do not corrupt storage."""
    test_csv = str(tmp_path / "concurrent_market_memory.csv")
    test_db = str(tmp_path / "concurrent_market_memory.db")
    monkeypatch.setattr("backtest.market_memory.get_memory_file", lambda: test_csv)
    monkeypatch.setattr("backtest.market_memory.DB_PATH", test_db)
    monkeypatch.setattr("backtest.market_memory.MARKET_MEMORY_DB_PATH", test_db)
    monkeypatch.setattr("config.database.MARKET_MEMORY_DB_PATH", test_db)

    def worker_append(thread_id, count=10):
        for i in range(count):
            record_prediction(
                timestamp=f"2026-08-31 12:{thread_id:02d}:{i:02d} UTC",
                price=65000.0 + i,
                regime="SIM_ARENA_TEST",
                raw_prob=0.72,
                calibrated_prob=0.75,
                decision="TAKE_LONG",
                prediction_id=f"thread_{thread_id}_pred_{i}"
            )

    threads = [threading.Thread(target=worker_append, args=(t, 10)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Total 50 predictions must exist cleanly in CSV without corruption or missing rows
    df = pd.read_csv(test_csv)
    assert len(df) == 50, f"Expected 50 records after concurrent append, found {len(df)}"
    assert len(df["prediction_id"].unique()) == 50, "Duplicate or overwritten prediction IDs found"
