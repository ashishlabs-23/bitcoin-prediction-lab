"""
Unit tests for position closure evaluation on candle high/low in backtest/simulate.py.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backtest.simulate import check_position_closure_high_low


def test_long_position_closure_on_candle_high_low():
    """LONG closes if candle high >= TP or low <= SL."""
    # Scenario 1: Candle high hits TP even if current spot is below TP
    res_tp = check_position_closure_high_low(
        direction="LONG",
        tp=119000.0,
        sl=117000.0,
        candle_high=119050.0,
        candle_low=118200.0
    )
    assert res_tp["closed"] is True
    assert res_tp["reason"] == "TP_HIT"
    assert res_tp["close_price"] == 119000.0

    # Scenario 2: Candle low hits SL
    res_sl = check_position_closure_high_low(
        direction="LONG",
        tp=119000.0,
        sl=117000.0,
        candle_high=118500.0,
        candle_low=116900.0
    )
    assert res_sl["closed"] is True
    assert res_sl["reason"] == "SL_HIT"
    assert res_sl["close_price"] == 117000.0

    # Scenario 3: Neither hit
    res_open = check_position_closure_high_low(
        direction="LONG",
        tp=119000.0,
        sl=117000.0,
        candle_high=118800.0,
        candle_low=117200.0
    )
    assert res_open["closed"] is False


def test_short_position_closure_on_candle_high_low():
    """SHORT closes if candle low <= TP or high >= SL."""
    res_tp = check_position_closure_high_low(
        direction="SHORT",
        tp=115000.0,
        sl=118000.0,
        candle_high=116800.0,
        candle_low=114900.0
    )
    assert res_tp["closed"] is True
    assert res_tp["reason"] == "TP_HIT"
    assert res_tp["close_price"] == 115000.0
