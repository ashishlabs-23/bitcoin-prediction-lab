"""
api/routes_notifications.py — High-Profit Alerts & Notification Settings
========================================================================
FastAPI APIRouter for multi-channel notifications (Email, WebHooks, Telegram, WebSockets).
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Query, Body, HTTPException

from api.notifications import notification_manager
from engine.feature_cache import feature_cache

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
async def update_notification_settings(payload: Dict[str, Any] = Body(...)):
    """Updates notification thresholds and webhook endpoints."""
    updated = notification_manager.update_settings(payload)
    return {"status": "success", "settings": updated}


@router.post("/api/notifications/test")
async def trigger_test_notification():
    """Rejects synthetic opportunity alerts instead of generating fake trade values."""
    raise HTTPException(
        status_code=409,
        detail={
            "status": "DATA_UNAVAILABLE",
            "message": "Synthetic opportunity notifications are disabled.",
        },
    )
