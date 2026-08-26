"""
engine/event_detector.py — MEIE Layer 2: Market Event Classifier
=================================================================
Classifies the market into five named states based on the z-score state vector:

    NORMAL | IGNITION | VACUUM | TOXICITY_SHOCK | ABSORPTION

Design constraints (Ponytail):
  - Thresholds are NOT hardcoded here. They are read from PREREGISTRATION_THRESHOLDS
    dict which reflects values locked in preregistration documents.
  - No imports beyond numpy and microstructure_state (already in codebase).
  - Minimum gap enforcement between events prevents overlapping signals.

Preregistration reference:
  - results/meie_event01_preregistration.md — IGNITION thresholds (v1.0, LOCKED)
  - results/meie_direction01_preregistration.md — directional thresholds (v1.0, LOCKED)
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional

from engine.microstructure_state import MicrostructureStateVector, _get_meie_db

logger = logging.getLogger("btcognitive.event_detector")


# ---------------------------------------------------------------------------
# Locked preregistration thresholds
# Source: results/meie_event01_preregistration.md — MEIE-EVENT-01-v1.0
# Source: results/meie_direction01_preregistration.md — MEIE-DIRECTION-01-v1.0
# THESE VALUES MUST NOT BE CHANGED WITHOUT A NEW PREREGISTRATION DOCUMENT.
# ---------------------------------------------------------------------------
PREREGISTRATION_THRESHOLDS = {
    # IGNITION: section 2.2, MEIE-EVENT-01-v1.0
    "ignition_z_hawkes_min":  1.5,   # Hawkes intensity acceleration
    "ignition_z_ofi_abs_min": 1.0,   # OFI imbalance (either direction)
    "ignition_z_spread_max": -0.5,   # Prior compression (low spread)
    "ignition_prior_window":  15,    # Candles of prior spread to average

    # VACUUM: liquidity collapse markers
    "vacuum_z_depth_min":    -1.5,   # Very thin book (low volume proxy)
    "vacuum_z_spread_min":    1.5,   # Wide spread
    "vacuum_z_impact_min":    1.5,   # High price impact

    # TOXICITY_SHOCK: VPIN spike
    "toxicity_z_vpin_min":    2.0,   # Extreme toxicity

    # ABSORPTION: large OFI with no price response
    "absorption_z_ofi_abs_min": 1.5,  # Strong flow imbalance
    "absorption_z_impact_max":  0.3,  # But price barely moves

    # DIRECTIONAL signals, MEIE-DIRECTION-01-v1.0
    "long_z_ofi_min":  0.5,
    "short_z_ofi_max": -0.5,

    # Minimum candles between events (de-duplication)
    "min_event_gap_candles": 15,
}


class MarketEvent(str, Enum):
    NORMAL          = "NORMAL"
    IGNITION        = "IGNITION"          # Volatility acceleration from compression
    VACUUM          = "VACUUM"            # Liquidity collapse
    TOXICITY_SHOCK  = "TOXICITY_SHOCK"    # VPIN spike → jump risk
    ABSORPTION      = "ABSORPTION"        # Large OFI, no price response


class EventDirection(str, Enum):
    LONG      = "LONG"
    SHORT     = "SHORT"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass
class DetectedEvent:
    timestamp: str
    price: float
    event_type: MarketEvent
    direction: EventDirection
    state: MicrostructureStateVector
    preregistration_id: str
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        d["direction"] = self.direction.value
        return d


# ---------------------------------------------------------------------------
# State tracking (in-process cache for gap enforcement)
# ---------------------------------------------------------------------------
_last_event_candle: int = -999
_candle_counter: int = 0


# ---------------------------------------------------------------------------
# Event classification
# ---------------------------------------------------------------------------

def _classify_ignition(sv: MicrostructureStateVector, prior_spread_mean: float) -> bool:
    """
    IGNITION: Hawkes spike + OFI imbalance out of prior compression.
    All three conditions from MEIE-EVENT-01-v1.0 section 2.2 must hold simultaneously.
    """
    th = PREREGISTRATION_THRESHOLDS
    cond_hawkes  = sv.z_hawkes >= th["ignition_z_hawkes_min"]
    cond_ofi     = abs(sv.z_ofi) >= th["ignition_z_ofi_abs_min"]
    cond_compress = prior_spread_mean <= th["ignition_z_spread_max"]
    return cond_hawkes and cond_ofi and cond_compress


def _classify_vacuum(sv: MicrostructureStateVector) -> bool:
    """VACUUM: Thin book + wide spread + high impact simultaneously."""
    th = PREREGISTRATION_THRESHOLDS
    return (
        sv.z_depth  <= th["vacuum_z_depth_min"] and
        sv.z_spread >= th["vacuum_z_spread_min"] and
        sv.z_impact >= th["vacuum_z_impact_min"]
    )


def _classify_toxicity_shock(sv: MicrostructureStateVector) -> bool:
    """TOXICITY_SHOCK: Extreme VPIN reading."""
    return sv.z_vpin >= PREREGISTRATION_THRESHOLDS["toxicity_z_vpin_min"]


def _classify_absorption(sv: MicrostructureStateVector) -> bool:
    """ABSORPTION: Strong OFI but price barely moves (seller/buyer absorbed by other side)."""
    th = PREREGISTRATION_THRESHOLDS
    return (
        abs(sv.z_ofi)   >= th["absorption_z_ofi_abs_min"] and
        sv.z_impact     <= th["absorption_z_impact_max"]
    )


def _resolve_direction(sv: MicrostructureStateVector,
                       hawkes_snapshot: Optional[Dict[str, Any]] = None) -> EventDirection:
    """
    Directional assignment per MEIE-DIRECTION-01-v1.0:
    Both z_ofi sign AND Hawkes buy/sell dominance must agree.
    """
    th = PREREGISTRATION_THRESHOLDS
    ofi_long  = sv.z_ofi >= th["long_z_ofi_min"]
    ofi_short = sv.z_ofi <= th["short_z_ofi_max"]

    hawkes_long = hawkes_short = False
    if hawkes_snapshot:
        lb = float(hawkes_snapshot.get("lambda_buy", 0.0))
        ls = float(hawkes_snapshot.get("lambda_sell", 0.0))
        hawkes_long  = lb > ls
        hawkes_short = ls > lb

    if ofi_long and hawkes_long:
        return EventDirection.LONG
    if ofi_short and hawkes_short:
        return EventDirection.SHORT
    return EventDirection.AMBIGUOUS


# ---------------------------------------------------------------------------
# Prior spread mean from rolling window (needed for IGNITION compression check)
# ---------------------------------------------------------------------------

def _prior_spread_z_mean(window_candles: int) -> float:
    """Loads the mean z_spread over the prior N candles from microstructure_raw."""
    conn = _get_meie_db()
    try:
        cur = conn.execute(
            "SELECT raw_spread FROM microstructure_raw ORDER BY id DESC LIMIT ?;",
            (window_candles + 1,)  # +1 to exclude current candle's own value
        )
        rows = [r[0] for r in cur.fetchall()[1:]]  # skip the most recent (current)
    finally:
        conn.close()

    if len(rows) < 5:
        return 0.0  # insufficient history → treat as neutral

    import numpy as np
    arr = np.array(rows, dtype=np.float64)
    mu, sigma = float(np.mean(arr)), float(np.std(arr, ddof=1))
    if sigma < 1e-10:
        return 0.0
    # Return z-score of the mean of that window relative to its own distribution
    return float((float(np.mean(arr)) - mu) / sigma)


# ---------------------------------------------------------------------------
# Persist event to meie_memory.db
# ---------------------------------------------------------------------------

def _persist_event(event: DetectedEvent):
    conn = _get_meie_db()
    try:
        with conn:
            conn.execute(
                """INSERT INTO meie_events
                   (timestamp, price, event_type, z_hawkes, z_ofi, z_vpin,
                    z_depth, z_spread, z_impact, window_n, data_quality, direction)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (
                    event.timestamp, event.price, event.event_type.value,
                    event.state.z_hawkes, event.state.z_ofi, event.state.z_vpin,
                    event.state.z_depth, event.state.z_spread, event.state.z_impact,
                    event.state.window_n, event.state.data_quality,
                    event.direction.value
                )
            )
    except Exception as e:
        logger.warning(f"Could not persist MEIE event: {e}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def detect_event(
    sv: MicrostructureStateVector,
    hawkes_snapshot: Optional[Dict[str, Any]] = None,
) -> DetectedEvent:
    """
    Classifies the current market state into a named event.
    Enforces minimum gap of 15 candles between IGNITION events.

    Args:
        sv: MicrostructureStateVector from microstructure_state.compute_state_vector()
        hawkes_snapshot: Optional raw Hawkes dict for directional resolution.

    Returns:
        DetectedEvent (always returns — defaults to NORMAL if no event detected).
    """
    global _last_event_candle, _candle_counter
    _candle_counter += 1

    event_type = MarketEvent.NORMAL
    direction  = EventDirection.AMBIGUOUS
    notes      = ""
    preregistration_id = "MEIE-EVENT-01-v1.0"

    if sv.data_quality == "INSUFFICIENT":
        notes = "Insufficient rolling window — no event classification."
    else:
        # Priority order: VACUUM > TOXICITY_SHOCK > IGNITION > ABSORPTION
        gap_ok = (_candle_counter - _last_event_candle) >= PREREGISTRATION_THRESHOLDS["min_event_gap_candles"]

        if _classify_vacuum(sv):
            event_type = MarketEvent.VACUUM
            notes = "Liquidity vacuum detected: thin book + wide spread + high impact."
        elif _classify_toxicity_shock(sv):
            event_type = MarketEvent.TOXICITY_SHOCK
            notes = "VPIN toxicity shock: extreme order-flow toxicity."
        elif gap_ok and _classify_ignition(sv, _prior_spread_z_mean(PREREGISTRATION_THRESHOLDS["ignition_prior_window"])):
            event_type = MarketEvent.IGNITION
            direction  = _resolve_direction(sv, hawkes_snapshot)
            _last_event_candle = _candle_counter
            notes = f"Volatility ignition from compression. Direction: {direction.value}."
            preregistration_id = "MEIE-EVENT-01-v1.0 / MEIE-DIRECTION-01-v1.0"
        elif _classify_absorption(sv):
            event_type = MarketEvent.ABSORPTION
            direction  = _resolve_direction(sv, hawkes_snapshot)
            notes = f"Absorption: strong OFI but minimal price response. Side: {direction.value}."

    event = DetectedEvent(
        timestamp=sv.timestamp,
        price=sv.price,
        event_type=event_type,
        direction=direction,
        state=sv,
        preregistration_id=preregistration_id,
        notes=notes,
    )

    if event_type != MarketEvent.NORMAL:
        _persist_event(event)
        logger.info(f"MEIE Event: {event_type.value} | dir={direction.value} | "
                    f"z_hawkes={sv.z_hawkes:.2f} z_ofi={sv.z_ofi:.2f} z_vpin={sv.z_vpin:.2f}")

    return event
