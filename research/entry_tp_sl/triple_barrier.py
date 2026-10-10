"""
research/entry_tp_sl/triple_barrier.py
======================================
Primary deterministic triple-barrier outcome resolution engine.

Status: RESEARCH CANONICAL (Phase 6B)
Resolver Version: ENTRY_TP_SL_RESOLVER_V1
"""

import math
from typing import List, Optional, Dict, Any, Tuple
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


def build_trade_contract(
    pair_id: str,
    decision_timestamp: int,
    side: Side,
    next_1m_open: float,
    sigma_t0: float,
    cost_scenario: CostScenario = CostScenario.BASE
) -> TradeContract:
    """
    Constructs an immutable TradeContract based on decision time parameters.
    Enforces causal Point-in-Time constraints: all inputs must be known at t0.
    """
    if pair_id not in FROZEN_BARRIER_GRID:
        raise ValueError(f"Invalid pair_id: {pair_id}. Must be one of {list(FROZEN_BARRIER_GRID.keys())}")
    if next_1m_open <= 0 or math.isnan(next_1m_open) or math.isinf(next_1m_open):
        raise ValueError(f"Invalid next_1m_open price: {next_1m_open}")
    if sigma_t0 <= 0 or math.isnan(sigma_t0) or math.isinf(sigma_t0):
        raise ValueError(f"Invalid volatility sigma_t0: {sigma_t0}")

    grid_cfg = FROZEN_BARRIER_GRID[pair_id]
    cost_cfg = FROZEN_COST_PARAMS[cost_scenario]

    entry_slip_bps = cost_cfg["entry_slippage_bps"]
    entry_slip_factor = entry_slip_bps / 10000.0

    # Marketable order fills with execution slippage
    if side == Side.LONG:
        entry_price = round(next_1m_open * (1.0 + entry_slip_factor), 4)
    else:
        entry_price = round(next_1m_open * (1.0 - entry_slip_factor), 4)

    k_tp = grid_cfg["tp_multiplier"]
    k_sl = grid_cfg["sl_multiplier"]

    # Calculate nominal price boundaries
    if side == Side.LONG:
        upper_boundary = round(entry_price * (1.0 + k_tp * sigma_t0), 4)
        lower_boundary = round(entry_price * (1.0 - k_sl * sigma_t0), 4)
    else:
        # For SHORT: lower boundary is TP, upper boundary is SL
        upper_boundary = round(entry_price * (1.0 + k_sl * sigma_t0), 4)
        lower_boundary = round(entry_price * (1.0 - k_tp * sigma_t0), 4)

    if upper_boundary <= lower_boundary or lower_boundary <= 0:
        raise ValueError(f"Degenerate barriers generated: upper={upper_boundary}, lower={lower_boundary}")

    entry_timestamp = decision_timestamp
    fill_timestamp = decision_timestamp + 60  # Open of next 1-minute bar

    return TradeContract(
        pair_id=pair_id,
        decision_timestamp=decision_timestamp,
        entry_timestamp=entry_timestamp,
        fill_timestamp=fill_timestamp,
        side=side,
        entry_price=entry_price,
        upper_boundary=upper_boundary,
        lower_boundary=lower_boundary,
        vertical_horizon_minutes=grid_cfg["vertical_horizon_minutes"],
        vertical_horizon_bars_1m=grid_cfg["vertical_horizon_bars_1m"],
        tp_multiplier=k_tp,
        sl_multiplier=k_sl,
        sigma_t0=sigma_t0,
        cost_scenario=cost_scenario,
        resolver_version=RESOLVER_VERSION
    )


