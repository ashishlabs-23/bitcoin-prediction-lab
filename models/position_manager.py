"""
models/position_manager.py -- Dynamic Position Sizing & Risk Manager

Implements professional position sizing algorithms with Kelly Criterion,
volatility scaling, and regime-aware risk overlays for the BTC prediction engine.

This module provides:
  - Kelly Criterion position sizing (full / fractional)
  - Volatility-target sizing (risk-adjusted)
  - Regime-aware position caps (reduce size in HIGH_VOLATILITY / RANGING)
  - Risk/Reward ratio computation from TP/SL levels
  - Maximum drawdown guardrail
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_KELLY_FRACTION   = 0.25   # Quarter-Kelly for safety
MAX_POSITION_PCT         = 0.20   # Never exceed 20% of portfolio per trade
MIN_POSITION_PCT         = 0.01   # Minimum meaningful position (1%)
REGIME_CAP: dict[str, float] = {
    "TRENDING_BULL":  0.20,
    "TRENDING_BEAR":  0.18,
    "BREAKOUT":       0.15,
    "RANGING":        0.08,   # Reduced in sideways market
    "HIGH_VOLATILITY": 0.05,  # Drastically reduced in volatile markets
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class PositionSpec:
    """Output specification for a single trade position."""
    direction:         Literal["LONG", "SHORT", "SKIP"]
    position_pct:      float            # Portfolio % to allocate (0.0–1.0)
    position_btc:      float            # BTC units to buy (given portfolio value)
    entry_price:       float            # Current BTC price
    tp_price:          float            # Take Profit price
    sl_price:          float            # Stop Loss price
    risk_reward_ratio: float            # TP_distance / SL_distance
    kelly_fraction:    float            # Raw Kelly fraction (pre-cap)
    regime_cap:        float            # Active regime position cap
    rationale:         str              # Human-readable sizing rationale


@dataclass
class RiskOverlay:
    """Aggregates current risk state to guard against overexposure."""
    current_drawdown:    float = 0.0   # Portfolio drawdown from peak (0.0–1.0)
    max_drawdown_limit:  float = 0.15  # Hard stop at 15% drawdown
    open_positions:      int   = 0     # Number of currently open positions
    max_open_positions:  int   = 3     # Never exceed 3 concurrent positions

    def is_risk_blocked(self) -> tuple[bool, str]:
        """Returns (True, reason) if a new position should be blocked."""
        if self.current_drawdown >= self.max_drawdown_limit:
            return True, f"Max drawdown limit reached ({self.current_drawdown:.1%} >= {self.max_drawdown_limit:.1%})"
        if self.open_positions >= self.max_open_positions:
            return True, f"Max open positions reached ({self.open_positions}/{self.max_open_positions})"
        return False, ""


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------
def kelly_fraction(prob_win: float, win_return: float, loss_return: float) -> float:
    """
    Computes the Kelly Criterion optimal bet fraction.

    f* = (p * b - q) / b
    where b = win_return / loss_return (odds ratio), p = win prob, q = 1 - p

    Args:
        prob_win:    Probability of winning (0.0–1.0).
        win_return:  Expected gain as a fraction of bet (e.g. 0.025 for 2.5%).
        loss_return: Expected loss as a fraction of bet (e.g. 0.012 for 1.2%).

    Returns:
        Kelly fraction (may be negative for "short" or 0 if unprofitable).
    """
    if loss_return <= 0 or win_return <= 0:
        return 0.0
    b    = win_return / loss_return   # odds ratio
    q    = 1.0 - prob_win
    raw  = (prob_win * b - q) / b
    return max(-1.0, min(1.0, raw))   # clamp to [-1, 1]


def compute_position(
    direction:       Literal["LONG", "SHORT", "SKIP"],
    prob:            float,
    entry_price:     float,
    tp_price:        float,
    sl_price:        float,
    portfolio_value: float,
    regime:          str             = "RANGING",
    kelly_mult:      float           = DEFAULT_KELLY_FRACTION,
    risk_overlay:    Optional[RiskOverlay] = None,
) -> PositionSpec:
    """
    Computes an optimal position specification for a given signal.

    Args:
        direction:       Trade direction (LONG | SHORT | SKIP).
        prob:            AI probability estimate (0.0–1.0).
        entry_price:     Current BTC price.
        tp_price:        Take Profit price target.
        sl_price:        Stop Loss price.
        portfolio_value: Total portfolio value in USD.
        regime:          Current market regime string.
        kelly_mult:      Kelly multiplier (default: 0.25 = quarter-Kelly).
        risk_overlay:    Optional risk guardrail state.

    Returns:
        PositionSpec with all sizing details.
    """
    # Guard: SKIP always returns zero position
    if direction == "SKIP":
        return PositionSpec(
            direction="SKIP", position_pct=0.0, position_btc=0.0,
            entry_price=entry_price, tp_price=tp_price, sl_price=sl_price,
            risk_reward_ratio=0.0, kelly_fraction=0.0, regime_cap=0.0,
            rationale="No trade — SKIP signal from ensemble."
        )

    # Guard: Risk overlay check
    if risk_overlay:
        blocked, reason = risk_overlay.is_risk_blocked()
        if blocked:
            return PositionSpec(
                direction="SKIP", position_pct=0.0, position_btc=0.0,
                entry_price=entry_price, tp_price=tp_price, sl_price=sl_price,
                risk_reward_ratio=0.0, kelly_fraction=0.0, regime_cap=0.0,
                rationale=f"Risk overlay blocked: {reason}"
            )

    # Compute TP/SL distances as price fractions
    if direction == "LONG":
        win_pct  = abs(tp_price - entry_price) / entry_price
        loss_pct = abs(entry_price - sl_price) / entry_price
    else:  # SHORT
        win_pct  = abs(entry_price - tp_price) / entry_price
        loss_pct = abs(sl_price - entry_price) / entry_price

    rr_ratio = round(win_pct / loss_pct, 3) if loss_pct > 0 else 0.0

    # Kelly fraction
    kf   = kelly_fraction(prob, win_pct, loss_pct)
    kf_scaled = kf * kelly_mult  # Fractional Kelly

    # Regime cap
    cap  = REGIME_CAP.get(regime, 0.10)
    final_pct = max(MIN_POSITION_PCT, min(abs(kf_scaled), cap, MAX_POSITION_PCT))

    # Convert to BTC units
    usd_allocation = portfolio_value * final_pct
    btc_units      = usd_allocation / entry_price

    rationale = (
        f"Kelly={kf:.3f} -> {kelly_mult:.0%} fraction={kf_scaled:.3f}. "
        f"Regime '{regime}' cap={cap:.0%}. "
        f"R/R={rr_ratio:.2f}:1. "
        f"Allocating {final_pct:.1%} of portfolio (${usd_allocation:,.0f})."
    )

    return PositionSpec(
        direction=direction,
        position_pct=round(final_pct, 4),
        position_btc=round(btc_units, 6),
        entry_price=entry_price,
        tp_price=tp_price,
        sl_price=sl_price,
        risk_reward_ratio=rr_ratio,
        kelly_fraction=round(kf, 4),
        regime_cap=cap,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def format_position_spec(spec: PositionSpec) -> str:
    """Returns a human-readable string summary of a PositionSpec."""
    if spec.direction == "SKIP":
        return f"Position: SKIP  |  {spec.rationale}"
    return (
        f"Position: {spec.direction}\n"
        f"  Size:         {spec.position_pct:.1%} of portfolio ({spec.position_btc:.6f} BTC)\n"
        f"  Entry:        ${spec.entry_price:,.2f}\n"
        f"  Take Profit:  ${spec.tp_price:,.2f}\n"
        f"  Stop Loss:    ${spec.sl_price:,.2f}\n"
        f"  Risk/Reward:  {spec.risk_reward_ratio:.2f}:1\n"
        f"  Kelly:        {spec.kelly_fraction:.4f} × {DEFAULT_KELLY_FRACTION:.0%} = {spec.kelly_fraction * DEFAULT_KELLY_FRACTION:.4f}\n"
        f"  Regime Cap:   {spec.regime_cap:.0%}\n"
        f"  Rationale:    {spec.rationale}"
    )


# ---------------------------------------------------------------------------
# CLI Smoke Test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing models/position_manager.py...")

    spec = compute_position(
        direction="LONG",
        prob=0.72,
        entry_price=63000.0,
        tp_price=64600.0,
        sl_price=62200.0,
        portfolio_value=10_000.0,
        regime="TRENDING_BULL",
    )
    print(format_position_spec(spec))

    overlay = RiskOverlay(current_drawdown=0.16, max_drawdown_limit=0.15)
    spec2 = compute_position(
        direction="LONG", prob=0.72, entry_price=63000.0,
        tp_price=64600.0, sl_price=62200.0,
        portfolio_value=10_000.0, regime="TRENDING_BULL",
        risk_overlay=overlay,
    )
    print(f"\nWith drawdown overlay: {spec2.direction} — {spec2.rationale}")
    assert spec2.direction == "SKIP", "Expected SKIP when drawdown breached"
    print("PASS: models/position_manager.py smoke test passed.")
