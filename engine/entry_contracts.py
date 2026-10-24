"""
engine/entry_contracts.py — Typed, Immutable Contracts for BTC Entry Lab
========================================================================
Defines strict, immutable data structures and validation logic for:
1. CandidateSetup: A prospective point-in-time entry candidate generated at decision timestamp t0.
2. ResolutionOutcome: The deterministic, conservative resolution of a triple-barrier excursion.

Invariants:
- All timestamp boundaries must be ISO-8601 UTC strings.
- Features and setup specifications are frozen at t0 (strictly before fill timestamp t_fill).
- Barrier geometry is explicitly validated:
    LONG:  tp_price > entry_price and sl_price < entry_price
    SHORT: tp_price < entry_price and sl_price > entry_price
- Intrabar collision (both TP and SL touched within the same bar) requires conservative SL_FIRST
  resolution with is_ambiguous_touch=True. One-minute bars CANNOT prove sub-minute order.
- Analysis-only status: execution_authorization is permanently DISABLED.
"""

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


def compute_candidate_id(
    strategy_archetype: str,
    direction: str,
    decision_timestamp_utc: str,
    entry_price: float,
    tp_price: float,
    sl_price: float,
    horizon_bars: int
) -> str:
    """Computes a deterministic, collision-resistant candidate setup ID."""
    payload = f"{strategy_archetype}:{direction.upper()}:{decision_timestamp_utc}:{entry_price:.2f}:{tp_price:.2f}:{sl_price:.2f}:{horizon_bars}"
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"cand_{sha[:16]}"


@dataclass(frozen=True)
class CandidateSetup:
    """
    Immutable candidate setup specification emitted at decision time t0.
    Frozen to prevent post-decision mutation or lookahead leakage.
    """
    candidate_id: str
    strategy_archetype: str
    direction: str  # "LONG" or "SHORT"
    instrument_id: str  # e.g. "BTC-USD"
    venue: str  # e.g. "COINBASE", "BINANCE_FUTURES"
    market_type: str  # "SPOT" or "PERPETUAL"
    decision_timestamp_utc: str
    fill_timestamp_utc: str
    entry_reference_price: float
    proposed_entry_price: float
    take_profit_price: float
    stop_loss_price: float
    k_tp: float
    k_sl: float
    horizon_bars: int
    sigma_at_t0: float
    risk_unit_usd: float
    cost_scenario: str
    round_trip_friction_bps: float
    friction_r: float
    p_tp: float
    p_sl: float
    p_timeout: float
    expected_gross_r: float
    expected_net_r: float
    features_hash: str
    model_version: str = "ENTRY_TP_SL_V1"
    execution_authorization: str = "DISABLED — ANALYSIS ONLY"
    governance_status: str = "OFFLINE_RESEARCH_ONLY"

    def __post_init__(self):
        """Validate causal and geometric consistency upon instantiation."""
        dir_upper = self.direction.upper()
        if dir_upper not in ("LONG", "SHORT", "CASH"):
            raise ValueError(f"Invalid direction '{self.direction}'; must be 'LONG', 'SHORT', or 'CASH'.")

        if self.proposed_entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {self.proposed_entry_price}.")
        if self.take_profit_price <= 0 or self.stop_loss_price <= 0:
            raise ValueError("Barrier prices must be strictly positive.")

        if dir_upper == "LONG":
            if not (self.take_profit_price > self.proposed_entry_price > self.stop_loss_price):
                raise ValueError(
                    f"Invalid LONG barrier geometry: require TP ({self.take_profit_price}) > "
                    f"Entry ({self.proposed_entry_price}) > SL ({self.stop_loss_price})."
                )
        elif dir_upper == "SHORT":
            if not (self.take_profit_price < self.proposed_entry_price < self.stop_loss_price):
                raise ValueError(
                    f"Invalid SHORT barrier geometry: require TP ({self.take_profit_price}) < "
                    f"Entry ({self.proposed_entry_price}) < SL ({self.stop_loss_price})."
                )
        elif dir_upper == "CASH":
            # Defensive Cash Hold: No barrier excursion permitted on spot
            pass

        if self.horizon_bars <= 0:
            raise ValueError(f"Horizon bars must be >= 1, got {self.horizon_bars}.")

        if not (self.fill_timestamp_utc >= self.decision_timestamp_utc):
            raise ValueError(
                f"Causal violation: fill timestamp ({self.fill_timestamp_utc}) cannot precede "
                f"decision timestamp ({self.decision_timestamp_utc})."
            )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CandidateSetup":
        return cls(**data)


@dataclass(frozen=True)
class ResolutionOutcome:
    """
    Immutable outcome record for a resolved candidate setup excursion.
    """
    candidate_id: str
    exit_timestamp_utc: str
    exit_price: float
    exit_reason: str  # "TP_FIRST", "SL_FIRST", "TIMEOUT", "INTRABAR_COLLISION_RESOLVED_SL"
    bars_held: int
    gross_return_r: float
    net_return_r: float
    mfe_r: float
    mae_r: float
    is_ambiguous_touch: bool
    ambiguity_reason: Optional[str]
    cost_scenario: str
    round_trip_friction_bps: float
    friction_r: float
    resolver_version: str = "DETERMINISTIC_BARRIER_RESOLVER_V1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResolutionOutcome":
        return cls(**data)
