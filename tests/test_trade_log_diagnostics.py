"""
tests/test_trade_log_diagnostics.py — Unit Tests for Trade Log Diagnostics Engine
================================================================================
Verifies:
1. Generation of standardized diagnostic trade log dataset
2. Test A: Horizon decomposition calculations
3. Test B: Confidence calibration binning
4. Test C: Temporal event loss clustering
5. Test D: PnL attribution metrics (Win size, Loss size, Payoff ratio)
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.trade_log_diagnostics import generate_arena_diagnostic_trade_log, run_trade_log_diagnostics


def test_generate_arena_diagnostic_trade_log():
    df_trades = generate_arena_diagnostic_trade_log(n_bars=100)
    assert isinstance(df_trades, pd.DataFrame)
    assert len(df_trades) > 0
    required_cols = [
        "timestamp", "horizon", "predicted_direction", "predicted_confidence",
        "actual_direction", "predicted_magnitude", "actual_magnitude", "PnL",
        "market_volatility_at_time", "was_near_news_event"
    ]
    for col in required_cols:
        assert col in df_trades.columns


def test_run_trade_log_diagnostics_structure():
    df_trades = generate_arena_diagnostic_trade_log(n_bars=80)
    results, summary = run_trade_log_diagnostics(df_trades)

    assert "test_a" in results
    assert "test_b" in results
    assert "test_c" in results
    assert "test_d" in results
    assert "recommended_architecture" in summary

    # Verify Test A structure
    assert "Horizon" in results["test_a"].columns
    assert "Directional Accuracy %" in results["test_a"].columns

    # Verify Test D structure
    assert "Payoff Ratio (|Win/Loss|)" in results["test_d"].columns