class TripleBarrierEngine:
    """
    Primary vectorized/procedural deterministic outcome resolution engine.
    Follows strict 6A contract invariants:
    - Conservative SL-first on unobserved intrabar collisions
    - Realized return on timeouts (never hard-coded to -1R)
    - Positive cost deductions
    - Explicit failure states
    """

    def __init__(self, resolver_version: str = RESOLVER_VERSION):
        self.resolver_version = resolver_version

    def resolve(self, contract: TradeContract, path_bars: List[PathBar]) -> OutcomeEvent:
        """Resolves trade outcome from 1-minute discrete path bars."""
        # 1. Path completeness and integrity checks
        if not path_bars:
            return self._fail_closed(contract, OutcomeState.DATA_UNAVAILABLE, "Empty path bars")

        # Validate monotonic timestamps and bar geometry
        expected_next_ts = contract.fill_timestamp
        valid_bars: List[PathBar] = []
        max_consecutive_missing = 0
        current_missing = 0

        for idx, bar in enumerate(path_bars):
            if not bar.validate():
                return self._fail_closed(contract, OutcomeState.DATA_GAP, f"Invalid bar structure at index {idx}")
            if idx > 0 and bar.timestamp <= path_bars[idx - 1].timestamp:
                return self._fail_closed(contract, OutcomeState.PROVENANCE_FAILURE, "Non-monotonic timestamps")
            
            # Check for bar timestamp relative to fill
            if bar.timestamp <= contract.fill_timestamp:
                continue  # Skip bars before or at fill timestamp

            # Measure gaps (expected step = 60s)
            if valid_bars:
                step = bar.timestamp - valid_bars[-1].timestamp
                if step > 60:
                    gap_bars = (step // 60) - 1
                    max_consecutive_missing = max(max_consecutive_missing, gap_bars)
                    if max_consecutive_missing > 3:
                        return self._fail_closed(contract, OutcomeState.DATA_GAP, "Excessive consecutive missing bars (> 3m)")

            valid_bars.append(bar)
            if len(valid_bars) >= contract.vertical_horizon_bars_1m:
                break

        # Check if we have enough path bars to evaluate
        if not valid_bars:
            return self._fail_closed(contract, OutcomeState.DATA_GAP, "No valid forward path bars")

        horizon_limit = min(len(valid_bars), contract.vertical_horizon_bars_1m)
        eval_bars = valid_bars[:horizon_limit]

        # Cost parameters
        cost_cfg = FROZEN_COST_PARAMS[contract.cost_scenario]
        total_cost_frac = cost_cfg["total_round_trip_cost_fraction"]
        one_r_usd = contract.one_r_usd

        # 2. Sequential path evaluation
        side_sign = 1.0 if contract.side == Side.LONG else -1.0

        for bar_idx, bar in enumerate(eval_bars):
            touch_upper = bar.high >= contract.upper_boundary
            touch_lower = bar.low <= contract.lower_boundary

            # Check gap crossings at open
            gapped_above_upper = bar.open >= contract.upper_boundary
            gapped_below_lower = bar.open <= contract.lower_boundary

            # CASE A: Same-bar dual-touch (Collision)
            if touch_upper and touch_lower:
                # Primary conservative policy: SL-first
                if contract.side == Side.LONG:
                    first_touch = "LOWER"
                    exit_p = contract.lower_boundary if not gapped_below_lower else bar.open
                else:
                    first_touch = "UPPER"
                    exit_p = contract.upper_boundary if not gapped_above_upper else bar.open

                gross_ret = (exit_p - contract.entry_price) * side_sign / contract.entry_price
                gross_r = -1.0  # SL exit is -1.0R baseline (adjusted for gap if any)
                if abs(exit_p - (contract.lower_boundary if contract.side == Side.LONG else contract.upper_boundary)) > 1e-4:
                    gross_r = ((exit_p - contract.entry_price) * side_sign) / one_r_usd

                cost_r = total_cost_frac / (contract.sl_multiplier * contract.sigma_t0)
                net_r = gross_r - cost_r
                pnl_bps = round(gross_ret * 10000.0 - cost_cfg["total_round_trip_cost_bps"], 2)

                return OutcomeEvent(
                    resolver_version=self.resolver_version,
                    pair_id=contract.pair_id,
                    decision_timestamp=contract.decision_timestamp,
                    entry_timestamp=contract.entry_timestamp,
                    fill_timestamp=contract.fill_timestamp,
                    side=contract.side,
                    entry_price=contract.entry_price,
                    upper_boundary=contract.upper_boundary,
                    lower_boundary=contract.lower_boundary,
                    vertical_horizon_minutes=contract.vertical_horizon_minutes,
                    first_touch=first_touch,
                    exit_timestamp=bar.timestamp,
                    exit_price=exit_p,
                    same_timestamp_collision=True,
                    observed_order=None,
                    unresolved_intrabar_order=True,
                    timeout=False,
                    data_gap=False,
                    exact_boundary_touch=(bar.high == contract.upper_boundary or bar.low == contract.lower_boundary),
                    crossing_between_samples=(gapped_above_upper or gapped_below_lower),
                    gross_return=gross_ret,
                    gross_r=gross_r,
                    cost_r=cost_r,
                    net_r=net_r,
                    outcome_state=OutcomeState.SL_FIRST,
                    realized_pnl_bps=pnl_bps,
                    path_bar_count=bar_idx + 1
                )

            # CASE B: Single Upper Touch
            elif touch_upper:
                exit_p = contract.upper_boundary if not gapped_above_upper else bar.open
                gross_ret = (exit_p - contract.entry_price) * side_sign / contract.entry_price

                if contract.side == Side.LONG:
                    outcome_state = OutcomeState.TP_FIRST
                    first_touch = "UPPER"
                    gross_r = +(contract.tp_multiplier / contract.sl_multiplier)
                    if gapped_above_upper:
                        gross_r = ((exit_p - contract.entry_price) * side_sign) / one_r_usd
                else:
                    outcome_state = OutcomeState.SL_FIRST
                    first_touch = "UPPER"
                    gross_r = -1.0
                    if gapped_above_upper:
                        gross_r = ((exit_p - contract.entry_price) * side_sign) / one_r_usd

                cost_r = total_cost_frac / (contract.sl_multiplier * contract.sigma_t0)
                net_r = gross_r - cost_r
                pnl_bps = round(gross_ret * 10000.0 - cost_cfg["total_round_trip_cost_bps"], 2)

                return OutcomeEvent(
                    resolver_version=self.resolver_version,
                    pair_id=contract.pair_id,
                    decision_timestamp=contract.decision_timestamp,
                    entry_timestamp=contract.entry_timestamp,
                    fill_timestamp=contract.fill_timestamp,
                    side=contract.side,
                    entry_price=contract.entry_price,
                    upper_boundary=contract.upper_boundary,
                    lower_boundary=contract.lower_boundary,
                    vertical_horizon_minutes=contract.vertical_horizon_minutes,
                    first_touch=first_touch,
                    exit_timestamp=bar.timestamp,
                    exit_price=exit_p,
                    same_timestamp_collision=False,
                    observed_order=None,
                    unresolved_intrabar_order=False,
                    timeout=False,
                    data_gap=False,
                    exact_boundary_touch=(bar.high == contract.upper_boundary),
                    crossing_between_samples=gapped_above_upper,
                    gross_return=gross_ret,
                    gross_r=gross_r,
                    cost_r=cost_r,
                    net_r=net_r,
                    outcome_state=outcome_state,
                    realized_pnl_bps=pnl_bps,
                    path_bar_count=bar_idx + 1
                )

            # CASE C: Single Lower Touch
            elif touch_lower:
                exit_p = contract.lower_boundary if not gapped_below_lower else bar.open
                gross_ret = (exit_p - contract.entry_price) * side_sign / contract.entry_price

                if contract.side == Side.LONG:
                    outcome_state = OutcomeState.SL_FIRST
                    first_touch = "LOWER"
                    gross_r = -1.0
                    if gapped_below_lower:
                        gross_r = ((exit_p - contract.entry_price) * side_sign) / one_r_usd
                else:
                    outcome_state = OutcomeState.TP_FIRST
                    first_touch = "LOWER"
                    gross_r = +(contract.tp_multiplier / contract.sl_multiplier)
                    if gapped_below_lower:
                        gross_r = ((exit_p - contract.entry_price) * side_sign) / one_r_usd

                cost_r = total_cost_frac / (contract.sl_multiplier * contract.sigma_t0)
                net_r = gross_r - cost_r
                pnl_bps = round(gross_ret * 10000.0 - cost_cfg["total_round_trip_cost_bps"], 2)

                return OutcomeEvent(
                    resolver_version=self.resolver_version,
                    pair_id=contract.pair_id,
                    decision_timestamp=contract.decision_timestamp,
                    entry_timestamp=contract.entry_timestamp,
                    fill_timestamp=contract.fill_timestamp,
                    side=contract.side,
                    entry_price=contract.entry_price,
                    upper_boundary=contract.upper_boundary,
                    lower_boundary=contract.lower_boundary,
                    vertical_horizon_minutes=contract.vertical_horizon_minutes,
                    first_touch=first_touch,
                    exit_timestamp=bar.timestamp,
                    exit_price=exit_p,
                    same_timestamp_collision=False,
                    observed_order=None,
                    unresolved_intrabar_order=False,
                    timeout=False,
                    data_gap=False,
                    exact_boundary_touch=(bar.low == contract.lower_boundary),
                    crossing_between_samples=gapped_below_lower,
                    gross_return=gross_ret,
                    gross_r=gross_r,
                    cost_r=cost_r,
                    net_r=net_r,
                    outcome_state=outcome_state,
                    realized_pnl_bps=pnl_bps,
                    path_bar_count=bar_idx + 1
                )

        # CASE D: Vertical Timeout (neither barrier touched)
        if len(eval_bars) < contract.vertical_horizon_bars_1m - 3:
            # If stream ended prematurely without hitting horizon or barrier -> DATA_GAP
            return self._fail_closed(contract, OutcomeState.DATA_GAP, "Incomplete horizon path coverage")

        final_bar = eval_bars[-1]
        exit_p = final_bar.close
        gross_ret = (exit_p - contract.entry_price) * side_sign / contract.entry_price
        gross_r = ((exit_p - contract.entry_price) * side_sign) / one_r_usd
        cost_r = total_cost_frac / (contract.sl_multiplier * contract.sigma_t0)
        net_r = gross_r - cost_r
        pnl_bps = round(gross_ret * 10000.0 - cost_cfg["total_round_trip_cost_bps"], 2)

        return OutcomeEvent(
            resolver_version=self.resolver_version,
            pair_id=contract.pair_id,
            decision_timestamp=contract.decision_timestamp,
            entry_timestamp=contract.entry_timestamp,
            fill_timestamp=contract.fill_timestamp,
            side=contract.side,
            entry_price=contract.entry_price,
            upper_boundary=contract.upper_boundary,
            lower_boundary=contract.lower_boundary,
            vertical_horizon_minutes=contract.vertical_horizon_minutes,
            first_touch="VERTICAL_TIMEOUT",
            exit_timestamp=final_bar.timestamp,
            exit_price=exit_p,
            same_timestamp_collision=False,
            observed_order=None,
            unresolved_intrabar_order=False,
            timeout=True,
            data_gap=False,
            exact_boundary_touch=False,
            crossing_between_samples=False,
            gross_return=gross_ret,
            gross_r=gross_r,
            cost_r=cost_r,
            net_r=net_r,
            outcome_state=OutcomeState.TIMEOUT,
            realized_pnl_bps=pnl_bps,
            path_bar_count=len(eval_bars)
        )

    def _fail_closed(self, contract: TradeContract, state: OutcomeState, reason: str) -> OutcomeEvent:
        """Returns a non-numeric fail-closed OutcomeEvent."""
        return OutcomeEvent(
            resolver_version=self.resolver_version,
            pair_id=contract.pair_id,
            decision_timestamp=contract.decision_timestamp,
            entry_timestamp=contract.entry_timestamp,
            fill_timestamp=contract.fill_timestamp,
            side=contract.side,
            entry_price=contract.entry_price,
            upper_boundary=contract.upper_boundary,
            lower_boundary=contract.lower_boundary,
            vertical_horizon_minutes=contract.vertical_horizon_minutes,
            first_touch=None,
            exit_timestamp=None,
            exit_price=None,
            same_timestamp_collision=False,
            observed_order=None,
            unresolved_intrabar_order=False,
            timeout=False,
            data_gap=(state == OutcomeState.DATA_GAP),
            exact_boundary_touch=False,
            crossing_between_samples=False,
            gross_return=None,
            gross_r=None,
            cost_r=None,
            net_r=None,
            outcome_state=state,
            realized_pnl_bps=None,
            path_bar_count=0
        )
