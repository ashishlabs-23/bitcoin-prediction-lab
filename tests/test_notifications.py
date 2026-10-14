"""
Unit Tests for High-Profit Opportunity Detection and Notification Dispatcher.
"""

import pytest
import asyncio
import socket
from models.opportunity_detector import OpportunityDetector
from api.notifications import NotificationManager, _PinnedWebhookNetworkBackend
from api.routes_notifications import trigger_test_notification


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


def test_notification_settings_redact_and_preserve_secrets():
    manager = NotificationManager()
    manager.settings["smtp_password"] = "smtp-secret"
    manager.settings["telegram_bot_token"] = "telegram-secret"
    manager.settings["webhook_url"] = "https://discord.com/api/webhooks/secret"

    public_settings = manager.get_settings()
    assert "smtp_password" not in public_settings
    assert "smtp_user" not in public_settings
    assert "smtp_from" not in public_settings
    assert "email_recipient" not in public_settings
    assert "telegram_bot_token" not in public_settings
    assert "webhook_url" not in public_settings
    assert public_settings["smtp_password_configured"] is True
    assert public_settings["telegram_bot_token_configured"] is True
    assert public_settings["webhook_url_configured"] is True

    manager.update_settings({"smtp_password": "", "telegram_bot_token": "", "webhook_url": ""})
    assert manager.settings["smtp_password"] == "smtp-secret"
    assert manager.settings["telegram_bot_token"] == "telegram-secret"
    assert manager.settings["webhook_url"] == "https://discord.com/api/webhooks/secret"


def test_dispatch_awaits_and_reports_webhook_delivery(monkeypatch):
    manager = NotificationManager()
    manager.update_settings({
        "email_enabled": False,
        "webhook_enabled": True,
        "webhook_url": "https://discord.com/api/webhooks/test"
    })
    sent_alerts = []

    async def send_webhook(alert):
        sent_alerts.append(alert)
        return {"status": "delivered"}

    monkeypatch.setattr(manager, "_send_external_webhook", send_webhook)
    result = asyncio.run(manager.dispatch_alert({"id": "notification-test", "is_test": True}))

    assert sent_alerts[0]["id"] == "notification-test"
    assert result["channels"]["webhook"] == {"status": "delivered"}


