"""Pure deterministic hypothetical barrier calculations."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Any

from fastapi import HTTPException

from research.entry_tp_sl.barrier_contract import FROZEN_BARRIER_GRID


FORMULA_VERSION = "REGISTERED_ATR_BARRIERS_V1"
SCENARIO_LABEL = "SCENARIO_CALCULATION — NOT A MODEL PREDICTION"
DISCLAIMER = (
    "Deterministic hypothetical calculation from user-provided inputs; "
    "not model inference, investment advice, or an order."
)


def _finite_positive_number(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HTTPException(status_code=422, detail=f"{field} must be a positive finite number.")
    if not math.isfinite(value) or value <= 0:
        raise HTTPException(status_code=422, detail=f"{field} must be a positive finite number.")
    return float(value)


def _round_usd(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    """Calculate TP/SL from an explicit reference price, ATR in USD, side, and frozen pair."""
    side = payload.get("side")
    if side not in {"LONG", "SHORT"}:
        raise HTTPException(status_code=422, detail="side must be LONG or SHORT.")

    reference_price = _finite_positive_number(payload, "reference_price")
    volatility_atr = _finite_positive_number(payload, "volatility_atr")
    barrier_pair_id = payload.get("barrier_pair_id")
    if not isinstance(barrier_pair_id, str) or barrier_pair_id not in FROZEN_BARRIER_GRID:
        raise HTTPException(status_code=422, detail="barrier_pair_id is not in the frozen barrier grid.")

    pair = FROZEN_BARRIER_GRID[barrier_pair_id]
    horizon_minutes = payload.get("horizon_minutes")
    if (
        isinstance(horizon_minutes, bool)
        or not isinstance(horizon_minutes, int)
        or horizon_minutes != pair["vertical_horizon_minutes"]
    ):
        raise HTTPException(
            status_code=422,
            detail="horizon_minutes must match the selected frozen barrier pair.",
        )

    tp_distance = pair["tp_multiplier"] * volatility_atr
    sl_distance = pair["sl_multiplier"] * volatility_atr
    unrounded_prices = (
        reference_price,
        reference_price + tp_distance if side == "LONG" else reference_price - tp_distance,
        reference_price - sl_distance if side == "LONG" else reference_price + sl_distance,
    )
    if not all(math.isfinite(value) for value in unrounded_prices):
        raise HTTPException(status_code=422, detail="Inputs produce a nonfinite barrier price.")

    if side == "LONG":
        take_profit = _round_usd(reference_price + tp_distance)
        stop_loss = _round_usd(reference_price - sl_distance)
    else:
        take_profit = _round_usd(reference_price - tp_distance)
        stop_loss = _round_usd(reference_price + sl_distance)

    entry_price = _round_usd(reference_price)
    if entry_price <= 0 or take_profit <= 0 or stop_loss <= 0:
        raise HTTPException(
            status_code=422,
            detail="Inputs produce a nonpositive rounded barrier price.",
        )

    return {
        "status": "SCENARIO_CALCULATION",
        "label": SCENARIO_LABEL,
        "side": side,
        "entry_price": entry_price,
        "tp_price": take_profit,
        "sl_price": stop_loss,
        "barrier_pair_id": barrier_pair_id,
        "tp_multiplier": pair["tp_multiplier"],
        "sl_multiplier": pair["sl_multiplier"],
        "vertical_horizon_minutes": horizon_minutes,
        "reference_price": entry_price,
        "volatility_atr_usd": volatility_atr,
        "input_source": "USER_PROVIDED",
        "formula_version": FORMULA_VERSION,
        "formula": (
            "LONG: TP=reference+k_tp*ATR, SL=reference-k_sl*ATR; "
            "SHORT: TP=reference-k_tp*ATR, SL=reference+k_sl*ATR; "
            "USD outputs rounded to 0.01."
        ),
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": DISCLAIMER,
        "execution_mode": "PAPER_RESEARCH_ONLY",
        "live_capital_authorized": False,
    }


def get_scenario_options() -> list[dict[str, Any]]:
    """Expose only the frozen pair identifiers, multipliers, and horizons."""
    return [
        {
            "barrier_pair_id": pair_id,
            "tp_multiplier": pair["tp_multiplier"],
            "sl_multiplier": pair["sl_multiplier"],
            "horizon_minutes": pair["vertical_horizon_minutes"],
        }
        for pair_id, pair in FROZEN_BARRIER_GRID.items()
    ]
