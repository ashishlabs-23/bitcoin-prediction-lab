"""
api/routes_manual_journal.py — Manual Trade Journal and AI Forecast Evaluation API
===================================================================================
BTCognitive V32.42: Observational Manual Trade Journal & Dual Evaluation Endpoints.

Strict Operating Rules:
- ZERO LIVE EXECUTION: No broker connectivity, no order routing, no live position synchronization.
- MANUAL USER REGISTRY: Users execute elsewhere and manually record entries and exits.
- IMMUTABLE FORECAST SNAPSHOT: Captured at entry time with SHA-256 integrity seal.
- TRANSPARENT EVALUATION: Separates User Trade Performance from AI Forecast Accuracy.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException

from engine.manual_trade_journal import (
    ManualTradeJournal,
    ManualTradeRecord,
    capture_entry_forecast_snapshot,
    _compute_dict_sha256,
)
from api.security_auth import get_current_principal_id

logger = logging.getLogger("btcognitive.routes_manual_journal")

router = APIRouter(prefix="/api/journal", tags=["Manual Trade Journal & AI Evaluation"])

# Global journal singleton
_journal = ManualTradeJournal()


def _validate_requested_owner(requested_owner: Optional[str], principal_id: str) -> None:
    if requested_owner is not None and requested_owner != principal_id:
        raise HTTPException(status_code=403, detail="Requested owner does not match authenticated principal.")


def _get_owned_trade(trade_id: str, principal_id: str) -> ManualTradeRecord:
    trade = _journal.get_trade(trade_id)
    if trade is None or trade.user_id != principal_id:
        raise HTTPException(status_code=404, detail="Trade not found.")
    return trade


def _valid_probability_pair(probability_up: Any, probability_down: Any) -> bool:
    values = (probability_up, probability_down)
    return (
        all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values)
        and all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in values)
        and math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-6)
    )


def _capture_safe_forecast_snapshot(instrument: str, reference_price: float) -> Dict[str, Any]:
    """Keep only reported forecasts and regime values that have verifiable inputs."""
    try:
        snapshot = dict(capture_entry_forecast_snapshot(instrument, reference_price))
    except Exception as exc:
        logger.warning(
            "Manual journal forecast snapshot unavailable: %s",
            type(exc).__name__,
        )
        snapshot = {
            "snapshot_timestamp_utc": None,
            "instrument": instrument,
            "reference_price": reference_price,
            "forecast_status": "UNAVAILABLE_CAPTURE_ERROR",
            "model_id": None,
            "model_version": None,
            "predicted_direction": "UNAVAILABLE",
            "probability_up": None,
            "probability_down": None,
            "data_age_seconds": None,
            "regime_classification": "UNKNOWN",
            "strategy_signal": "ABSTAIN",
            "horizons": {},
        }

    horizons = snapshot.get("horizons")
    if not isinstance(horizons, dict):
        horizons = {}
    for horizon, result in horizons.items():
        if not isinstance(result, dict):
            horizons[horizon] = {
                "status": "UNAVAILABLE_INVALID_FORECAST",
                "p_up": None,
                "p_down": None,
                "predicted_direction": "UNAVAILABLE",
            }
            continue
        if snapshot.get("forecast_status") != "VALID" or not _valid_probability_pair(
            result.get("p_up"), result.get("p_down")
        ):
            result.update({
                "status": (
                    "UNAVAILABLE_UPSTREAM"
                    if snapshot.get("forecast_status") != "VALID"
                    else "UNAVAILABLE_INVALID_FORECAST"
                ),
                "p_up": None,
                "p_down": None,
                "predicted_direction": "UNAVAILABLE",
            })

    if snapshot.get("forecast_status") != "VALID" or not _valid_probability_pair(
        snapshot.get("probability_up"), snapshot.get("probability_down")
    ):
        if snapshot.get("forecast_status") == "VALID":
            snapshot["forecast_status"] = "UNAVAILABLE_INVALID_FORECAST"
        snapshot["probability_up"] = None
        snapshot["probability_down"] = None
        snapshot["predicted_direction"] = "UNAVAILABLE"

    try:
        from engine.inference_service import live_engine
        regime = getattr(live_engine, "latest_regime", None)
        snapshot["regime_classification"] = str(regime) if regime else "UNKNOWN"
    except Exception as exc:
        logger.warning(
            "Manual journal regime context unavailable: %s",
            type(exc).__name__,
        )
        snapshot["regime_classification"] = "UNKNOWN"

    snapshot["horizons"] = horizons
    snapshot.pop("immutable_sha256", None)
    snapshot["immutable_sha256"] = _compute_dict_sha256(snapshot)
    return snapshot


class EnterTradeRequest(BaseModel):
    instrument: str = Field(default="BTC-USD", description="Instrument traded by user")
    direction: str = Field(default="LONG", description="LONG or SHORT")
    entry_price: float = Field(..., gt=0, description="Entry price executed on user exchange")
    entry_timestamp_utc: Optional[str] = Field(default=None, description="ISO timestamp of entry")
    quantity: Optional[float] = Field(default=None, description="Position size in BTC (optional)")
    entry_fee_usd: Optional[float] = Field(default=None, ge=0, description="Explicit fee paid at entry in USD")
    market_type: str = Field(default="SPOT", description="SPOT, PERPETUAL, or FUTURES")
    leverage: float = Field(default=1.0, ge=1.0, le=100.0, description="Leverage if derivative")
    contract_multiplier: float = Field(default=1.0, gt=0, description="Contract multiplier")
    notes: Optional[str] = Field(default=None, max_length=500, description="Optional thesis / notes")
    user_id: Optional[str] = Field(
        default=None,
        description="Optional legacy field; if provided it must match the authenticated principal.",
    )
    trade_id: Optional[str] = Field(default=None, description="Optional custom unique trade ID")


class ExitTradeRequest(BaseModel):
    exit_price: float = Field(..., gt=0, description="Exit price executed on user exchange")
    exit_timestamp_utc: Optional[str] = Field(default=None, description="ISO timestamp of exit")
    quantity: Optional[float] = Field(default=None, gt=0, description="Quantity closed (supports partial)")
    exit_fee_usd: Optional[float] = Field(default=None, ge=0, description="Explicit fee paid at exit in USD")
    notes: Optional[str] = Field(default=None, max_length=500, description="Exit notes / reason")


class AdjustTradeRequest(BaseModel):
    field_name: str = Field(..., description="Field to adjust (e.g. notes, entry_fee_usd, leverage)")
    new_value: Any = Field(..., description="New value to record")
    reason: str = Field(..., min_length=3, description="Auditable rationale for the adjustment")


@router.get("/status")
def get_journal_status(principal_id: str = Depends(get_current_principal_id)):
    """Returns manual journal service status and non-execution posture."""
    open_trades = [trade for trade in _journal.get_open_trades() if trade.user_id == principal_id]
    closed_trades = [trade for trade in _journal.get_closed_trades() if trade.user_id == principal_id]
    return {
        "status": "ONLINE",
        "service": "ManualTradeJournal_and_AIForecastEvaluation",
        "version": "V32.42",
        "product_mode": "ANALYSIS_ONLY",
        "governance_status": "OFFLINE_RESEARCH_ONLY",
        "economic_posture": "NO_GO_NO_VALIDATED_EDGE",
        "live_trading_authorization": "DISABLED",
        "broker_adapters": "STRICTLY_NONE",
        "total_open_records": len(open_trades),
        "total_closed_records": len(closed_trades),
        "ledger_file": _journal.ledger_path
    }


@router.get("/trades")
def list_trades(
    user_id: Optional[str] = None,
    principal_id: str = Depends(get_current_principal_id),
):
    """Lists all open and closed manual trade records with summary counts."""
    _validate_requested_owner(user_id, principal_id)
    open_trades = [t for t in _journal.get_open_trades() if t.user_id == principal_id]
    closed_trades = [t for t in _journal.get_closed_trades() if t.user_id == principal_id]

    return {
        "status": "SUCCESS",
        "total_open": len(open_trades),
        "total_closed": len(closed_trades),
        "open_trades": [t.to_dict() for t in open_trades],
        "closed_trades": [t.to_dict() for t in closed_trades]
    }


@router.post("/trades/enter")
def enter_trade(
    req: EnterTradeRequest,
    principal_id: str = Depends(get_current_principal_id),
):
    """
    Records a manual trade entry with an immutable point-in-time AI forecast snapshot.
    """
    _validate_requested_owner(req.user_id, principal_id)
    snapshot = _capture_safe_forecast_snapshot(req.instrument, req.entry_price)
    trade, err = _journal.record_entry(
        instrument=req.instrument,
        direction=req.direction,
        entry_price=req.entry_price,
        entry_timestamp_utc=req.entry_timestamp_utc,
        quantity=req.quantity,
        entry_fee_usd=req.entry_fee_usd,
        market_type=req.market_type,
        leverage=req.leverage,
        contract_multiplier=req.contract_multiplier,
        notes=req.notes,
        user_id=principal_id,
        trade_id=req.trade_id,
        pre_captured_snapshot=snapshot,
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    return {
        "status": "SUCCESS",
        "message": "Manual trade entered and point-in-time forecast snapshot saved.",
        "trade": trade.to_dict()
    }


@router.get("/trades/{trade_id}")
def get_trade_detail(trade_id: str, principal_id: str = Depends(get_current_principal_id)):
    """Retrieves full details of a single manual trade record."""
    trade = _get_owned_trade(trade_id, principal_id)
    return {
        "status": "SUCCESS",
        "trade": trade.to_dict()
    }


@router.post("/trades/{trade_id}/exit")
def exit_trade(
    trade_id: str,
    req: ExitTradeRequest,
    principal_id: str = Depends(get_current_principal_id),
):
    """
    Records an exit (partial or full) against an open manual trade.
    """
    _get_owned_trade(trade_id, principal_id)
    trade, err = _journal.record_exit(
        trade_id=trade_id,
        exit_price=req.exit_price,
        exit_timestamp_utc=req.exit_timestamp_utc,
        quantity=req.quantity,
        exit_fee_usd=req.exit_fee_usd,
        notes=req.notes
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    return {
        "status": "SUCCESS",
        "message": "Manual exit recorded and P&L calculated.",
        "trade": trade.to_dict()
    }


@router.post("/trades/{trade_id}/adjust")
def adjust_trade(
    trade_id: str,
    req: AdjustTradeRequest,
    principal_id: str = Depends(get_current_principal_id),
):
    """
    Records an auditable adjustment to a manual trade.
    """
    _get_owned_trade(trade_id, principal_id)
    trade, err = _journal.record_adjustment(
        trade_id=trade_id,
        field_name=req.field_name,
        new_value=req.new_value,
        reason=req.reason
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    return {
        "status": "SUCCESS",
        "message": "Auditable adjustment recorded successfully.",
        "trade": trade.to_dict()
    }


@router.get("/evaluation")
def get_performance_evaluation(principal_id: str = Depends(get_current_principal_id)):
    """
    Computes and returns separate User Trade Performance and AI Forecast Performance.
    """
    raise HTTPException(
        status_code=503,
        detail=(
            "Owner-scoped performance evaluation is unavailable; the current journal evaluator "
            "aggregates records without an owner filter."
        ),
    )
