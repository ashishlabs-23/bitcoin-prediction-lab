"""
api/routes_notifications.py — High-Profit Alerts & Notification Settings
========================================================================
FastAPI APIRouter for multi-channel notifications (Email, WebHooks, Telegram, WebSockets).
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from config.security import UserRole
from api.security_auth import require_role

from api.notifications import notification_manager

logger = logging.getLogger("btcognitive.routes_notifications")

router = APIRouter(tags=["Notifications & Alerts"])


@router.get("/api/notifications/recent")
def get_recent_notifications(limit: int = Query(20, le=100)):
    """Returns recent high-profit opportunity alerts."""
    return {
        "alerts": notification_manager.get_recent_alerts(limit=limit),
        "count": len(notification_manager.recent_alerts),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/api/notifications/settings")
def get_notification_settings():
    """Returns current notification and webhook configurations."""
    return notification_manager.get_settings()


@router.post("/api/notifications/settings")
async def update_notification_settings(
    payload: Dict[str, Any] = Body(...),
    _current_role: UserRole = Depends(require_role(UserRole.ADMIN)),
):
    """Updates notification thresholds and webhook endpoints."""
    try:
        updated = notification_manager.update_settings(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "success", "settings": updated}


@router.post("/api/notifications/test")
async def trigger_test_notification(
    _current_role: UserRole = Depends(require_role(UserRole.ADMIN)),
):
    """Sends a neutral test message through configured channels; it is not a market signal."""
    test_alert = {
        "id": f"notification_test_{time.time_ns()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tier": "NOTIFICATION_TEST",
        "tier_title": "BTCognitive notification delivery test",
        "badge": "TEST ONLY",
        "rationale": "This test verifies notification delivery only. It is not a market observation, forecast, or trading signal.",
        "is_test": True
    }

    dispatch_result = await notification_manager.dispatch_alert(test_alert)
    channels = dispatch_result.get("channels", {})
    delivered = [name for name, result in channels.items() if result.get("status") == "delivered"]
    failed = [name for name, result in channels.items() if result.get("status") == "failed"]
    unconfigured = [name for name, result in channels.items() if result.get("status") == "not_configured"]

    if delivered and failed:
        status = "partial"
    elif delivered:
        status = "delivered"
    elif failed:
        status = "failed"
    else:
        status = "not_configured"

    details = []
    if delivered:
        details.append("delivered via " + ", ".join(delivered))
    if failed:
        details.append("failed via " + ", ".join(failed))
    if unconfigured:
        details.append("not configured: " + ", ".join(unconfigured))
    message = "Test message " + ("; ".join(details) if details else "was not delivered by any configured channel.")
    return {
        "status": status,
        "message": message,
        "delivery": channels,
        "alert": test_alert
    }


from api.security_auth import require_role, get_current_user_role

@router.post("/api/notifications/research-alerts/evaluate")
async def evaluate_research_alerts(
    request: Request,
    force: bool = Query(False, description="Force evaluation bypassing cooldown (Admin only)"),
    current_role: UserRole = Depends(get_current_user_role),
):
    """
    Evaluates documented BTCUSD research conditions on fresh market data.
    Dispatches notifications across configured channels if a genuine condition is detected.
    Strictly analysis-only: never places an order or enables live execution.
    """
    if force and current_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Bypassing research alert cooldown with force=true requires ADMIN role credentials."
        )

    ws_manager = getattr(request.app.state, "ws_manager", None) if hasattr(request, "app") and hasattr(request.app, "state") else None
    result = await notification_manager.evaluate_research_conditions(force=force, ws_manager=ws_manager)
    return result



@router.get("/api/notifications/diagnostics")
def get_notification_diagnostics(request: Request):
    """
    Returns comprehensive alert worker health and channel delivery diagnostics.
    Exposes worker heartbeat, last evaluation result, channel configuration,
    and recent alert count. Safe to call without authentication.
    """
    ws_manager = getattr(request.app.state, "ws_manager", None) if hasattr(request, "app") and hasattr(request.app, "state") else None
    return notification_manager.get_diagnostics(ws_manager=ws_manager)


@router.get("/api/notifications/research-alerts/conditions")
def get_research_conditions_status():
    """Returns metadata and status for documented BTCUSD research conditions."""
    return {
        "conditions": [
            {
                "id": "volatility_compression",
                "name": "Hourly Volatility Compression",
                "hypothesis": "Realized variance contraction below historical 15th percentile signals regime transition setup.",
                "governance": "OFFLINE_RESEARCH_ONLY",
                "is_directional": False,
                "cooldown_seconds": 900,
            },
            {
                "id": "extreme_mean_reversion_deviation",
                "name": "Extreme Z-Score Price Stretch",
                "hypothesis": "Candle deviation > 3.0 standard deviations from short-term rolling mean indicates high-excursion risk envelope.",
                "governance": "OFFLINE_RESEARCH_ONLY",
                "is_directional": False,
                "cooldown_seconds": 900,
            },
            {
                "id": "confirmed_high_vol_regime",
                "name": "Confirmed High-Volatility Regime",
                "hypothesis": "Realized variance expansion above 85th percentile signals elevated tail risk and wider forecast uncertainty bounds.",
                "governance": "OFFLINE_RESEARCH_ONLY",
                "is_directional": False,
                "cooldown_seconds": 900,
            },
        ],
        "governance_mode": "ANALYSIS_ONLY",
        "live_trading_enabled": False,
        "order_submission_enabled": False,
        "directional_recommendation_status": "DISABLED",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

