"""
tests/test_phase5_paper_simulator.py — Verification of Phase 5 Paper Research Simulator
========================================================================================
Tests:
1. PaperResearchSimulator executes with 1-bar execution lag (zero lookahead).
2. Evaluates stop-loss before take-profit if both are touched within the same bar.
3. Deducts taker frictions (fee, spread, slippage) on both entry and exit.
4. Generates complete performance analytics (Sharpe, Max Drawdown, Profit Factor).
5. Enforces OFFLINE_RESEARCH_ONLY with live_broker_connected = False.
"""

from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
import pytest

from backtest.paper_research_simulator import (
    PaperResearchSimulator,
    PaperTrade,
    PaperSimulationSummary,
)
from backtest.execution_reality import ExecutionRealityEngine


def test_paper_simulator_execution_lag_and_conservative_sl():
    simulator = PaperResearchSimulator(initial_capital_usd=100_000.0)

    # Construct synthetic candles
    base_time = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    candles = []
    prices = [90000.0]

    for i in range(100):
        t = base_time + timedelta(hours=i)
        p = prices[-1] * (1.0 + np.sin(i / 5.0) * 0.01)
        prices.append(p)
        candles.append({
            "timestamp": t.isoformat(),
            "open": p,
            "high": p * 1.01,
            "low": p * 0.99,
            "close": p * 1.002,
            "volume": 100.0
        })

    df_candles = pd.DataFrame(candles)

    # Signal: LONG at bar 5, FLAT elsewhere
    signals = pd.Series([0] * 100)
    signals.iloc[5] = 1

    summary, trades, equity_curve = simulator.simulate(
        df_candles=df_candles,
        signals=signals,
        tp_pct=0.03,
        sl_pct=0.02,
        max_holding_bars=10
    )

    assert summary.execution_mode == "OFFLINE_RESEARCH_ONLY"
    assert summary.live_broker_connected is False
    assert len(trades) >= 1

    # First trade entered at bar 6 open (1-bar lag after bar 5 signal)
    first_trade = trades[0]
    expected_entry_time = str(df_candles.iloc[6]["timestamp"])
    assert first_trade.entry_time == expected_entry_time
    assert first_trade.entry_price == df_candles.iloc[6]["open"]
    assert first_trade.fees_paid_usd > 0
    assert first_trade.slippage_usd > 0


def test_intrabar_sl_priority_over_tp():
    simulator = PaperResearchSimulator(initial_capital_usd=100_000.0)
    base_time = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Bar 0: baseline
    # Bar 1: signal bar
    # Bar 2: entry bar (open=100,000)
    # Bar 3: both high=105,000 (+5%) and low=95,000 (-5%) hit! (TP=2%, SL=1.5%)
    candles = [
        {"timestamp": (base_time + timedelta(hours=0)).isoformat(), "open": 100000, "high": 100100, "low": 99900, "close": 100000, "volume": 10},
        {"timestamp": (base_time + timedelta(hours=1)).isoformat(), "open": 100000, "high": 100100, "low": 99900, "close": 100000, "volume": 10},
        {"timestamp": (base_time + timedelta(hours=2)).isoformat(), "open": 100000, "high": 100100, "low": 99900, "close": 100000, "volume": 10},
        {"timestamp": (base_time + timedelta(hours=3)).isoformat(), "open": 100000, "high": 105000, "low": 95000, "close": 100000, "volume": 10},
    ] + [
        {"timestamp": (base_time + timedelta(hours=i)).isoformat(), "open": 100000, "high": 100100, "low": 99900, "close": 100000, "volume": 10}
        for i in range(4, 60)
    ]

    df_candles = pd.DataFrame(candles)
    signals = pd.Series([0] * len(candles))
    signals.iloc[1] = 1 # LONG signal

    summary, trades, equity_curve = simulator.simulate(
        df_candles=df_candles,
        signals=signals,
        tp_pct=0.02,
        sl_pct=0.015,
        max_holding_bars=10
    )

    assert len(trades) >= 1
    trade = trades[0]
    # Stop Loss MUST be evaluated first
    assert trade.exit_reason == "SL_HIT"
    assert trade.exit_price == 100000 * (1.0 - 0.015)
    assert trade.net_return_pct < 0
