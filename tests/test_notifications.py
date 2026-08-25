"""
Unit Tests for High-Profit Opportunity Detection and Notification Dispatcher.
"""

import pytest
import asyncio
from models.opportunity_detector import OpportunityDetector
from api.notifications import NotificationManager


def test_opportunity_detector_no_signal():
    detector = OpportunityDetector(cooldown_seconds=0)
    prediction = {
        "direction": "SKIP",
        "probability": 0.50,
        "entry_price": 60000.0,
        "tp": 60300.0,
        "sl": 59800.0
    }
    alert = detector.evaluate_opportunity(prediction)
    assert alert is None, "SKIP direction should not trigger an alert"


def test_opportunity_detector_high_profit_long():
    detector = OpportunityDetector(min_probability_long=0.54, min_expected_profit_pct=1.5, cooldown_seconds=0)
    prediction = {
        "direction": "LONG",
        "probability": 0.72,
        "entry_price": 60000.0,
        "tp": 61500.0,   # +2.5% TP
        "sl": 59400.0,   # -1.0% SL
        "expected_return": 0.025
    }
    regime = {"current_regime": "TRENDING_BULL", "event_flags": []}
    quality = {"score": 85}

    alert = detector.evaluate_opportunity(prediction, regime, quality)
    assert alert is not None, "High-conviction LONG with 2.5% TP should trigger alert"
    assert alert["direction"] == "LONG"
    assert alert["tier"] == "ULTRA_HIGH_PROFIT" or alert["tier"] == "HIGH_CONVICTION"
    assert alert["opportunity_score"] >= 75
    assert alert["target_profit_pct"] == 2.5
    assert alert["risk_pct"] == 1.0


def test_opportunity_detector_high_profit_short():
    detector = OpportunityDetector(max_probability_short=0.46, min_expected_profit_pct=1.5, cooldown_seconds=0)
    prediction = {
        "direction": "SHORT",
        "probability": 0.35,
        "entry_price": 60000.0,
        "tp": 58500.0,   # +2.5% TP for short
        "sl": 60600.0,   # -1.0% SL for short
        "expected_return": -0.025
    }
    regime = {"current_regime": "TRENDING_BEAR", "event_flags": []}
    quality = {"score": 88}

    alert = detector.evaluate_opportunity(prediction, regime, quality)
    assert alert is not None, "High-conviction SHORT with 2.5% TP should trigger alert"
    assert alert["direction"] == "SHORT"
    assert alert["target_profit_pct"] == 2.5


def test_notification_manager_lifecycle():
    manager = NotificationManager()
    
    initial_settings = manager.get_settings()
    assert "sound_alerts_enabled" in initial_settings
    assert "webhook_enabled" in initial_settings

    manager.update_settings({"min_profit_threshold_pct": 2.0, "sound_alerts_enabled": False})
    updated = manager.get_settings()
    assert updated["min_profit_threshold_pct"] == 2.0
    assert updated["sound_alerts_enabled"] is False

    alert = {
        "id": "alert_test_123",
        "tier_title": "💎 ULTRA HIGH PROFIT OPPORTUNITY",
        "direction": "LONG",
        "opportunity_score": 90,
        "entry_price": 62000.0,
        "target_profit_pct": 2.5
    }

    manager.record_alert(alert)
    recent = manager.get_recent_alerts(limit=5)
    assert len(recent) >= 1
    assert recent[0]["id"] == "alert_test_123"


def test_notification_manager_email():
    manager = NotificationManager()
    settings = manager.get_settings()
    assert settings["email_enabled"] is True
    assert "manuashi2018@gmail.com" in settings["email_recipient"]

    alert = {
        "id": "alert_email_test_999",
        "tier_title": "💎 ULTRA HIGH PROFIT OPPORTUNITY",
        "direction": "LONG",
        "opportunity_score": 95,
        "entry_price": 63500.0,
        "target_profit_price": 65150.0,
        "stop_loss_price": 62738.0,
        "target_profit_pct": 2.6,
        "risk_pct": 1.2,
        "risk_reward_ratio": "2.17:1",
        "rationale": "High-conviction LONG with +2.6% Target TP."
    }

    # Dispatch alert synchronously in test
    asyncio.run(manager.dispatch_alert(alert))
    recent = manager.get_recent_alerts(limit=1)
    assert len(recent) == 1
    assert recent[0]["id"] == "alert_email_test_999"

