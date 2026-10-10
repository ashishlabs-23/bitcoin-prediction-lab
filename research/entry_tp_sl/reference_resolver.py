"""
research/entry_tp_sl/reference_resolver.py
==========================================
Independent pure-Python reference oracle for differential verification.

Status: REFERENCE ORACLE (Phase 6B)
Resolver Version: ENTRY_TP_SL_RESOLVER_V1
"""

from typing import List, Optional, Dict, Any
from research.entry_tp_sl.barrier_contract import (
    RESOLVER_VERSION,
    OutcomeState,
    Side,
    CostScenario,
    FROZEN_COST_PARAMS,
    PathBar,
    TradeContract,
    OutcomeEvent
)


class ReferenceOracle:
    """
    Independent pure-Python oracle written with discrete step-by-step procedural logic.
    Used exclusively for differential testing against TripleBarrierEngine.
    """

    def __init__(self, resolver_version: str = RESOLVER_VERSION):
        self.resolver_version = resolver_version

    def evaluate(self, contract: TradeContract, path_bars: List[PathBar]) -> OutcomeEvent:
        if not path_bars:
            return self._build_failure(contract, OutcomeState.DATA_UNAVAILABLE)

        # 1. Filter bars strictly after fill timestamp
        filtered_bars: List[PathBar] = []
        for i, b in enumerate(path_bars):
            if not b.validate():
                return self._build_failure(contract, OutcomeState.DATA_GAP)
            if i > 0 and b.timestamp <= path_bars[i - 1].timestamp:
                return self._build_failure(contract, OutcomeState.PROVENANCE_FAILURE)
            if b.timestamp > contract.fill_timestamp:
                filtered_bars.append(b)

        if not filtered_bars:
            return self._build_failure(contract, OutcomeState.DATA_GAP)

        # Check for gap tolerance (max 3 consecutive missing bars)
        for i in range(1, len(filtered_bars)):
            delta = filtered_bars[i].timestamp - filtered_bars[i - 1].timestamp
            if delta > 240:  # > 4 minutes (meaning > 3 missing bars)
                return self._build_failure(contract, OutcomeState.DATA_GAP)

        horizon_bars = filtered_bars[:contract.vertical_horizon_bars_1m]

        cost_info = FROZEN_COST_PARAMS[contract.cost_scenario]
        fee_slip_cost = cost_info["total_round_trip_cost_fraction"]
        risk_usd = contract.entry_price * contract.sl_multiplier * contract.sigma_t0
        cost_in_r = fee_slip_cost / (contract.sl_multiplier * contract.sigma_t0)

        # 2. Iterate bar-by-bar
        for step_idx, bar in enumerate(horizon_bars):
            hit_up = (bar.high >= contract.upper_boundary)
            hit_down = (bar.low <= contract.lower_boundary)

            # Dual touch collision
            if hit_up and hit_down:
                # Conservative tie-breaker: loss (SL)
                if contract.side == Side.LONG:
                    effective_exit = min(contract.lower_boundary, bar.open) if bar.open <= contract.lower_boundary else contract.lower_boundary
                    touch_type = "LOWER"
                else:
                    effective_exit = max(contract.upper_boundary, bar.open) if bar.open >= contract.upper_boundary else contract.upper_boundary
                    touch_type = "UPPER"

                dir_mult = 1.0 if contract.side == Side.LONG else -1.0
                g_return = dir_mult * (effective_exit - contract.entry_price) / contract.entry_price
                g_r = -1.0 if abs(effective_exit - (contract.lower_boundary if contract.side == Side.LONG else contract.upper_boundary)) < 1e-4 else (dir_mult * (effective_exit - contract.entry_price) / risk_usd)
                n_r = g_r - cost_in_r
                bps = round(g_return * 10000.0 - cost_info["total_round_trip_cost_bps"], 2)

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
                    first_touch=touch_type,
                    exit_timestamp=bar.timestamp,
                    exit_price=effective_exit,
                    same_timestamp_collision=True,
                    observed_order=None,
                    unresolved_intrabar_order=True,
                    timeout=False,
                    data_gap=False,
                    exact_boundary_touch=(bar.high == contract.upper_boundary or bar.low == contract.lower_boundary),
                    crossing_between_samples=(bar.open >= contract.upper_boundary or bar.open <= contract.lower_boundary),
                    gross_return=g_return,
                    gross_r=g_r,
                    cost_r=cost_in_r,
                    net_r=n_r,
                    outcome_state=OutcomeState.SL_FIRST,
                    realized_pnl_bps=bps,
                    path_bar_count=step_idx + 1
                )

            elif hit_up:
                effective_exit = bar.open if bar.open >= contract.upper_boundary else contract.upper_boundary
                dir_mult = 1.0 if contract.side == Side.LONG else -1.0
                g_return = dir_mult * (effective_exit - contract.entry_price) / contract.entry_price

                if contract.side == Side.LONG:
                    st = OutcomeState.TP_FIRST
                    touch_type = "UPPER"
                    g_r = contract.tp_multiplier / contract.sl_multiplier if bar.open < contract.upper_boundary else (dir_mult * (effective_exit - contract.entry_price) / risk_usd)
                else:
                    st = OutcomeState.SL_FIRST
                    touch_type = "UPPER"
                    g_r = -1.0 if bar.open < contract.upper_boundary else (dir_mult * (effective_exit - contract.entry_price) / risk_usd)

                n_r = g_r - cost_in_r
                bps = round(g_return * 10000.0 - cost_info["total_round_trip_cost_bps"], 2)

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
                    first_touch=touch_type,
                    exit_timestamp=bar.timestamp,
                    exit_price=effective_exit,
                    same_timestamp_collision=False,
                    observed_order=None,
                    unresolved_intrabar_order=False,
                    timeout=False,
                    data_gap=False,
                    exact_boundary_touch=(bar.high == contract.upper_boundary),
                    crossing_between_samples=(bar.open >= contract.upper_boundary),
                    gross_return=g_return,
                    gross_r=g_r,
                    cost_r=cost_in_r,
                    net_r=n_r,
                    outcome_state=st,
                    realized_pnl_bps=bps,
                    path_bar_count=step_idx + 1
                )

            elif hit_down:
                effective_exit = bar.open if bar.open <= contract.lower_boundary else contract.lower_boundary
                dir_mult = 1.0 if contract.side == Side.LONG else -1.0
                g_return = dir_mult * (effective_exit - contract.entry_price) / contract.entry_price

                if contract.side == Side.LONG:
                    st = OutcomeState.SL_FIRST
                    touch_type = "LOWER"
                    g_r = -1.0 if bar.open > contract.lower_boundary else (dir_mult * (effective_exit - contract.entry_price) / risk_usd)
                else:
                    st = OutcomeState.TP_FIRST
                    touch_type = "LOWER"
                    g_r = contract.tp_multiplier / contract.sl_multiplier if bar.open > contract.lower_boundary else (dir_mult * (effective_exit - contract.entry_price) / risk_usd)

                n_r = g_r - cost_in_r
                bps = round(g_return * 10000.0 - cost_info["total_round_trip_cost_bps"], 2)

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
                    first_touch=touch_type,
                    exit_timestamp=bar.timestamp,
                    exit_price=effective_exit,
                    same_timestamp_collision=False,
                    observed_order=None,
                    unresolved_intrabar_order=False,
                    timeout=False,
                    data_gap=False,
                    exact_boundary_touch=(bar.low == contract.lower_boundary),
                    crossing_between_samples=(bar.open <= contract.lower_boundary),
                    gross_return=g_return,
                    gross_r=g_r,
                    cost_r=cost_in_r,
                    net_r=n_r,
                    outcome_state=st,
                    realized_pnl_bps=bps,
                    path_bar_count=step_idx + 1
                )

        # 3. Handle Timeout
        if len(horizon_bars) < contract.vertical_horizon_bars_1m - 3:
            return self._build_failure(contract, OutcomeState.DATA_GAP)

        last_b = horizon_bars[-1]
        effective_exit = last_b.close
        dir_mult = 1.0 if contract.side == Side.LONG else -1.0
        g_return = dir_mult * (effective_exit - contract.entry_price) / contract.entry_price
        g_r = dir_mult * (effective_exit - contract.entry_price) / risk_usd
        n_r = g_r - cost_in_r
        bps = round(g_return * 10000.0 - cost_info["total_round_trip_cost_bps"], 2)

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
            exit_timestamp=last_b.timestamp,
            exit_price=effective_exit,
            same_timestamp_collision=False,
            observed_order=None,
            unresolved_intrabar_order=False,
            timeout=True,
            data_gap=False,
            exact_boundary_touch=False,
            crossing_between_samples=False,
            gross_return=g_return,
            gross_r=g_r,
            cost_r=cost_in_r,
            net_r=n_r,
            outcome_state=OutcomeState.TIMEOUT,
            realized_pnl_bps=bps,
            path_bar_count=len(horizon_bars)
        )

    def _build_failure(self, contract: TradeContract, st: OutcomeState) -> OutcomeEvent:
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
            data_gap=(st == OutcomeState.DATA_GAP),
            exact_boundary_touch=False,
            crossing_between_samples=False,
            gross_return=None,
            gross_r=None,
            cost_r=None,
            net_r=None,
            outcome_state=st,
            realized_pnl_bps=None,
            path_bar_count=0
        )
