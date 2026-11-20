"""
api/routes_user_positions.py — User Position Tracker & Adaptive Risk Copilot Endpoints
========================================================================================
Protocol: BTCognitive V32.42 — User Position Tracker & Adaptive Risk Copilot
Governance: OFFLINE_RESEARCH_ONLY | NO_GO_NO_VALIDATED_EDGE | Live Trading: DISABLED

FastAPI router exposing endpoints for:
- User position registration and lifecycle management (OPEN_LONG, OPEN_SHORT, PARTIAL_EXIT, CLOSE_POSITION)
- Spot vs derivative contract validation (spot short rejection)
- Adaptive Risk Copilot mark-to-market evaluation and explainable alerts
- Full trade journaling and timeline history
"""

from __future__ import annotations

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Request

from engine.user_position_tracker import UserPositionTracker, UserPosition
from engine.adaptive_risk_copilot import AdaptiveRiskCopilot, PositionRiskSnapshot
from api.market_drivers import _fetch_quote
from api.security_auth import get_current_principal_id

logger = logging.getLogger("btcognitive.routes_user_positions")
router = APIRouter(prefix="/api/positions", tags=["User Positions & Risk Copilot"])

# Global tracker and copilot singletons
_tracker = UserPositionTracker()
_copilot = AdaptiveRiskCopilot(stale_threshold_seconds=5.0)


def _validate_requested_owner(requested_owner: Optional[str], principal_id: str) -> None:
    if requested_owner is not None and requested_owner != principal_id:
        raise HTTPException(status_code=403, detail="Requested owner does not match authenticated principal.")


def _get_owned_position(position_id: str, principal_id: str) -> UserPosition:
    position = _tracker.get_position(position_id)
    if position is None or position.user_id != principal_id:
        raise HTTPException(status_code=404, detail="Position not found.")
    return position


class OpenPositionRequest(BaseModel):
    position_id: Optional[str] = None
    user_id: Optional[str] = Field(
        default=None,
        description="Optional legacy field; if provided it must match the authenticated principal.",
    )
    instrument: str = "BTC-USD"
    venue: str = "COINBASE"
    market_type: str = "SPOT"  # "SPOT", "PERPETUAL", "FUTURES"
    side: str = "LONG"  # "LONG", "SHORT"
    entry_price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    entry_timestamp_utc: Optional[str] = None
    entry_fee_usd: float = 0.0
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    leverage: float = 1.0
    margin_usd: Optional[float] = None
    notes: Optional[str] = None


class PartialExitRequest(BaseModel):
    exit_price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    fee_usd: float = 0.0
    timestamp_utc: Optional[str] = None
    reason: Optional[str] = None


class ClosePositionRequest(BaseModel):
    exit_price: float = Field(..., gt=0)
    fee_usd: float = 0.0
    timestamp_utc: Optional[str] = None
    reason: Optional[str] = "USER_REQUESTED_CLOSE"


async def _get_current_market_quote(request: Request) -> Dict[str, Any]:
    """Retrieve a quote or report an explicit unavailable state; never fabricate one."""
    client = getattr(request.app.state, "http", None) if hasattr(request, "app") else None
    try:
        quote = await _fetch_quote("coinbase", client)
        age = quote.get("cache_age_seconds", 0.0)
        return {
            "price": quote.get("price"),
            "bid": quote.get("bid"),
            "ask": quote.get("ask"),
            "provider": "COINBASE",
            "source_timestamp": quote.get("source_timestamp"),
            "age_seconds": age,
            "is_live": True
        }
    except Exception as exc:
        logger.debug("Live quote fetch failed: %s", type(exc).__name__)
        return {
            "status": "UNAVAILABLE",
            "price": None,
            "bid": None,
            "ask": None,
            "provider": "COINBASE",
            "source_timestamp": None,
            "age_seconds": None,
            "is_live": False,
            "reason": "Market quote provider unavailable; no synthetic fallback is used.",
        }


@router.get("/status")
async def get_copilot_status(principal_id: str = Depends(get_current_principal_id)):
    """Returns runtime status and strict non-execution boundaries of the Risk Copilot."""
    open_positions = _tracker.get_open_positions(user_id=principal_id)
    return {
        "status": "SUCCESS",
        "product_mode": "ANALYSIS_ONLY",
        "copilot_state": "COPILOT_MONITORING_ACTIVE",
        "governing_posture": "OFFLINE_RESEARCH_ONLY",
        "live_trading": "DISABLED",
        "broker_execution_adapters": "NONE",
        "order_placement_routes": "NONE",
        "monitored_open_positions_count": len(open_positions),
        "disclaimer": (
            "Risk Copilot operates as an observational telemetry and risk monitoring engine only. "
            "It monitors positions recorded by users and provides diagnostic risk alerts. "
            "Zero order execution, broker routing, or real capital deployment capabilities exist."
        )
    }


