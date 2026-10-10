"""
research/entry_tp_sl/barrier_contract.py
========================================
Immutable contract data structures, outcome state enums, cost parameters,
and pre-registered barrier configurations for the Entry/TP/SL Research Track.

Status: FROZEN ARCHITECTURE (Phase 6A/6B)
Resolver Version: ENTRY_TP_SL_RESOLVER_V1
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
import math

RESOLVER_VERSION = "ENTRY_TP_SL_RESOLVER_V1"


class OutcomeState(str, Enum):
    TP_FIRST = "TP_FIRST"
    SL_FIRST = "SL_FIRST"
    TIMEOUT = "TIMEOUT"
    UNRESOLVED_INTRABAR = "UNRESOLVED_INTRABAR"
    DATA_GAP = "DATA_GAP"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    PROVENANCE_FAILURE = "PROVENANCE_FAILURE"
    INVALID_CONTRACT = "INVALID_CONTRACT"


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class CostScenario(str, Enum):
    BASE = "BASE"
    CONSERVATIVE = "CONSERVATIVE"


FROZEN_COST_PARAMS = {
    CostScenario.BASE: {
        "entry_taker_fee_bps": 10.0,
        "exit_taker_fee_bps": 10.0,
        "entry_slippage_bps": 5.0,
        "exit_slippage_bps": 5.0,
        "half_spread_bps": 2.5,
        "total_round_trip_cost_bps": 35.0,
        "total_round_trip_cost_fraction": 0.0035
    },
    CostScenario.CONSERVATIVE: {
        "entry_taker_fee_bps": 15.0,
        "exit_taker_fee_bps": 15.0,
        "entry_slippage_bps": 10.0,
        "exit_slippage_bps": 15.0,
        "half_spread_bps": 5.0,
        "total_round_trip_cost_bps": 65.0,
        "total_round_trip_cost_fraction": 0.0065
    }
}

FROZEN_BARRIER_GRID = {
    "barrier_pair_01": {
        "pair_id": "barrier_pair_01",
        "role": "PRIMARY_REFERENCE",
        "tp_multiplier": 1.0,
        "sl_multiplier": 1.0,
        "vertical_horizon_minutes": 240,
        "vertical_horizon_bars_1m": 240,
        "target_rr_ratio": 1.0
    },
    "barrier_pair_02": {
        "pair_id": "barrier_pair_02",
        "role": "CONFIRMATORY_SECONDARY",
        "tp_multiplier": 1.5,
        "sl_multiplier": 1.0,
        "vertical_horizon_minutes": 240,
        "vertical_horizon_bars_1m": 240,
        "target_rr_ratio": 1.5
    },
    "barrier_pair_03": {
        "pair_id": "barrier_pair_03",
        "role": "CONFIRMATORY_SECONDARY",
        "tp_multiplier": 2.0,
        "sl_multiplier": 1.0,
        "vertical_horizon_minutes": 240,
        "vertical_horizon_bars_1m": 240,
        "target_rr_ratio": 2.0
    },
    "barrier_pair_04": {
        "pair_id": "barrier_pair_04",
        "role": "CONFIRMATORY_SECONDARY_TIGHT",
        "tp_multiplier": 0.75,
        "sl_multiplier": 0.75,
        "vertical_horizon_minutes": 120,
        "vertical_horizon_bars_1m": 120,
        "target_rr_ratio": 1.0
    },
    "barrier_pair_05": {
        "pair_id": "barrier_pair_05",
        "role": "CONFIRMATORY_SECONDARY_WIDE",
        "tp_multiplier": 2.0,
        "sl_multiplier": 1.5,
        "vertical_horizon_minutes": 240,
        "vertical_horizon_bars_1m": 240,
        "target_rr_ratio": 1.3333
    }
}


@dataclass(frozen=True)
class PathBar:
    """Represents a discrete 1-minute OHLCV bar."""
    timestamp: int  # Unix seconds at interval close
    open: float
    high: float
    low: float
    close: float
    volume: float

    def validate(self) -> bool:
        if self.timestamp <= 0:
            return False
        if any(math.isnan(v) or math.isinf(v) or v <= 0 for v in (self.open, self.high, self.low, self.close)):
            return False
        if self.volume < 0 or math.isnan(self.volume) or math.isinf(self.volume):
            return False
        if self.high < self.low or self.high < self.open or self.high < self.close or self.low > self.open or self.low > self.close:
            return False
        return True


@dataclass(frozen=True)
class TradeContract:
    """
    Immutable specification of a single trade opportunity at entry.
    All parameters are strictly determined at t0 and never altered.
    """
    pair_id: str
    decision_timestamp: int
    entry_timestamp: int
    fill_timestamp: int
    side: Side
    entry_price: float
    upper_boundary: float
    lower_boundary: float
    vertical_horizon_minutes: int
    vertical_horizon_bars_1m: int
    tp_multiplier: float
    sl_multiplier: float
    sigma_t0: float
    cost_scenario: CostScenario = CostScenario.BASE
    resolver_version: str = RESOLVER_VERSION

    @property
    def one_r_usd(self) -> float:
        """Nominal 1R risk in USD per unit."""
        return self.entry_price * self.sl_multiplier * self.sigma_t0


@dataclass(frozen=True)
class OutcomeEvent:
    """
    Complete, auditable record of a resolved trade outcome.
    Strictly follows schema invariants: UNOBSERVABLE = None, OBSERVED_ZERO = 0.0.
    """
    resolver_version: str
    pair_id: str
    decision_timestamp: int
    entry_timestamp: int
    fill_timestamp: int
    side: Side
    entry_price: float
    upper_boundary: float
    lower_boundary: float
    vertical_horizon_minutes: int
    first_touch: Optional[str]  # "UPPER", "LOWER", "VERTICAL_TIMEOUT", or None
    exit_timestamp: Optional[int]
    exit_price: Optional[float]
    same_timestamp_collision: bool
    observed_order: Optional[str]  # "UPPER_FIRST", "LOWER_FIRST", or None
    unresolved_intrabar_order: bool
    timeout: bool
    data_gap: bool
    exact_boundary_touch: bool
    crossing_between_samples: bool
    gross_return: Optional[float]
    gross_r: Optional[float]
    cost_r: Optional[float]
    net_r: Optional[float]
    outcome_state: OutcomeState
    realized_pnl_bps: Optional[float]
    path_bar_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolver_version": self.resolver_version,
            "pair_id": self.pair_id,
            "decision_timestamp": self.decision_timestamp,
            "entry_timestamp": self.entry_timestamp,
            "fill_timestamp": self.fill_timestamp,
            "side": self.side.value if isinstance(self.side, Side) else str(self.side),
            "entry_price": self.entry_price,
            "upper_boundary": self.upper_boundary,
            "lower_boundary": self.lower_boundary,
            "vertical_horizon_minutes": self.vertical_horizon_minutes,
            "first_touch": self.first_touch,
            "exit_timestamp": self.exit_timestamp,
            "exit_price": self.exit_price,
            "same_timestamp_collision": self.same_timestamp_collision,
            "observed_order": self.observed_order,
            "unresolved_intrabar_order": self.unresolved_intrabar_order,
            "timeout": self.timeout,
            "data_gap": self.data_gap,
            "exact_boundary_touch": self.exact_boundary_touch,
            "crossing_between_samples": self.crossing_between_samples,
            "gross_return": self.gross_return,
            "gross_r": self.gross_r,
            "cost_r": self.cost_r,
            "net_r": self.net_r,
            "outcome_state": self.outcome_state.value if isinstance(self.outcome_state, OutcomeState) else str(self.outcome_state),
            "realized_pnl_bps": self.realized_pnl_bps,
            "path_bar_count": self.path_bar_count
        }
