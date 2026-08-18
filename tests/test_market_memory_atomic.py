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
    assert latest.get("data_source") == "live_terminal"


def test_storage_separation_and_synthetic_isolation(tmp_path, monkeypatch):
    """Verify that synthetic stress trials are written to stress_trials.csv and never touch market_memory.csv."""
    from backtest.market_memory import record_stress_trial, load_stress_trials, sanitize_market_memory
    
    test_mem_csv = str(tmp_path / "market_memory.csv")
    test_stress_csv = str(tmp_path / "stress_trials.csv")
    
    monkeypatch.setattr("backtest.market_memory.get_memory_file", lambda: test_mem_csv)
    monkeypatch.setattr("backtest.market_memory.get_stress_trials_file", lambda: test_stress_csv)

    # 1. Record authentic prediction
    record_prediction(
        timestamp="2026-08-18 10:00:00 UTC",
        price=65000.0,
        regime="TRENDING_BULL",
        raw_prob=0.75,
        calibrated_prob=0.78,
        decision="TAKE_LONG",
        direction="LONG"
    )

    # 2. Record synthetic stress trial
    record_stress_trial(
        trial_id="stress_101",
        timestamp="2026-08-18 10:05:00 UTC",
        price=63000.0,
        direction="SHORT",
        decision="TAKE_SHORT",
        probability=0.82,
        tp=61000.0,
        sl=64500.0,
        macro_shock="CAPITULATION",
        volatility_mult=2.5,
        liquidity_shock_pct=-30.0,
        hypothetical_return=-0.015,
        was_correct=True,
        pnl_bps=150.0,
        data_source="synthetic_arena"
    )

    # Verify market_memory.csv contains only 1 authentic record
    mem_df = load_market_memory()
    assert len(mem_df) == 1
    assert mem_df.iloc[0]["data_source"] == "live_terminal"
    assert mem_df.iloc[0]["price"] == 65000.0

    # Verify stress_trials.csv contains the synthetic record
    stress_df = load_stress_trials()
    assert len(stress_df) == 1
    assert stress_df.iloc[0]["data_source"] == "synthetic_arena"
    assert stress_df.iloc[0]["macro_shock"] == "CAPITULATION"

    # 3. Test sanitization: inject an accidental synthetic row into market_memory.csv and verify sanitize removes it
    df = pd.read_csv(test_mem_csv)
    bad_row = df.iloc[0].copy()
    bad_row["regime"] = "SIM_ARENA_CAPITULATION"
    bad_row["data_source"] = "synthetic_arena"
    df = pd.concat([df, pd.DataFrame([bad_row])], ignore_index=True)
    df.to_csv(test_mem_csv, index=False)

    assert len(pd.read_csv(test_mem_csv)) == 2
    purged = sanitize_market_memory()
    assert purged == 1
    clean_df = load_market_memory()
    assert len(clean_df) == 1
    assert clean_df.iloc[0]["data_source"] == "live_terminal"

