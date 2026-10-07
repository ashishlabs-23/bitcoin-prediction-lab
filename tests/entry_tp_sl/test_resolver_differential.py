import pytest
from hypothesis import given, strategies as st, settings
from research.entry_tp_sl.barrier_contract import (
    RESOLVER_VERSION,
    OutcomeState,
    Side,
    CostScenario,
    PathBar,
    TradeContract
)
from research.entry_tp_sl.triple_barrier import build_trade_contract, TripleBarrierEngine
from research.entry_tp_sl.reference_resolver import ReferenceOracle


def make_bars(start_ts: int, prices: list, step: int = 60) -> list:
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


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("pair_id", ["barrier_pair_01", "barrier_pair_02", "barrier_pair_03", "barrier_pair_04", "barrier_pair_05"])
@pytest.mark.parametrize("scenario", ["TP_TOUCH", "SL_TOUCH", "TIMEOUT", "COLLISION", "GAP_OPEN_TP", "GAP_OPEN_SL"])
def test_deterministic_differential_parity(side, pair_id, scenario):
    engine = TripleBarrierEngine()
    oracle = ReferenceOracle()
    contract = build_trade_contract(pair_id, 1700000000, side, 100000.0, 0.01)

    u = contract.upper_boundary
    l = contract.lower_boundary
    mid = (u + l) / 2.0

    if scenario == "TP_TOUCH":
        # Long touches upper, Short touches lower
        touch_p = u + 50.0 if side == Side.LONG else l - 50.0
        prices = [(mid, max(mid, touch_p), min(mid, touch_p), mid)]
    elif scenario == "SL_TOUCH":
        touch_p = l - 50.0 if side == Side.LONG else u + 50.0
        prices = [(mid, max(mid, touch_p), min(mid, touch_p), mid)]
    elif scenario == "COLLISION":
        prices = [(mid, u + 50.0, l - 50.0, mid)]
    elif scenario == "GAP_OPEN_TP":
        # Open already beyond TP
        g_open = u + 100.0 if side == Side.LONG else l - 100.0
        prices = [(g_open, max(g_open, u + 150.0), min(g_open, l + 50.0), g_open)]
    elif scenario == "GAP_OPEN_SL":
        g_open = l - 100.0 if side == Side.LONG else u + 100.0
        prices = [(g_open, max(g_open, u - 50.0), min(g_open, l - 150.0), g_open)]
    else:  # TIMEOUT
        n_bars = contract.vertical_horizon_bars_1m
        prices = [(mid, mid + 10.0, mid - 10.0, mid + 5.0)] * n_bars

    bars = make_bars(contract.fill_timestamp, prices)

    res_engine = engine.resolve(contract, bars)
    res_oracle = oracle.evaluate(contract, bars)

    assert res_engine.outcome_state == res_oracle.outcome_state
    assert res_engine.first_touch == res_oracle.first_touch
    assert res_engine.same_timestamp_collision == res_oracle.same_timestamp_collision
    assert res_engine.unresolved_intrabar_order == res_oracle.unresolved_intrabar_order
    assert res_engine.timeout == res_oracle.timeout
    assert res_engine.data_gap == res_oracle.data_gap
    assert res_engine.path_bar_count == res_oracle.path_bar_count

    if res_engine.gross_r is not None:
        assert res_engine.gross_r == pytest.approx(res_oracle.gross_r, 1e-5)
        assert res_engine.cost_r == pytest.approx(res_oracle.cost_r, 1e-5)
        assert res_engine.net_r == pytest.approx(res_oracle.net_r, 1e-5)
        assert res_engine.exit_price == pytest.approx(res_oracle.exit_price, 1e-4)


@settings(max_examples=100, deadline=None)
@given(
    pair_id=st.sampled_from(["barrier_pair_01", "barrier_pair_02", "barrier_pair_04"]),
    side=st.sampled_from([Side.LONG, Side.SHORT]),
    price_offsets=st.lists(
        st.tuples(
            st.floats(min_value=-500.0, max_value=500.0),
            st.floats(min_value=-500.0, max_value=500.0)
        ),
        min_size=1,
        max_size=30
    )
)
def test_hypothesis_differential_randomized(pair_id, side, price_offsets):
    engine = TripleBarrierEngine()
    oracle = ReferenceOracle()
    contract = build_trade_contract(pair_id, 1700000000, side, 100000.0, 0.01)

    base = contract.entry_price
    prices = []
    for off1, off2 in price_offsets:
        high = base + max(off1, off2, 0.0)
        low = base + min(off1, off2, 0.0)
        open_p = (high + low) / 2.0
        close_p = (high + low) / 2.0
        prices.append((open_p, high, low, close_p))

    bars = make_bars(contract.fill_timestamp, prices)

    res_engine = engine.resolve(contract, bars)
    res_oracle = oracle.evaluate(contract, bars)

    assert res_engine.outcome_state == res_oracle.outcome_state
    assert res_engine.first_touch == res_oracle.first_touch
    assert res_engine.same_timestamp_collision == res_oracle.same_timestamp_collision
    if res_engine.net_r is not None and res_oracle.net_r is not None:
        assert res_engine.net_r == pytest.approx(res_oracle.net_r, 1e-5)