@router.get("")
async def list_open_positions(
    request: Request,
    user_id: Optional[str] = None,
    principal_id: str = Depends(get_current_principal_id),
):
    """Lists all open positions with real-time mark-to-market risk evaluations and alerts."""
    _validate_requested_owner(user_id, principal_id)
    open_positions = _tracker.get_open_positions(user_id=principal_id)
    quote = await _get_current_market_quote(request)

    evaluated_positions = []
    total_unrealized_pnl = 0.0
    total_cost_basis = 0.0

    for pos in open_positions:
        snapshot = _copilot.evaluate_position_risk(
            position=pos,
            market_quote=quote
        )
        total_unrealized_pnl += snapshot.net_unrealized_pnl_usd
        total_cost_basis += snapshot.cost_basis_usd
        evaluated_positions.append({
            "position": pos.to_dict(),
            "risk_snapshot": snapshot.to_dict()
        })

    portfolio_return_pct = (total_unrealized_pnl / total_cost_basis * 100.0) if total_cost_basis > 0 else 0.0

    return {
        "status": "SUCCESS",
        "user_id": principal_id,
        "total_open_count": len(open_positions),
        "total_unrealized_pnl_usd": round(total_unrealized_pnl, 2),
        "total_cost_basis_usd": round(total_cost_basis, 2),
        "portfolio_return_pct": round(portfolio_return_pct, 2),
        "market_quote": quote,
        "positions": evaluated_positions
    }


@router.get("/history")
async def list_closed_positions(
    user_id: Optional[str] = None,
    principal_id: str = Depends(get_current_principal_id),
):
    """Lists closed user positions with complete trade journals and realized P&L."""
    _validate_requested_owner(user_id, principal_id)
    closed = _tracker.get_closed_positions(user_id=principal_id)
    total_realized_pnl = sum(p.total_realized_pnl_usd for p in closed)
    total_fees = sum(p.accumulated_fees_usd for p in closed)

    return {
        "status": "SUCCESS",
        "total_closed_count": len(closed),
        "total_realized_pnl_usd": round(total_realized_pnl, 2),
        "total_fees_paid_usd": round(total_fees, 2),
        "positions": [p.to_dict() for p in closed]
    }


@router.get("/{position_id}")
async def get_position_detail(
    position_id: str,
    request: Request,
    principal_id: str = Depends(get_current_principal_id),
):
    """Retrieves full details, event timeline, and current risk snapshot for a position."""
    pos = _get_owned_position(position_id, principal_id)

    quote = await _get_current_market_quote(request)
    snapshot = _copilot.evaluate_position_risk(
        position=pos,
        market_quote=quote
    )

    return {
        "status": "SUCCESS",
        "position": pos.to_dict(),
        "risk_snapshot": snapshot.to_dict(),
        "market_quote": quote
    }


@router.post("/open")
async def open_position(
    req: OpenPositionRequest,
    principal_id: str = Depends(get_current_principal_id),
):
    """
    Records a user-entered position.
    Validates spot short constraints, leverage, stops, and targets.
    """
    _validate_requested_owner(req.user_id, principal_id)
    pos_id = req.position_id or f"usr_pos_{int(time.time()*1000)}"
    entry_ts = req.entry_timestamp_utc or datetime.now(timezone.utc).isoformat()

    pos, err = _tracker.record_open_position(
        position_id=pos_id,
        instrument=req.instrument,
        side=req.side,
        entry_price=req.entry_price,
        quantity=req.quantity,
        entry_timestamp_utc=entry_ts,
        user_id=principal_id,
        venue=req.venue,
        market_type=req.market_type,
        entry_fee_usd=req.entry_fee_usd,
        stop_loss_price=req.stop_loss_price,
        take_profit_price=req.take_profit_price,
        leverage=req.leverage,
        margin_usd=req.margin_usd,
        notes=req.notes
    )

    if err or not pos:
        raise HTTPException(status_code=400, detail=err or "Failed to record position")

    return {
        "status": "SUCCESS",
        "message": f"Position {pos_id} successfully recorded for risk monitoring.",
        "position": pos.to_dict()
    }


@router.post("/{position_id}/partial-exit")
async def partial_exit_position(
    position_id: str,
    req: PartialExitRequest,
    principal_id: str = Depends(get_current_principal_id),
):
    """Records a partial exit against an active open position."""
    _get_owned_position(position_id, principal_id)
    exit_ts = req.timestamp_utc or datetime.now(timezone.utc).isoformat()

    pos, err = _tracker.record_partial_exit(
        position_id=position_id,
        exit_price=req.exit_price,
        quantity=req.quantity,
        exit_timestamp_utc=exit_ts,
        fee_usd=req.fee_usd,
        reason=req.reason
    )

    if err or not pos:
        raise HTTPException(status_code=400, detail=err or "Failed to record partial exit")

    return {
        "status": "SUCCESS",
        "message": f"Partial exit recorded for position {position_id}.",
        "position": pos.to_dict()
    }


@router.post("/{position_id}/close")
async def close_position(
    position_id: str,
    req: ClosePositionRequest,
    principal_id: str = Depends(get_current_principal_id),
):
    """Records full exit and closure of an active position."""
    _get_owned_position(position_id, principal_id)
    exit_ts = req.timestamp_utc or datetime.now(timezone.utc).isoformat()

    pos, err = _tracker.record_close_position(
        position_id=position_id,
        exit_price=req.exit_price,
        exit_timestamp_utc=exit_ts,
        fee_usd=req.fee_usd,
        reason=req.reason
    )

    if err or not pos:
        raise HTTPException(status_code=400, detail=err or "Failed to close position")

    return {
        "status": "SUCCESS",
        "message": f"Position {position_id} successfully closed and archived to trade journal.",
        "position": pos.to_dict()
    }
