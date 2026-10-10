import pytest
from research.entry_tp_sl.barrier_contract import Side, CostScenario, PathBar, OutcomeState
from research.entry_tp_sl.triple_barrier import build_trade_contract, TripleBarrierEngine


def make_constant_bars(start_ts: int, close_prices: list) -> list:
    bars = []
    for i, c in enumerate(close_prices):
        bars.append(PathBar(
            timestamp=start_ts + (i + 1) * 60,
            open=c,
            high=c + 1.0,
            low=c - 1.0,
            close=c,
            volume=10.0
        ))
    return bars


def test_timeout_gross_r_is_continuous_and_non_hardcoded():
    engine = TripleBarrierEngine()
    contract = build_trade_contract("barrier_pair_04", 1700000000, Side.LONG, 100000.0, 0.01)
    # Pair 04: horizon 120 bars, 1R = 100050 * 0.75 * 0.01 = 750.375 USD
    
    # Case 1: Timeout at profit (+300 USD)
    prices_profit = [100050.0] * 119 + [100350.0]
    bars_profit = make_constant_bars(contract.fill_timestamp, prices_profit)
    event_profit = engine.resolve(contract, bars_profit)
    
    assert event_profit.outcome_state == OutcomeState.TIMEOUT
    assert event_profit.timeout is True
    assert event_profit.gross_r == pytest.approx(300.0 / contract.one_r_usd, 1e-5)
    assert event_profit.gross_r > 0

    # Case 2: Timeout at exact breakeven (0.0 USD)
    prices_even = [100050.0] * 120
    bars_even = make_constant_bars(contract.fill_timestamp, prices_even)
    event_even = engine.resolve(contract, bars_even)
    assert event_even.gross_r == pytest.approx(0.0, 1e-6)

    # Case 3: Timeout at small loss (-200 USD)
    prices_loss = [100050.0] * 119 + [99850.0]
    bars_loss = make_constant_bars(contract.fill_timestamp, prices_loss)
    event_loss = engine.resolve(contract, bars_loss)
    assert event_loss.gross_r == pytest.approx(-200.0 / contract.one_r_usd, 1e-5)
    assert event_loss.gross_r > -1.0  # Not a full SL loss!
