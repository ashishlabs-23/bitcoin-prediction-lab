import pytest
from research.entry_tp_sl.barrier_contract import Side, CostScenario, PathBar, OutcomeState
from research.entry_tp_sl.triple_barrier import build_trade_contract, TripleBarrierEngine


def test_base_vs_conservative_cost_scenarios():
    engine = TripleBarrierEngine()
    
    contract_base = build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, 100000.0, 0.01, CostScenario.BASE)
    contract_cons = build_trade_contract("barrier_pair_01", 1700000000, Side.LONG, 100000.0, 0.01, CostScenario.CONSERVATIVE)
    
    # Same price path hitting TP
    bar = PathBar(timestamp=contract_base.fill_timestamp + 60, open=100050.0, high=102000.0, low=99500.0, close=101500.0, volume=10.0)
    
    event_base = engine.resolve(contract_base, [bar])
    event_cons = engine.resolve(contract_cons, [bar])
    
    assert event_base.gross_r == event_cons.gross_r == 1.0
    
    # Cost R must be strictly positive
    assert event_base.cost_r > 0
    assert event_cons.cost_r > 0
    
    # Conservative cost R must be strictly greater than Base cost R
    assert event_cons.cost_r > event_base.cost_r
    
    # Net R must be strictly lower under Conservative
    assert event_cons.net_r < event_base.net_r
    
    # Monotonicity: higher cost can never increase net R
    assert event_base.net_r == pytest.approx(1.0 - event_base.cost_r, 1e-6)
    assert event_cons.net_r == pytest.approx(1.0 - event_cons.cost_r, 1e-6)