def test_unvalidated_market_alert_is_blocked_before_any_delivery(monkeypatch):
    manager = NotificationManager()
    manager.settings.update({
        "email_enabled": True,
        "webhook_enabled": True,
        "telegram_bot_token": "configured-token",
        "telegram_chat_id": "configured-chat",
    })
    calls = []

    async def should_not_send(*args, **kwargs):
        calls.append((args, kwargs))
        return {"status": "delivered"}

    monkeypatch.setattr(manager, "_send_email_alert", should_not_send)
    monkeypatch.setattr(manager, "_send_external_webhook", should_not_send)
    monkeypatch.setattr(manager, "_send_telegram_alert", should_not_send)

    result = asyncio.run(manager.dispatch_alert({
        "id": "unvalidated-market-alert",
        "direction": "LONG",
        "opportunity_score": 99,
        "entry_price": 60000,
        "target_profit_price": 62000,
    }))

    assert result["status"] == "blocked"
    assert result["research_authorization"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert result["channels"] == {"all": {"status": "blocked"}}
    assert calls == []
    assert manager.get_recent_alerts() == []


@pytest.mark.parametrize(
    "sender_name",
    ["_send_email_alert", "_send_external_webhook", "_send_telegram_alert"],
)
def test_direct_market_alert_senders_are_blocked(sender_name):
    manager = NotificationManager()
    result = asyncio.run(getattr(manager, sender_name)({"direction": "LONG"}))
    assert result["status"] == "blocked"
    assert result["reason"]


def test_telegram_webhook_selection_uses_bot_channel_only(monkeypatch):
    manager = NotificationManager()
    manager.update_settings({
        "email_enabled": False,
        "webhook_enabled": True,
        "webhook_type": "telegram",
        "telegram_bot_token": "bot-secret",
        "telegram_chat_id": "chat-id",
        "webhook_url": "http://127.0.0.1/internal",
    })
    sent_alerts = []

    async def send_telegram(alert):
        sent_alerts.append(alert)
        return {"status": "delivered"}

    monkeypatch.setattr(manager, "_send_telegram_alert", send_telegram)
    result = asyncio.run(manager.dispatch_alert({"id": "telegram-test", "is_test": True}))

    assert sent_alerts[0]["id"] == "telegram-test"
    assert result["channels"]["telegram"] == {"status": "delivered"}
    assert "webhook" not in result["channels"]


@pytest.mark.parametrize(("status_code", "expected"), [(204, "delivered"), (503, "failed")])
def test_test_webhook_reports_real_http_result(monkeypatch, status_code, expected):
    manager = NotificationManager()
    manager.update_settings({
        "webhook_enabled": True,
        "webhook_type": "discord",
        "webhook_url": "https://discord.com/api/webhooks/test"
    })
    captured = {}

    class FakeResponse:
        def __init__(self, code):
            self.status_code = code

    async def validate_destination(url):
        return ["8.8.8.8"]

    async def post_webhook(url, payload, addresses):
        captured["url"] = url
        captured["payload"] = payload
        captured["addresses"] = addresses
        return FakeResponse(status_code)

    monkeypatch.setattr(manager, "_validate_public_webhook_destination", validate_destination)
    monkeypatch.setattr(manager, "_post_webhook", post_webhook)
    result = asyncio.run(manager._send_external_webhook({
        "id": "notification-test",
        "tier_title": "BTCognitive notification delivery test",
        "rationale": "Test only; not a market signal.",
        "is_test": True
    }))

    assert result["status"] == expected
    assert captured["payload"]["content"] == "BTCognitive test message; this is not a trading signal."
    assert "fields" not in captured["payload"]["embeds"][0]


def test_test_notification_has_no_fabricated_market_signal(monkeypatch):
    captured = {}

    async def dispatch(alert):
        captured.update(alert)
        return {
            "status": "dispatched",
            "channels": {
                "webhook": {"status": "not_configured"},
                "email": {"status": "disabled"}
            }
        }

    monkeypatch.setattr("api.routes_notifications.notification_manager.dispatch_alert", dispatch)
    result = asyncio.run(trigger_test_notification())

    assert result["status"] == "not_configured"
    assert captured["is_test"] is True
    assert "not a market observation" in captured["rationale"]
    assert not {"direction", "entry_price", "target_profit_price", "stop_loss_price", "opportunity_score"} & captured.keys()
    assert "not configured: webhook" in result["message"]


def test_notification_manager_does_not_expose_personal_email_defaults(monkeypatch):
    for name in ("SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "EMAIL_RECIPIENT"):
        monkeypatch.delenv(name, raising=False)
    manager = NotificationManager()
    settings = manager.get_settings()
    assert settings["email_enabled"] is False
    assert "email_recipient" not in settings


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/hook",
    "https://127.0.0.1/hook",
    "https://localhost/hook",
    "https://discord.com.evil.example/api/webhooks/token",
    "https://user:pass@discord.com/api/webhooks/token",
    "https://discord.com:444/api/webhooks/token",
])
def test_webhook_url_rejects_untrusted_destinations(url):
    manager = NotificationManager()
    with pytest.raises(ValueError):
        manager.update_settings({"webhook_url": url})


def test_generic_webhook_requires_explicit_host_allowlist(monkeypatch):
    manager = NotificationManager()
    monkeypatch.setattr("api.notifications.ALLOWED_WEBHOOK_HOSTS", {"hooks.example.com"})
    manager.update_settings({
        "webhook_type": "generic",
        "webhook_url": "https://hooks.example.com/notify"
    })
    with pytest.raises(ValueError, match="not in BTCOGNITIVE_WEBHOOK_ALLOWED_HOSTS"):
        manager.update_settings({"webhook_url": "https://untrusted.example/notify"})


def test_webhook_delivery_rejects_private_dns_resolution(monkeypatch):
    manager = NotificationManager()
    manager.update_settings({
        "webhook_enabled": True,
        "webhook_url": "https://discord.com/api/webhooks/test"
    })
    posted = []

    class FakeLoop:
        async def getaddrinfo(self, hostname, port, *, type):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]

    async def post_webhook(*args):
        posted.append(args)

    monkeypatch.setattr("api.notifications.asyncio.get_running_loop", lambda: FakeLoop())
    monkeypatch.setattr(manager, "_post_webhook", post_webhook)
    result = asyncio.run(manager._send_external_webhook({"is_test": True}))

    assert result["status"] == "failed"
    assert "non-public IP" in result["reason"]
    assert posted == []


def test_pinned_webhook_transport_connects_to_checked_address():
    backend = _PinnedWebhookNetworkBackend("discord.com", ["8.8.8.8"])
    connected = []

    class FakeBackend:
        async def connect_tcp(self, host, port, **kwargs):
            connected.append((host, port))
            return object()

    backend._backend = FakeBackend()
    asyncio.run(backend.connect_tcp("discord.com", 443))

    assert connected == [("8.8.8.8", 443)]
