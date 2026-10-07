import pytest
from research.entry_tp_sl.barrier_contract import Side, CostScenario, PathBar, OutcomeState
from research.entry_tp_sl.triple_barrier import build_trade_contract, TripleBarrierEngine


def test_pit_contract_parameters_immutable():
    """Verify that future price movements cannot alter already-frozen TradeContract parameters."""
    t0 = 1700000000
    contract = build_trade_contract("barrier_pair_01", t0, Side.LONG, 100000.0, 0.01)
    
    # Contract parameters must remain constant
    assert contract.decision_timestamp == t0
    assert contract.entry_price == 100050.0
    assert contract.upper_boundary == round(100050.0 * 1.01, 4)
    assert contract.lower_boundary == round(100050.0 * 0.99, 4)
    assert contract.sigma_t0 == 0.01

    # Attempting to mutate dataclass raises FrozenInstanceError
    with pytest.raises(Exception):
        contract.upper_boundary = 200000.0


def test_bars_prior_to_fill_are_ignored():
    """Verify that path bars occurring before or at fill_timestamp do not trigger premature resolution."""
    engine = TripleBarrierEngine()
    contract = build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, 100000.0, 0.01)
    
    # Bar at decision_timestamp (t0) has high >= upper, but is before fill
    pre_bar = PathBar(timestamp=contract.decision_timestamp, open=100000.0, high=105000.0, low=99000.0, close=100000.0, volume=10.0)
    fill_bar = PathBar(timestamp=contract.fill_timestamp, open=100000.0, high=105000.0, low=99000.0, close=100000.0, volume=10.0)
    
    # Valid post-fill bar that does not touch boundaries
    post_bar = PathBar(timestamp=contract.fill_timestamp + 60, open=100050.0, high=100200.0, low=99900.0, close=100100.0, volume=10.0)
    
    # Pass pre-bars along with 1 post-fill bar (short of horizon)
    event = engine.resolve(contract, [pre_bar, fill_bar, post_bar])
    # Must NOT resolve to TP_FIRST from pre-fill bars!
    assert event.outcome_state == OutcomeState.DATA_GAP or event.outcome_state == OutcomeState.TIMEOUT
    assert event.first_touch != "UPPER"


def test_post_resolution_data_cannot_alter_outcome():
    """Verify that adding bars after a touch resolution does not alter the resolved outcome."""
    engine = TripleBarrierEngine()
    contract = build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, 100000.0, 0.01)
    
    # Bar 1 hits TP
    bar1 = PathBar(timestamp=contract.fill_timestamp + 60, open=100050.0, high=102000.0, low=99500.0, close=101500.0, volume=10.0)
    
    # Bar 2 crashes to 50,000 (huge SL crash)
    bar2 = PathBar(timestamp=contract.fill_timestamp + 120, open=101500.0, high=101500.0, low=50000.0, close=50000.0, volume=10.0)
    
    event1 = engine.resolve(contract, [bar1])
    event2 = engine.resolve(contract, [bar1, bar2])
    
    assert event1.outcome_state == OutcomeState.TP_FIRST
    assert event2.outcome_state == OutcomeState.TP_FIRST
    assert event1.exit_timestamp == event2.exit_timestamp
    assert event1.exit_price == event2.exit_price
    assert event1.net_r == event2.net_r
