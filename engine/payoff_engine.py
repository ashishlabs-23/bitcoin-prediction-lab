"""
engine/payoff_engine.py — MEIE Layer 3: Conditional Payoff Distribution & Net EV
==================================================================================
Given a detected event and current market state, estimates:
  - E[MFE | state]  — expected favorable excursion
  - E[MAE | state]  — expected adverse excursion
  - P(TP) / P(SL)   — hit probability using empirical directional accuracy
  - EV_net (bps)    — gross edge minus full execution cost
  - execute: bool   — True only when EV_net > 0 AND no execution risk blockers

Design constraints (Ponytail):
  - Wraps EXISTING RangeForecastService (no new math on MFE/MAE).
  - Wraps EXISTING ExecutionSimulator (no new cost model).
  - EV_net > 0 is the PRIMARY gate (per MEIE-EXECUTION-01-v1.0 preregistration).
  - DSR is NOT computed here — it's a post-hoc diagnostic only.
  - Execution is blocked by VACUUM or extreme VPIN/spread (hidden liquidity risk).

Preregistration reference: results/meie_execution01_preregistration.md (MEIE-EXECUTION-01-v1.0)
"""

import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Tuple

from engine.event_detector import DetectedEvent, MarketEvent, EventDirection
from engine.microstructure_state import MicrostructureStateVector
from engine.range_forecast_service import RangeForecastService
from backtest.execution_simulator import ExecutionSimulator

logger = logging.getLogger("btcognitive.payoff_engine")

# Shared instances (reuse existing singletons)
_range_svc = RangeForecastService(default_horizon="15m")
_exec_sim   = ExecutionSimulator(fee_tier="taker", taker_fee_bps=5.0, base_slippage_bps=2.0)

# ---------------------------------------------------------------------------
# Locked execution-risk blockers
# Source: results/meie_execution01_preregistration.md — MEIE-EXECUTION-01-v1.0
# ---------------------------------------------------------------------------
_EXEC_RISK_THRESHOLDS = {
    "block_z_vpin_extreme":  2.5,   # Hidden liquidity risk (2026 SSRN study)
    "block_z_spread_extreme": 2.0,  # Spread too wide for profitable fill
    "min_risk_reward":       1.5,   # TP_dist / SL_dist minimum
    "ev_net_floor_bps":      0.0,   # Primary gate: EV_net > 0
    "fee_total_bps":        10.0,   # Fixed: 5 bps entry + 5 bps exit taker
}


@dataclass
class PayoffEstimate:
    """Full payoff distribution estimate for one candidate trade."""
    timestamp: str
    event_type: str
    direction: str
    price: float

    # Excursion envelope from RangeForecastService
    mfe_p50: float      # Median favorable excursion (fraction, e.g. 0.012 = 1.2%)
    mae_p25: float      # 25th-pct adverse excursion (tighter SL per preregistration)
    tp_dist_bps: float  # mfe_p50 * 10000
    sl_dist_bps: float  # mae_p25 * 10000

    # Probability estimates
    p_tp: float         # Estimated P(TP hit before SL)
    p_sl: float         # 1 - p_tp

    # Gross and net economics
    gross_edge_bps: float       # p_tp * tp_dist - p_sl * sl_dist
    fee_bps: float              # always 10.0 (per preregistration)
    slippage_bps: float         # VPIN-aware from ExecutionSimulator
    ev_net_bps: float           # gross_edge - fee - slippage

    # Opportunity Quality (OQ) Metric
    opportunity_quality: float   # EV_net / (Expected MAE + eps) - penalties
    opportunity_category: str    # IGNORE | WATCH | PAPER_CANDIDATE | HIGH_QUALITY_CANDIDATE

    # Contract Specification
    target_rr: float             # Target R:R ratio (e.g. 2.00)
    max_hold_bars: int           # Hard timeout in bars (1m each)
    impact_bps: float            # Expected market impact

    # Decision
    execute: bool               # True only if EV_net > 0 and no blockers active
    block_reason: str           # Empty if execute=True

    # Proposed levels
    tp_price: float
    sl_price: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# P(TP) estimation
# ---------------------------------------------------------------------------

def _estimate_p_tp(direction: EventDirection, empirical_hit_rate: Optional[float] = None) -> float:
    """
    Uses empirical directional accuracy from MEIE-DIRECTION-01 if available.
    Falls back to 0.50 (no edge assumed) before sufficient data accumulates.
    This conservative default means gross_edge will be near zero early on → EV_net < 0 → ABSTAIN.
    That is the correct behaviour before the experiment proves directional accuracy.
    """
    if empirical_hit_rate is not None and 0.0 < empirical_hit_rate < 1.0:
        return float(empirical_hit_rate)
    return 0.50  # Conservative prior: no edge assumed


