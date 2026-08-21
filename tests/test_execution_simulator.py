"""
Unit tests for backtest/execution_simulator.py module.
"""

import pytest
from backtest.execution_simulator import ExecutionSimulator


def test_execution_simulator_fees_and_slippage():
    sim = ExecutionSimulator(maker_fee_bps=2.0, taker_fee_bps=5.0, base_slippage_bps=3.0)

    # Taker Buy Execution
    res_buy = sim.execute_order(side="BUY", price=50000.0, order_size_usdt=10000.0, bid_ask_spread_pct=0.0010, vpin=0.30, is_maker=False)
    assert res_buy['side'] == "BUY"
    assert res_buy['fill_price'] > 50000.0
    assert res_buy['fee_rate'] == 0.0005 # 5 bps
    assert res_buy['slippage_rate'] > 0.0

    # Maker Sell Execution
    res_sell = sim.execute_order(side="SELL", price=50000.0, order_size_usdt=10000.0, bid_ask_spread_pct=0.0010, vpin=0.30, is_maker=True)
    assert res_sell['side'] == "SELL"
    assert res_sell['fill_price'] < 50000.0
    assert res_sell['fee_rate'] == 0.0002 # 2 bps


def test_dynamic_tp_sl_calculation():
    sim = ExecutionSimulator()

    # LONG Position
    long_bounds = sim.compute_dynamic_tp_sl(entry_price=50000.0, direction="LONG", atr=500.0, tp_mult=2.0, sl_mult=1.5)
    assert long_bounds['tp_price'] == 51000.0
    assert long_bounds['sl_price'] == 49250.0

    # SHORT Position
    short_bounds = sim.compute_dynamic_tp_sl(entry_price=50000.0, direction="SHORT", atr=500.0, tp_mult=2.0, sl_mult=1.5)
    assert short_bounds['tp_price'] == 49000.0
    assert short_bounds['sl_price'] == 50750.0
