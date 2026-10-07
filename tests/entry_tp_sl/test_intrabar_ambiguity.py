import pytest
from research.entry_tp_sl.barrier_contract import Side, CostScenario, PathBar, OutcomeState
from research.entry_tp_sl.triple_barrier import build_trade_contract, TripleBarrierEngine


def test_dual_touch_metadata_preservation():
    """Verify that unobserved same-bar dual-touch resolves to SL_FIRST while preserving collision metadata."""
    engine = TripleBarrierEngine()
    
    # Test for LONG
    contract_long = build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, 100000.0, 0.01)
    bar_long = PathBar(timestamp=contract_long.fill_timestamp + 60, open=100050.0, high=102000.0, low=98000.0, close=100000.0, volume=10.0)
    event_long = engine.resolve(contract_long, [bar_long])
    
    assert event_long.outcome_state == OutcomeState.SL_FIRST
    assert event_long.same_timestamp_collision is True
    assert event_long.unresolved_intrabar_order is True
    assert event_long.observed_order is None
    assert event_long.first_touch == "LOWER"
    assert event_long.gross_r == -1.0

    # Test for SHORT
    contract_short = build_trade_contract("barrier_pair_01", 1700000000, Side.SHORT, 100000.0, 0.01)
    bar_short = PathBar(timestamp=contract_short.fill_timestamp + 60, open=99950.0, high=102000.0, low=98000.0, close=100000.0, volume=10.0)
    event_short = engine.resolve(contract_short, [bar_short])
    
    assert event_short.outcome_state == OutcomeState.SL_FIRST
    assert event_short.same_timestamp_collision is True
    assert event_short.unresolved_intrabar_order is True
    assert event_short.observed_order is None
    assert event_short.first_touch == "UPPER"  # For short, Upper is SL
    assert event_short.gross_r == -1.0


def test_single_touch_does_not_flag_collision():
    """Verify that single-boundary touches do NOT set same_timestamp_collision or unresolved_intrabar_order."""
    engine = TripleBarrierEngine()
    contract = build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, 100000.0, 0.01)
    
    bar_tp = PathBar(timestamp=contract.fill_timestamp + 60, open=100050.0, high=102000.0, low=99500.0, close=101000.0, volume=10.0)
    event_tp = engine.resolve(contract, [bar_tp])
    
    assert event_tp.outcome_state == OutcomeState.TP_FIRST
    assert event_tp.same_timestamp_collision is False
    assert event_tp.unresolved_intrabar_order is False
    assert event_tp.first_touch == "UPPER"