def _execution_blocked(sv: MicrostructureStateVector, event: DetectedEvent) -> str:
    """
    Returns block reason string if execution should be blocked, empty string otherwise.
    Per MEIE-EXECUTION-01-v1.0 section 2.4: blocks override positive EV.
    """
    th = _EXEC_RISK_THRESHOLDS
    if event.event_type == MarketEvent.VACUUM:
        return "VACUUM: liquidity collapse — execution blocked"
    if sv.z_vpin >= th["block_z_vpin_extreme"]:
        return f"VPIN extreme (z={sv.z_vpin:.2f} >= {th['block_z_vpin_extreme']})"
    if sv.z_spread >= th["block_z_spread_extreme"]:
        return f"Spread extreme (z={sv.z_spread:.2f} >= {th['block_z_spread_extreme']})"
    return ""


def compute_opportunity_quality(
    ev_net_bps: float,
    expected_mae_bps: float,
    data_quality: str = "VALID",
    z_spread: float = 0.0,
    is_ambiguous: bool = False,
) -> Tuple[float, str]:
    """
    Computes Opportunity Quality (OQ) = EV_net / (Expected MAE + eps) - penalties.
    Categories:
      < 0.25: IGNORE
      0.25 - 0.50: WATCH
      0.50 - 1.00: PAPER_CANDIDATE
      >= 1.00: HIGH_QUALITY_CANDIDATE
    """
    if ev_net_bps <= 0:
        return 0.0, "IGNORE"

    raw_oq = ev_net_bps / max(1.0, expected_mae_bps)

    # Penalties
    penalties = 0.0
    if data_quality == "DEGRADED":
        penalties += 0.15
    if abs(z_spread) > 1.0:
        penalties += 0.10
    if is_ambiguous:
        penalties += 0.25

    oq = round(max(0.0, raw_oq - penalties), 4)

    if oq >= 1.00:
        cat = "HIGH_QUALITY_CANDIDATE"
    elif oq >= 0.50:
        cat = "PAPER_CANDIDATE"
    elif oq >= 0.25:
        cat = "WATCH"
    else:
        cat = "IGNORE"

    return oq, cat


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def estimate_payoff(
    event: DetectedEvent,
    vol_24h: float = 0.015,
    features: Optional[Dict[str, Any]] = None,
    position_size_usd: float = 100.0,
    empirical_hit_rate: Optional[float] = None,
) -> PayoffEstimate:
    """
    Estimates the full conditional payoff distribution for a candidate trade.
    Enforces archetype-specific TP/SL geometry and max hold bounds:
      - IGNITION:   Target 2.0R (asymmetric momentum), T_max = 30m
      - ABSORPTION: Target 1.2R (mean reversion mid),  T_max = 20m
      - VACUUM:     Target 1.5R (fast sweep),          T_max = 10m
    """
    sv = event.state
    price = sv.price
    direction = event.direction
    event_str = event.event_type.value

    # Archetype-specific geometry scaling
    if event_str == "IGNITION":
        tp_scale = 2.0
        sl_scale = 1.0
        max_hold_bars = 30
    elif event_str == "ABSORPTION":
        tp_scale = 1.2
        sl_scale = 1.0
        max_hold_bars = 20
    elif event_str == "VACUUM":
        tp_scale = 1.5
        sl_scale = 0.8
        max_hold_bars = 10
    else:
        tp_scale = 1.5
        sl_scale = 1.0
        max_hold_bars = 30

    # Step 1: Get excursion envelope from existing RangeForecastService
    try:
        fc = _range_svc.generate_forecast(
            current_price=price,
            vol_24h=vol_24h,
            features=features,
            market_regime="Unknown",
        )
        mfe_p50 = fc.mfe_p50
        mae_p25 = fc.mae_p25
    except Exception as e:
        logger.warning(f"RangeForecastService failed: {e}. Using vol-based fallback.")
        mfe_p50 = vol_24h * 0.85
        mae_p25 = vol_24h * 0.65

    effective_mfe = mfe_p50 * tp_scale
    effective_mae = mae_p25 * sl_scale
    tp_dist_bps = effective_mfe * 10_000.0
    sl_dist_bps = effective_mae * 10_000.0
    target_rr = round(tp_dist_bps / max(0.01, sl_dist_bps), 2)

    # Step 2a: Execution risk blockers — these override all economic checks
    block_reason = _execution_blocked(sv, event)
    if block_reason:
        return _build_abstain(event, effective_mfe, effective_mae, tp_dist_bps, sl_dist_bps,
                              price, direction, block_reason, target_rr, max_hold_bars)

    # Step 2b: Risk-reward check (per preregistration: must be ≥ 1.5)
    rr = tp_dist_bps / max(0.01, sl_dist_bps)
    if rr < _EXEC_RISK_THRESHOLDS["min_risk_reward"] and event_str != "ABSORPTION":
        block_reason = f"Risk-reward {rr:.2f} < {_EXEC_RISK_THRESHOLDS['min_risk_reward']}"
        return _build_abstain(event, effective_mfe, effective_mae, tp_dist_bps, sl_dist_bps,
                              price, direction, block_reason, target_rr, max_hold_bars)

    # Step 3: P(TP) estimate
    p_tp = _estimate_p_tp(direction, empirical_hit_rate)
    p_sl = 1.0 - p_tp

    # Step 4: Gross edge
    gross_edge_bps = p_tp * tp_dist_bps - p_sl * sl_dist_bps

    # Step 5: Execution costs from existing ExecutionSimulator
    exec_result = _exec_sim.execute_order(
        side="BUY" if direction == EventDirection.LONG else "SELL",
        price=price,
        order_size_usdt=position_size_usd,
        bid_ask_spread_pct=sv.raw_spread,
        vpin=sv.raw_vpin,
        is_maker=False
    )
    slippage_bps = exec_result.get("slippage_cost", 0.0) / max(1.0, position_size_usd) * 10_000.0
    slippage_bps = round(float(slippage_bps), 2)
    impact_bps = round(float(exec_result.get("impact_cost", 1.0)), 2)

    fee_bps = _EXEC_RISK_THRESHOLDS["fee_total_bps"]
    ev_net_bps = gross_edge_bps - fee_bps - slippage_bps

    # Step 6: Opportunity Quality (OQ) Metric
    oq, oq_category = compute_opportunity_quality(
        ev_net_bps=ev_net_bps,
        expected_mae_bps=sl_dist_bps,
        data_quality=sv.data_quality,
        z_spread=sv.z_spread,
        is_ambiguous=(direction == EventDirection.AMBIGUOUS),
    )

    # Step 7: Primary gate per MEIE-EXECUTION-01-v1.0
    block_reason = ""
    execute = (
        ev_net_bps > _EXEC_RISK_THRESHOLDS["ev_net_floor_bps"] and
        direction != EventDirection.AMBIGUOUS and
        sv.data_quality != "INSUFFICIENT"
    )

    if execute:
        if direction == EventDirection.LONG:
            tp_price = round(price * (1.0 + effective_mfe), 2)
            sl_price = round(price * (1.0 - effective_mae), 2)
        else:
            tp_price = round(price * (1.0 - effective_mfe), 2)
            sl_price = round(price * (1.0 + effective_mae), 2)
    else:
        tp_price = sl_price = price

    return PayoffEstimate(
        timestamp=event.timestamp,
        event_type=event.event_type.value,
        direction=direction.value,
        price=price,
        mfe_p50=effective_mfe,
        mae_p25=effective_mae,
        tp_dist_bps=round(tp_dist_bps, 2),
        sl_dist_bps=round(sl_dist_bps, 2),
        p_tp=round(p_tp, 4),
        p_sl=round(p_sl, 4),
        gross_edge_bps=round(gross_edge_bps, 2),
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        ev_net_bps=round(ev_net_bps, 2),
        opportunity_quality=oq,
        opportunity_category=oq_category,
        target_rr=target_rr,
        max_hold_bars=max_hold_bars,
        impact_bps=impact_bps,
        execute=execute,
        block_reason=block_reason,
        tp_price=tp_price,
        sl_price=sl_price,
    )


def _build_abstain(event, mfe_p50, mae_p25, tp_dist_bps, sl_dist_bps,
                   price, direction, block_reason, target_rr=2.0, max_hold_bars=30) -> PayoffEstimate:
    """Returns a non-executing PayoffEstimate with the given block reason."""
    return PayoffEstimate(
        timestamp=event.timestamp,
        event_type=event.event_type.value,
        direction=direction.value if hasattr(direction, "value") else str(direction),
        price=price,
        mfe_p50=mfe_p50, mae_p25=mae_p25,
        tp_dist_bps=round(tp_dist_bps, 2),
        sl_dist_bps=round(sl_dist_bps, 2),
        p_tp=0.50, p_sl=0.50,
        gross_edge_bps=0.0, fee_bps=10.0, slippage_bps=0.0, ev_net_bps=0.0,
        opportunity_quality=0.0, opportunity_category="IGNORE",
        target_rr=target_rr, max_hold_bars=max_hold_bars, impact_bps=1.0,
        execute=False, block_reason=block_reason,
        tp_price=price, sl_price=price,
    )
