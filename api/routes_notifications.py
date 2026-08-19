"""
api/routes_notifications.py — High-Profit Alerts & Notification Settings
========================================================================
FastAPI APIRouter for multi-channel notifications (Email, WebHooks, Telegram, WebSockets).
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Query, Body

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
    """Triggers an instant simulated high-profit opportunity alert for testing sound & webhook."""
    row = feature_cache.get_latest_row()
    live_p = float(row["close"]) if row is not None else 65000.0
    tp = round(live_p * 1.026, 2)
    sl = round(live_p * 0.988, 2)

    test_alert = {
        "id": f"test_alert_{int(time.time())}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tier": "ULTRA_HIGH_PROFIT",
        "tier_title": "💎 ULTRA HIGH PROFIT OPPORTUNITY (TEST)",
        "badge": "TEST ALERT",
        "opportunity_score": 92,
        "direction": "LONG",
        "probability": 0.785,
        "probability_pct": 78.5,
        "entry_price": live_p,
        "target_profit_price": tp,
        "stop_loss_price": sl,
        "target_profit_pct": 2.6,
        "risk_pct": 1.2,
        "risk_reward_ratio": "2.17:1",
        "expected_gain_usd_per_btc": round(tp - live_p, 2),
        "regime": "TRENDING_BULL",
        "quality_score": 90,
        "rationale": "High-conviction test opportunity: +2.6% Target TP with 2.17:1 Risk/Reward ratio.",
        "sound_alert": True,
        "is_test": True
    }

    await notification_manager.dispatch_alert(test_alert)
    return {"status": "success", "message": "Test notification dispatched!", "alert": test_alert}
