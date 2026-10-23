"""
models/signal_contract.py — BTCognitive Authoritative Signal & Scenario Contract
================================================================================
Defines the single authoritative schema, invariants, and validation rules for
research-only directional signals, scenario levels, probability calibration,
and risk-reward geometry.

Epistemic Invariants:
1. Canonical Volatility Target Separation: HAR-RS-DOW-v1.0 (168h rv7d_var_ann)
   never produces directional signals, trade entries, or TP/SL levels.
2. Gated/Abstaining Models: If direction is NONE, NEUTRAL, or NOT_ESTIMATED, or
   if model status is GATED, no actionable entry, TP, or SL scenario is rendered.
3. Level Geometry:
   - For LONG:  SL < entry < TP. Risk = entry - SL > 0, Reward = TP - entry > 0.
   - For SHORT: TP < entry < SL. Risk = SL - entry > 0, Reward = entry - TP > 0.
   - Gross R:R = Reward / Risk.
   - Net R:R accounts for estimated round-trip execution costs.
4. Probability Calibration: Event probabilities must specify target event and
   horizon. Raw model scores must never be labeled as calibrated conviction percentages.
5. Non-Execution: Live trading and automated execution remain permanently DISABLED.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, model_validator


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    ABSTAIN = "ABSTAIN"
    NOT_ESTIMATED = "NOT_ESTIMATED"
    NEUTRAL = "NEUTRAL"


class SignalStatus(str, Enum):
    ACTIVE_CANDIDATE = "ACTIVE_CANDIDATE"
    ACTIVE = "ACTIVE"
    ABSTAINED = "ABSTAINED"
    ABSTAIN = "ABSTAIN"
    GATED = "GATED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    NOT_ESTIMATED = "NOT_ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"


class CalibrationStatus(str, Enum):
    CALIBRATED_ISOTONIC = "CALIBRATED_ISOTONIC"
    CALIBRATED_PLATT = "CALIBRATED_PLATT"
    CALIBRATED_CONFORMAL = "CALIBRATED_CONFORMAL"
    CALIBRATED = "CALIBRATED"
    UNCALIBRATED_RAW_SCORE = "UNCALIBRATED_RAW_SCORE"
    UNAVAILABLE = "UNAVAILABLE"


class EntryType(str, Enum):
    CURRENT_MARKET_REFERENCE = "CURRENT_MARKET_REFERENCE"
    MARKET_REFERENCE = "MARKET_REFERENCE"
    LIMIT_ENTRY_HYPOTHESIS = "LIMIT_ENTRY_HYPOTHESIS"
    STOP_ENTRY_HYPOTHESIS = "STOP_ENTRY_HYPOTHESIS"
    NO_ENTRY_ABSTAIN = "NO_ENTRY_ABSTAIN"


class ExecutionAuthorization(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    DISABLED = "DISABLED"


class SignalContract(BaseModel):
    """Authoritative Signal & Scenario Contract for BTCognitive."""
    
    # Identification
    signal_id: str = Field(..., description="Unique deterministic signal/scenario UUID")
    scenario_id: Optional[str] = Field(None, description="Scenario instance ID")
    generated_at: str = Field(..., description="ISO 8601 UTC timestamp of signal generation")
    valid_until: str = Field(..., description="ISO 8601 UTC timestamp of signal validity expiration")
    
    # Market & Instrument Identity
    instrument: str = Field(default="BTC-USD", description="Canonical instrument symbol")
    exchange: str = Field(default="Coinbase", description="Execution reference venue")
    market_type: str = Field(default="SPOT", description="Market product type: SPOT or PERPETUAL")
    quote_currency: str = Field(default="USD", description="Quote currency")
    reference_price: float = Field(..., gt=0.0, description="Live spot reference price at signal issue")
    bid: Optional[float] = Field(None, description="Current market bid price")
    ask: Optional[float] = Field(None, description="Current market ask price")
    price_timestamp: str = Field(..., description="Timestamp of market reference price")
    data_freshness: str = Field(default="FRESH", description="Data stream freshness: FRESH, DEGRADED, STALE")
    data_freshness_seconds: Optional[float] = Field(None, description="Age of data stream in seconds")
    
    # Horizons
    chart_interval: str = Field(default="1h", description="Display chart interval")
    signal_horizon: str = Field(default="15m", description="Evaluation and holding horizon")
    maximum_holding_period: str = Field(default="15m", description="Maximum holding period before vertical timeout")
    
    # Directional Signal & Governance
    direction: SignalDirection = Field(default=SignalDirection.ABSTAIN, description="Target signal direction")
    signal_status: SignalStatus = Field(default=SignalStatus.ABSTAINED, description="Authoritative signal lifecycle state")
    signal_type: str = Field(default="RESEARCH_SCENARIO", description="RESEARCH_SCENARIO or BENCHMARK_NULL")
    model_id: str = Field(..., description="Predicting model canonical ID")
    model_version: str = Field(default="v1.0", description="Model version")
    model_authorization: str = Field(default="OFFLINE_RESEARCH_ONLY", description="Governance authorization scope")
    execution_authorization: ExecutionAuthorization = Field(default=ExecutionAuthorization.DISABLED, description="Execution venue authorization: strictly DISABLED")
    
    # Probability & Calibration
    event_probability: Optional[float] = Field(None, ge=0.0, le=1.0, description="Calibrated probability of target event")
    probability_target: Optional[str] = Field(None, description="Explicit target event definition (e.g. TP_BEFORE_SL)")
    probability_horizon: Optional[str] = Field(None, description="Target probability horizon")
    calibration_status: CalibrationStatus = Field(default=CalibrationStatus.UNAVAILABLE, description="Calibration methodology")
    calibration_evidence: Optional[Dict[str, Any]] = Field(None, description="Calibration diagnostics: Brier score, ECE, N_eff")
    
    # Scenario Levels & Risk Mathematics
    entry_type: EntryType = Field(default=EntryType.NO_ENTRY_ABSTAIN, description="Entry order hypothesis type")
    entry_price: Optional[float] = Field(None, description="Scenario entry price")
    entry_condition: Optional[str] = Field(None, description="Pre-condition for entry activation")
    take_profit: Optional[float] = Field(None, description="Scenario take-profit boundary price")
    stop_loss: Optional[float] = Field(None, description="Scenario stop-loss boundary price")
    
    # Mathematical Geometry
    risk_distance: Optional[float] = Field(None, ge=0.0, description="Distance from entry to stop loss (|entry - SL|)")
    reward_distance: Optional[float] = Field(None, ge=0.0, description="Distance from entry to take profit (|TP - entry|)")
    gross_reward_to_risk: Optional[float] = Field(None, ge=0.0, description="Gross reward-to-risk ratio: reward_distance / risk_distance")
    estimated_costs: Optional[Dict[str, Any]] = Field(None, description="Breakdown of exchange fees, spread, slippage, and funding")
    net_expected_value: Optional[float] = Field(None, description="Expected net utility after all costs in basis points")
    net_reward_to_risk: Optional[float] = Field(None, description="Cost-adjusted net reward-to-risk ratio")
    
    # Invalidation & Lineage
    invalidation_reason: Optional[str] = Field(None, description="Reason code if scenario is abstained or invalidated")
    feature_hash: Optional[str] = Field(None, description="Cryptographic SHA-256 hash of input feature vector")
    data_snapshot_id: Optional[str] = Field(None, description="Point-in-time data snapshot identifier")
    provenance: Optional[Dict[str, Any]] = Field(None, description="Complete audit lineage metadata")

    def is_expired(self) -> bool:
        """Returns True if current UTC time exceeds valid_until."""
        try:
            vu = datetime.fromisoformat(self.valid_until.replace("Z", "+00:00"))
            if vu.tzinfo is None:
                vu = vu.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > vu
        except Exception:
            return False

    @model_validator(mode="after")
    def validate_scenario_geometry_and_state(self):
        """Enforces mathematical consistency and side-specific level invariants."""
        # Rule 1: Abstention / Inactive cases must not expose actionable TP/SL levels
        if self.direction in [SignalDirection.ABSTAIN, SignalDirection.NOT_ESTIMATED, SignalDirection.NEUTRAL] or \
           self.signal_status in [SignalStatus.ABSTAINED, SignalStatus.GATED, SignalStatus.NOT_ESTIMATED, SignalStatus.UNAVAILABLE]:
            self.entry_price = None
            self.take_profit = None
            self.stop_loss = None
            self.risk_distance = None
            self.reward_distance = None
            self.gross_reward_to_risk = None
            self.net_reward_to_risk = None
            if not self.invalidation_reason:
                self.invalidation_reason = "DIRECTION_ABSTAINED_OR_GATED"
            return self

        # Rule 2: Active scenarios must have positive, finite prices
        if self.entry_price is None or self.take_profit is None or self.stop_loss is None:
            raise ValueError("Active signal candidate requires entry_price, take_profit, and stop_loss.")

        if self.entry_price <= 0 or self.take_profit <= 0 or self.stop_loss <= 0:
            raise ValueError(f"Prices must be strictly positive: entry={self.entry_price}, TP={self.take_profit}, SL={self.stop_loss}")

        # Rule 3: Side-specific bracket checks
        if self.direction == SignalDirection.LONG:
            if not (self.stop_loss < self.entry_price < self.take_profit):
                raise ValueError(
                    f"Long bracket invalid: must satisfy SL ({self.stop_loss}) < entry ({self.entry_price}) < TP ({self.take_profit})"
                )
            computed_risk = round(self.entry_price - self.stop_loss, 4)
            computed_reward = round(self.take_profit - self.entry_price, 4)
        elif self.direction == SignalDirection.SHORT:
            if not (self.take_profit < self.entry_price < self.stop_loss):
                raise ValueError(
                    f"Short bracket invalid: must satisfy TP ({self.take_profit}) < entry ({self.entry_price}) < SL ({self.stop_loss})"
                )
            computed_risk = round(self.stop_loss - self.entry_price, 4)
            computed_reward = round(self.entry_price - self.take_profit, 4)
        else:
            raise ValueError(f"Unsupported direction for active scenario: {self.direction}")

        if computed_risk <= 0:
            raise ValueError(f"Non-positive risk distance: {computed_risk}")
        if computed_reward <= 0:
            raise ValueError(f"Non-positive reward distance: {computed_reward}")

        self.risk_distance = computed_risk
        self.reward_distance = computed_reward
        self.gross_reward_to_risk = round(computed_reward / computed_risk, 4)

        # Reconcile net R:R if costs available
        if self.estimated_costs and "total_cost_distance" in self.estimated_costs:
            cost_dist = float(self.estimated_costs["total_cost_distance"])
            net_reward = max(0.0, computed_reward - cost_dist)
            net_risk = computed_risk + cost_dist
            self.net_reward_to_risk = round(net_reward / net_risk, 4) if net_risk > 0 else 0.0

        return self


def validate_scenario_geometry(direction: str, entry: float, tp: float, sl: float) -> Dict[str, Any]:
    """Helper to validate entry/tp/sl geometry without constructing a full model."""
    dir_u = str(direction).upper()
    if dir_u == "LONG":
        if not (sl < entry < tp):
            return {"is_valid": False, "error_code": "INVERTED_LEVELS_OR_INVALID_ORDER"}
        risk = entry - sl
        reward = tp - entry
    elif dir_u == "SHORT":
        if not (tp < entry < sl):
            return {"is_valid": False, "error_code": "INVERTED_LEVELS_OR_INVALID_ORDER"}
        risk = sl - entry
        reward = entry - tp
    else:
        return {"is_valid": False, "error_code": "UNSUPPORTED_DIRECTION"}

    if risk <= 0:
        return {"is_valid": False, "error_code": "ZERO_OR_NEGATIVE_RISK"}
    if reward <= 0:
        return {"is_valid": False, "error_code": "ZERO_OR_NEGATIVE_REWARD"}

    return {
        "is_valid": True,
        "reward_distance": reward,
        "risk_distance": risk,
        "gross_rr": round(reward / risk, 4)
    }


def create_abstain_signal(
    model_id: str = "HAR-RS-DOW-v1.0",
    reference_price: float = 81440.0,
    reason_code: Optional[str] = None,
    reason: Optional[str] = None,
    instrument: str = "BTC-USD",
    exchange: str = "Coinbase",
    market_type: str = "SPOT",
    quote_currency: str = "USD",
    horizon: str = "15m",
    price_timestamp: Optional[str] = None,
    **kwargs: Any
) -> SignalContract:
    """Helper creating a standardized, immutable ABSTAIN signal contract."""
    now_iso = datetime.now(timezone.utc).isoformat()
    eff_reason = reason or reason_code or "ABSTAINED"
    return SignalContract(
        signal_id=f"sig_abstain_{int(datetime.now(timezone.utc).timestamp())}",
        generated_at=now_iso,
        valid_until=now_iso,
        instrument=instrument,
        exchange=exchange,
        market_type=market_type,
        quote_currency=quote_currency,
        reference_price=round(reference_price, 2) if reference_price and reference_price > 0 else 81440.0,
        price_timestamp=price_timestamp or now_iso,
        signal_horizon=horizon,
        maximum_holding_period=horizon,
        direction=SignalDirection.ABSTAIN,
        signal_status=SignalStatus.ABSTAIN,
        model_id=model_id,
        execution_authorization=ExecutionAuthorization.DISABLED,
        invalidation_reason=eff_reason,
        calibration_status=CalibrationStatus.UNAVAILABLE,
        entry_type=EntryType.NO_ENTRY_ABSTAIN
    )
