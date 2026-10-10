import pytest
from research.entry_tp_sl.barrier_contract import (
    RESOLVER_VERSION,
    OutcomeState,
    Side,
    CostScenario,
    FROZEN_COST_PARAMS,
    FROZEN_BARRIER_GRID,
    PathBar,
    TradeContract,
    OutcomeEvent
)
from research.entry_tp_sl.triple_barrier import build_trade_contract


def test_path_bar_validation():
    valid_bar = PathBar(timestamp=1700000060, open=100.0, high=105.0, low=95.0, close=102.0, volume=10.0)
    assert valid_bar.validate() is True

    # Inverted high/low
    invalid_bar = PathBar(timestamp=1700000060, open=100.0, high=90.0, low=95.0, close=102.0, volume=10.0)
    assert invalid_bar.validate() is False

    # Negative price
    invalid_bar2 = PathBar(timestamp=1700000060, open=-100.0, high=105.0, low=95.0, close=102.0, volume=10.0)
    assert invalid_bar2.validate() is False

    # Negative volume
    invalid_bar3 = PathBar(timestamp=1700000060, open=100.0, high=105.0, low=95.0, close=102.0, volume=-1.0)
    assert invalid_bar3.validate() is False


def test_build_trade_contract_long_and_short():
    contract_long = build_trade_contract(
        pair_id="barrier_pair_01",
        decision_timestamp=1700000000,
        side=Side.LONG,
        next_1m_open=100000.0,
        sigma_t0=0.01,
        cost_scenario=CostScenario.BASE
    )

    assert contract_long.side == Side.LONG
    # Long slippage 5 bps on 100,000 = 100,050.0
    assert contract_long.entry_price == 100050.0
    # TP = entry * (1 + 1.0 * 0.01) = 101,050.5
    assert contract_long.upper_boundary == round(100050.0 * 1.01, 4)
    # SL = entry * (1 - 1.0 * 0.01) = 99,049.5
    assert contract_long.lower_boundary == round(100050.0 * 0.99, 4)
    assert contract_long.vertical_horizon_bars_1m == 240
    assert contract_long.one_r_usd == 100050.0 * 1.0 * 0.01

    contract_short = build_trade_contract(
        pair_id="barrier_pair_01",
        decision_timestamp=1700000000,
        side=Side.SHORT,
        next_1m_open=100000.0,
        sigma_t0=0.01,
        cost_scenario=CostScenario.BASE
    )

    assert contract_short.side == Side.SHORT
    # Short slippage 5 bps on 100,000 = 99,950.0
    assert contract_short.entry_price == 99950.0
    # For short, Upper is SL (entry * (1 + 0.01))
    assert contract_short.upper_boundary == round(99950.0 * 1.01, 4)
    # Lower is TP (entry * (1 - 0.01))
    assert contract_short.lower_boundary == round(99950.0 * 0.99, 4)


def test_invalid_contract_inputs_raise_errors():
    with pytest.raises(ValueError, match="Invalid pair_id"):
        build_trade_contract("invalid_pair", 1700000000, Side.LONG, 100000.0, 0.01)

    with pytest.raises(ValueError, match="Invalid next_1m_open"):
        build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, -100.0, 0.01)

    with pytest.raises(ValueError, match="Invalid volatility"):
        build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, 100000.0, 0.0)
