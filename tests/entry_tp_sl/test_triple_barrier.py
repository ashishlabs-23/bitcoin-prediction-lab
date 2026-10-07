import pytest
from research.entry_tp_sl.barrier_contract import (
    RESOLVER_VERSION,
    OutcomeState,
    Side,
    CostScenario,
    PathBar,
    TradeContract
)
from research.entry_tp_sl.triple_barrier import build_trade_contract, TripleBarrierEngine


def make_bars(start_ts: int, prices: list, step: int = 60) -> list:
    """Helper to generate sequential PathBar instances."""
    bars = []
    for i, (o, h, l, c) in enumerate(prices):
        bars.append(PathBar(
            timestamp=start_ts + (i + 1) * step,
            open=float(o),
            high=float(h),
            low=float(l),
            close=float(c),
            volume=10.0
        ))
    return bars


def test_triple_barrier_tp_first_long():
    engine = TripleBarrierEngine()
    contract = build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, 100000.0, 0.01)
    
    # Upper boundary is 101,050.5, Lower is 99,049.5
    # Bar 1 touches upper boundary (High = 101,200)
    bars = make_bars(contract.fill_timestamp, [
        (100050.0, 101200.0, 99500.0, 101100.0)
    ])
    
    event = engine.resolve(contract, bars)
    assert event.outcome_state == OutcomeState.TP_FIRST
    assert event.first_touch == "UPPER"
    assert event.exit_price == contract.upper_boundary
    assert event.same_timestamp_collision is False
    assert event.gross_r == 1.0  # k_tp / k_sl = 1.0
    assert event.cost_r > 0
    assert event.net_r == pytest.approx(1.0 - event.cost_r, 1e-6)


def test_triple_barrier_sl_first_long():
    engine = TripleBarrierEngine()
    contract = build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, 100000.0, 0.01)
    
    # Bar 1 touches lower boundary (Low = 98,900)
    bars = make_bars(contract.fill_timestamp, [
        (100050.0, 100500.0, 98900.0, 99100.0)
    ])
    
    event = engine.resolve(contract, bars)
    assert event.outcome_state == OutcomeState.SL_FIRST
    assert event.first_touch == "LOWER"
    assert event.exit_price == contract.lower_boundary
    assert event.gross_r == -1.0
    assert event.net_r == pytest.approx(-1.0 - event.cost_r, 1e-6)


def test_triple_barrier_timeout_exit():
    engine = TripleBarrierEngine()
    contract = build_trade_contract("barrier_pair_04", 1700000000, Side.LONG, 100000.0, 0.01)
    # Horizon is 120 bars for pair_04
    
    # Generate 120 bars that stay strictly within boundaries [99250, 100750]
    prices = [(100000.0, 100200.0, 99800.0, 100100.0)] * 120
    # Last bar closes at 100,300 (above entry of 100,050 -> positive gross return on timeout)
    prices[-1] = (100100.0, 100400.0, 99900.0, 100300.0)
    bars = make_bars(contract.fill_timestamp, prices)
    
    event = engine.resolve(contract, bars)
    assert event.outcome_state == OutcomeState.TIMEOUT
    assert event.timeout is True
    assert event.first_touch == "VERTICAL_TIMEOUT"
    assert event.exit_price == 100300.0
    # Gross R must reflect actual price difference: (100300 - 100050) / (100050 * 0.75 * 0.01)
    expected_gross_r = (100300.0 - contract.entry_price) / contract.one_r_usd
    assert event.gross_r == pytest.approx(expected_gross_r, 1e-6)
    assert event.gross_r > 0.0  # Positive timeout R! Proves never hardcoded to -1R!


def test_triple_barrier_dual_touch_collision():
    engine = TripleBarrierEngine()
    contract = build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, 100000.0, 0.01)
    
    # Bar touches BOTH high (101500 >= upper) AND low (98500 <= lower)
    bars = make_bars(contract.fill_timestamp, [
        (100050.0, 101500.0, 98500.0, 100000.0)
    ])
    
    event = engine.resolve(contract, bars)
    # Primary conservative policy: SL_FIRST
    assert event.outcome_state == OutcomeState.SL_FIRST
    assert event.first_touch == "LOWER"
    assert event.same_timestamp_collision is True
    assert event.unresolved_intrabar_order is True
    assert event.observed_order is None
    assert event.gross_r == -1.0


def test_triple_barrier_gap_failure():
    engine = TripleBarrierEngine()
    contract = build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, 100000.0, 0.01)
    
    # Step has a 5-minute missing gap (> 3 minutes tolerance)
    bars = [
        PathBar(timestamp=contract.fill_timestamp + 60, open=100050.0, high=100100.0, low=99900.0, close=100000.0, volume=1.0),
        PathBar(timestamp=contract.fill_timestamp + 360, open=100050.0, high=100100.0, low=99900.0, close=100000.0, volume=1.0) # gap of 300s (5 min)
    ]
    
    event = engine.resolve(contract, bars)
    assert event.outcome_state == OutcomeState.DATA_GAP
    assert event.data_gap is True
    assert event.gross_r is None
    assert event.net_r is None
