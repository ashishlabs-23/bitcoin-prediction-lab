"""
api/routes_notifications.py — High-Profit Alerts & Notification Settings
========================================================================
FastAPI APIRouter for multi-channel notifications (Email, WebHooks, Telegram, WebSockets).
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Body, Depends, HTTPException, Query
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
