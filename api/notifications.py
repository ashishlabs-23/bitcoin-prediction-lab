import os
import json
import time
import math
import hashlib
import asyncio
import ipaddress
import socket
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpcore
import httpx
from httpcore._backends.auto import AutoBackend
import logging

logger = logging.getLogger("btcognitive.notifications")

from api.http_client import get_shared_client
from config.security import ALLOWED_WEBHOOK_HOSTS


class _PinnedWebhookNetworkBackend:
    def __init__(self, hostname: str, addresses: List[str]):
        self.hostname = hostname.lower().rstrip(".")
        self.addresses = addresses
        self._backend = AutoBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        if host.lower().rstrip(".") != self.hostname or port != 443:
            raise OSError("Webhook transport attempted to connect to an unexpected destination.")

        last_error = None
        for address in self.addresses:
            try:
                return await self._backend.connect_tcp(
                    address,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except OSError as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise OSError("Webhook hostname has no validated IP addresses.")

    async def connect_unix_socket(self, path, timeout=None, socket_options=None):
        return await self._backend.connect_unix_socket(path, timeout, socket_options)

    async def sleep(self, seconds):
        await self._backend.sleep(seconds)


class _PinnedWebhookTransport(httpx.AsyncHTTPTransport):
    def __init__(self, hostname: str, addresses: List[str]):
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl.create_default_context(),
            max_connections=1,
            max_keepalive_connections=0,
            network_backend=_PinnedWebhookNetworkBackend(hostname, addresses),
        )


class NotificationManager:
    """
    Manages delivery of high-profit opportunity notifications across channels
    (Gmail SMTP, WebSockets, Browser Desktop Push, Discord, Telegram, Webhooks).
    """

    def __init__(self):
        smtp_user = os.getenv("SMTP_USER", "").strip()
        smtp_pw = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()
        smtp_from = os.getenv("SMTP_FROM", smtp_user).strip()

        self.settings = {
            "browser_alerts_enabled": True,
            "sound_alerts_enabled": True,
            "min_profit_threshold_pct": 1.5,
            "min_opportunity_score": 75,
            "email_enabled": bool(smtp_user and smtp_pw),
            "email_recipient": os.getenv("EMAIL_RECIPIENT", "").strip(),
            "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", 587)),
            "smtp_user": smtp_user,
            "smtp_password": smtp_pw,
            "smtp_from": smtp_from,
            "webhook_enabled": os.getenv("WEBHOOK_ENABLED", "false").strip().lower() == "true",
            "webhook_url": os.getenv("WEBHOOK_URL", "").strip(),
            "webhook_type": os.getenv("WEBHOOK_TYPE", "discord").strip().lower(),
            "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", "").strip()
        }
        self.recent_alerts: List[Dict[str, Any]] = []
        self.condition_cooldowns: Dict[str, float] = {}
        self.seen_dedup_hashes: set[str] = set()
        self.COOLDOWN_SECONDS: float = 900.0  # 15-minute standard research alert cooldown
        self.worker_status: str = "RUNNING"
        self.last_worker_heartbeat: Optional[str] = datetime.now(timezone.utc).isoformat()
        self.last_evaluation: Optional[Dict[str, Any]] = None

        from config.paths import DATA_DIR
        self._state_file = os.path.join(DATA_DIR, "research_alert_state.json")
        self._load_alert_state()

    def _load_alert_state(self) -> None:
        """Loads persisted cooldowns and deduplication hashes to survive restarts."""
        try:
            if os.path.exists(self._state_file) and os.path.getsize(self._state_file) > 0:
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.condition_cooldowns = data.get("condition_cooldowns", {})
                    self.seen_dedup_hashes = set(data.get("seen_dedup_hashes", []))
                    logger.info("Loaded persisted research alert state (%d cooldowns, %d dedup hashes).",
                                len(self.condition_cooldowns), len(self.seen_dedup_hashes))
        except Exception as e:
            logger.debug("Could not load research alert state: %s", e)

    def _save_alert_state(self) -> None:
        """Atomically persists cooldowns and deduplication hashes to disk."""
        try:
            os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
            tmp_path = f"{self._state_file}.tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump({
                    "condition_cooldowns": self.condition_cooldowns,
                    "seen_dedup_hashes": list(self.seen_dedup_hashes)[-500:],
                    "last_saved_at": datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
            os.replace(tmp_path, self._state_file)
        except Exception as e:
            logger.debug("Could not save research alert state: %s", e)


    def get_settings(self) -> Dict[str, Any]:
        settings = self.settings.copy()
        for key in (
            "smtp_password",
            "smtp_user",
            "smtp_from",
            "email_recipient",
            "telegram_bot_token",
            "telegram_chat_id",
            "webhook_url",
        ):
            settings.pop(key, None)
        settings["smtp_password_configured"] = bool(self.settings.get("smtp_password"))
        settings["email_configured"] = bool(
            self.settings.get("smtp_user") and self.settings.get("smtp_password")
        )
        settings["telegram_bot_token_configured"] = bool(self.settings.get("telegram_bot_token"))
        settings["telegram_chat_id_configured"] = bool(self.settings.get("telegram_chat_id"))
        settings["webhook_url_configured"] = bool(self.settings.get("webhook_url"))
        return settings

    @staticmethod
    def _validate_webhook_url(url: str, webhook_type: str) -> None:
        try:
            parsed = urlsplit(url)
            hostname = (parsed.hostname or "").lower().rstrip(".")
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Webhook URL is invalid.") from exc

        if (
            parsed.scheme != "https"
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or port not in (None, 443)
            or parsed.fragment
        ):
            raise ValueError("Webhook URL must be an HTTPS URL on port 443 without user information or a fragment.")

        if webhook_type == "discord":
            if hostname != "discord.com" or not parsed.path.startswith("/api/webhooks/"):
                raise ValueError("Discord webhooks must use https://discord.com/api/webhooks/ URLs.")
        elif webhook_type == "generic":
            if hostname not in ALLOWED_WEBHOOK_HOSTS:
                raise ValueError("Generic webhook host is not in BTCOGNITIVE_WEBHOOK_ALLOWED_HOSTS.")
        else:
            raise ValueError("Webhook type must be 'discord' or 'generic'.")

    @staticmethod
    async def _validate_public_webhook_destination(url: str) -> List[str]:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Webhook URL is missing a hostname.")

        try:
            loop = asyncio.get_running_loop()
            resolved = await loop.getaddrinfo(
                hostname,
                parsed.port or 443,
                type=socket.SOCK_STREAM,
            )
        except OSError as exc:
            raise ValueError("Webhook hostname could not be resolved.") from exc

        addresses = {record[4][0] for record in resolved}
        if not addresses:
            raise ValueError("Webhook hostname did not resolve to any IP addresses.")
        for address in addresses:
            try:
                is_global = ipaddress.ip_address(address).is_global
            except ValueError as exc:
                raise ValueError("Webhook hostname resolved to an invalid IP address.") from exc
            if not is_global:
                raise ValueError("Webhook hostname resolves to a non-public IP address.")
        return sorted(addresses)

    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        webhook_type = new_settings.get("webhook_type", self.settings.get("webhook_type", "discord"))
        if not isinstance(webhook_type, str) or webhook_type not in {"discord", "generic", "telegram"}:
            raise ValueError("Unsupported webhook type.")

        for key, value in new_settings.items():
            if key.endswith("_enabled") and type(value) is not bool:
                raise ValueError(f"{key} must be a boolean.")

        webhook_url = new_settings.get("webhook_url") or self.settings.get("webhook_url")
        if webhook_url and webhook_type != "telegram":
            if not isinstance(webhook_url, str):
                raise ValueError("Webhook URL must be a string.")
            self._validate_webhook_url(webhook_url, webhook_type)

        for k, v in new_settings.items():
            if k in self.settings:
                if k in {"smtp_password", "telegram_bot_token", "webhook_url"} and not v:
                    continue
                self.settings[k] = v
        return self.get_settings()

    def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(reversed(self.recent_alerts[-limit:]))

    def record_alert(self, alert_payload: Dict[str, Any]):
        self.recent_alerts.append(alert_payload)
        if len(self.recent_alerts) > 100:
            self.recent_alerts.pop(0)

    def get_diagnostics(self, ws_manager=None) -> Dict[str, Any]:
        """Returns comprehensive delivery diagnostics and alert worker state."""
        now_iso = datetime.now(timezone.utc).isoformat()
        ws_count = len(ws_manager.active_connections) if ws_manager and hasattr(ws_manager, "active_connections") else 0
        settings = self.get_settings()
        return {
            "worker_status": self.worker_status,
            "worker_interval_seconds": 60,
            "last_heartbeat": self.last_worker_heartbeat or now_iso,
            "last_evaluation": self.last_evaluation or {
                "timestamp": now_iso,
                "status": "INITIALIZING",
                "reason": "WAITING_FOR_FIRST_EVALUATION",
                "message": "Alert evaluator is starting up. First automatic cycle executes within 60 seconds."
            },
            "recent_alerts_count": len(self.recent_alerts),
            "cooldown_active_count": len(self.condition_cooldowns),
            "channels": {
                "websocket": {
                    "configured": True,
                    "status": "connected" if ws_count > 0 else "listening",
                    "active_clients": ws_count
                },
                "email": {
                    "configured": bool(settings.get("email_configured")),
                    "enabled": bool(settings.get("email_enabled")),
                    "status": "configured" if settings.get("email_configured") else "unconfigured"
                },
                "webhook": {
                    "configured": bool(settings.get("webhook_url_configured")),
                    "enabled": bool(settings.get("webhook_enabled")),
                    "type": settings.get("webhook_type"),
                    "status": "configured" if settings.get("webhook_url_configured") else "unconfigured"
                },
                "telegram": {
                    "configured": bool(settings.get("telegram_bot_token_configured") and settings.get("telegram_chat_id_configured")),
                    "status": "configured" if (settings.get("telegram_bot_token_configured") and settings.get("telegram_chat_id_configured")) else "unconfigured"
                }
            },
            "governance": {
                "product_mode": "ANALYSIS_ONLY",
                "live_trading_enabled": False,
                "order_submission_enabled": False,
                "directional_recommendation_status": "DISABLED",
                "execution_status": "DISABLED_ANALYSIS_ONLY"
            },
            "timestamp": now_iso
        }

    async def dispatch_alert(self, alert_payload: Dict[str, Any], ws_manager=None) -> Dict[str, Any]:
        """
        Dispatches neutral delivery tests or verified research-condition alerts.
        Production trade orders and unauthorized market execution signals remain blocked.
        """
        is_test = bool(alert_payload.get("is_test"))
        is_research = bool(alert_payload.get("is_research_alert") or alert_payload.get("type") == "RESEARCH_CONDITION_ALERT")
        if not (is_test or is_research):
            return {
                "status": "blocked",
                "alert_id": alert_payload.get("id"),
                "reason": "Production forecasts are unavailable; no market alert was sent.",
                "research_authorization": "BLOCKED_PROVENANCE_UNVERIFIED",
                "channels": {"all": {"status": "blocked"}},
            }

        self.record_alert(alert_payload)

        channels: Dict[str, Dict[str, str]] = {}

        # 1. WebSocket broadcast if manager provided
        if ws_manager is not None:
            try:
                # Primary event type
                ws_primary_type = "RESEARCH_CONDITION_ALERT" if is_research else ("NOTIFICATION_TEST" if is_test else "HIGH_PROFIT_ALERT")
                msg_payload = {
                    "type": ws_primary_type,
                    "data": alert_payload,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await ws_manager.broadcast(json.dumps(msg_payload))

                # Also broadcast NEW_ALERT canonical event for unified notification listeners
                new_alert_msg = {
                    "type": "NEW_ALERT",
                    "alert_type": ws_primary_type,
                    "data": alert_payload,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await ws_manager.broadcast(json.dumps(new_alert_msg))
                channels["websocket"] = {"status": "delivered"}
            except Exception as e:
                channels["websocket"] = {"status": "failed", "reason": type(e).__name__}
        else:
            channels["websocket"] = {"status": "not_configured"}

        # 2. Email Notification
        if self.settings.get("email_enabled"):
            channels["email"] = await self._send_email_alert(alert_payload)
        else:
            channels["email"] = {"status": "disabled"}

        # 3. Webhook / Discord / Telegram
        webhook_uses_telegram = (
            self.settings.get("webhook_enabled")
            and self.settings.get("webhook_type") == "telegram"
        )
        if webhook_uses_telegram:
            channels["telegram"] = await self._send_telegram_alert(alert_payload)
        elif self.settings.get("webhook_enabled"):
            channels["webhook"] = await self._send_external_webhook(alert_payload)
        else:
            channels["webhook"] = {"status": "disabled"}

        if not webhook_uses_telegram:
            if self.settings.get("telegram_bot_token") and self.settings.get("telegram_chat_id"):
                channels["telegram"] = await self._send_telegram_alert(alert_payload)
            else:
                channels["telegram"] = {"status": "not_configured"}

        return {"status": "dispatched", "alert_id": alert_payload.get("id"), "channels": channels}

    async def _send_test_email_alert(self, alert: Dict[str, Any]) -> Dict[str, str]:
        recipients = self.settings.get("email_recipient", "")
        recipients = [r.strip() for r in recipients.split(",") if r.strip()] if isinstance(recipients, str) else list(recipients)
        smtp_user = self.settings.get("smtp_user", "")
        smtp_password = self.settings.get("smtp_password", "").replace(" ", "").strip()
        if not recipients or not smtp_user or not smtp_password:
            return {"status": "not_configured", "reason": "SMTP credentials or recipient are not configured."}

        message = MIMEText(
            alert.get("rationale", "BTCognitive notification delivery test. This is not a market signal."),
            "plain",
            "utf-8"
        )
        message["Subject"] = "BTCognitive notification delivery test"
        message["From"] = self.settings.get("smtp_from", smtp_user)
        message["To"] = ", ".join(recipients)

        try:
            loop = asyncio.get_running_loop()

            def _send():
                with smtplib.SMTP(self.settings.get("smtp_host", "smtp.gmail.com"), int(self.settings.get("smtp_port", 587))) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(message["From"], recipients, message.as_string())

            await loop.run_in_executor(None, _send)
            return {"status": "delivered"}
        except Exception as e:
            return {"status": "failed", "reason": f"SMTP delivery failed ({type(e).__name__})."}

    async def _send_research_email_alert(self, alert: Dict[str, Any]) -> Dict[str, str]:
        recipients = self.settings.get("email_recipient", "")
        recipients = [r.strip() for r in recipients.split(",") if r.strip()] if isinstance(recipients, str) else list(recipients)
        smtp_user = self.settings.get("smtp_user", "")
        smtp_password = self.settings.get("smtp_password", "").replace(" ", "").strip()
        if not recipients or not smtp_user or not smtp_password:
            return {"status": "not_configured", "reason": "SMTP credentials or recipient are not configured."}

        cond_name = alert.get("condition_name", "RESEARCH_CONDITION")
        ref_price = alert.get("reference_price_usd", 0.0)
        body = (
            f"BTCUSD research condition detected\n\n"
            f"Condition: {cond_name}\n"
            f"Reference Price: ${ref_price:,.2f}\n"
            f"Event Time (UTC): {alert.get('timestamp')}\n"
            f"Source: {alert.get('source')}\n"
            f"Hypothesis: {alert.get('condition_hypothesis')}\n"
            f"Trigger Reason: {alert.get('trigger_reason')}\n"
            f"Limitations: {alert.get('limitations')}\n"
            f"Alert ID: {alert.get('id')}\n\n"
            f"Governance Notice: BTCognitive is analysis-only. Live trading, order placement, and automated execution are permanently disabled."
        )
        message = MIMEText(body, "plain", "utf-8")
        message["Subject"] = f"[BTCognitive Research] BTCUSD research condition detected: {cond_name}"
        message["From"] = self.settings.get("smtp_from", smtp_user)
        message["To"] = ", ".join(recipients)

        try:
            loop = asyncio.get_running_loop()

            def _send():
                with smtplib.SMTP(self.settings.get("smtp_host", "smtp.gmail.com"), int(self.settings.get("smtp_port", 587))) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(message["From"], recipients, message.as_string())

            await loop.run_in_executor(None, _send)
            return {"status": "delivered"}
        except Exception as e:
            return {"status": "failed", "reason": f"SMTP delivery failed ({type(e).__name__})."}

    async def _send_email_alert(self, alert: Dict[str, Any]):
        """Formats and sends email alert if a test alert or research condition alert is triggered."""
        if alert.get("is_test"):
            return await self._send_test_email_alert(alert)
        if alert.get("is_research_alert") or alert.get("type") == "RESEARCH_CONDITION_ALERT":
            return await self._send_research_email_alert(alert)
        return {
            "status": "blocked",
            "reason": "Production forecasts are unavailable; no market alert was sent.",
        }

    async def _post_webhook(self, url: str, payload: Dict[str, Any], addresses: List[str]):
        hostname = urlsplit(url).hostname
        if hostname is None:
            raise ValueError("Webhook URL is missing a hostname.")
        async with httpx.AsyncClient(
            transport=_PinnedWebhookTransport(hostname, addresses),
            timeout=5.0,
            trust_env=False,
        ) as client:
            return await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json", "User-Agent": "BTCognitive/2.0"},
            )

    async def _send_external_webhook(self, alert: Dict[str, Any]):
        """Asynchronously sends Discord or generic HTTP webhook using shared httpx client."""
        is_test = bool(alert.get("is_test"))
        is_research = bool(alert.get("is_research_alert") or alert.get("type") == "RESEARCH_CONDITION_ALERT")
        if not (is_test or is_research):
            return {
                "status": "blocked",
                "reason": "Production forecasts are unavailable; no market alert was sent.",
            }
        url = self.settings.get("webhook_url")
        w_type = self.settings.get("webhook_type", "discord")
        if w_type == "telegram":
            return {"status": "failed", "reason": "Telegram must use the configured bot-token channel."}
        if not url:
            return {"status": "not_configured", "reason": "Webhook URL is not configured."}
        try:
            self._validate_webhook_url(url, w_type)
            addresses = await self._validate_public_webhook_destination(url)
        except ValueError as exc:
            return {"status": "failed", "reason": str(exc)}

        try:
            if is_test and w_type == "discord" and "discord.com" in url:
                embed = {
                    "title": "BTCognitive notification delivery test",
                    "description": alert.get("rationale", "Test only; not a market signal."),
                    "color": 0x00F0FF,
                    "footer": {"text": "Test message · no market signal"}
                }
                payload = {"content": "BTCognitive test message; this is not a trading signal.", "embeds": [embed]}
            elif is_research and w_type == "discord" and "discord.com" in url:
                embed = {
                    "title": "🔬 BTCUSD research condition detected",
                    "description": alert.get("condition_hypothesis", "Research condition observation."),
                    "color": 0x38BDF8,
                    "fields": [
                        {"name": "Condition", "value": str(alert.get("condition_name")), "inline": True},
                        {"name": "Reference Price", "value": f"${alert.get('reference_price_usd', 0):,.2f}", "inline": True},
                        {"name": "Event Time (UTC)", "value": str(alert.get("timestamp")), "inline": False},
                        {"name": "Trigger Reason", "value": str(alert.get("trigger_reason")), "inline": False},
                        {"name": "Limitations", "value": str(alert.get("limitations")), "inline": False},
                    ],
                    "footer": {"text": f"Alert ID: {alert.get('id')} · Analysis Only · Live Trading Disabled"}
                }
                payload = {"content": "🔬 **BTCUSD research condition detected**", "embeds": [embed]}
            elif w_type == "discord" and "discord.com" in url:
                # Discord rich embed format
                dir_color = 0x00FF87 if alert.get("direction") == "LONG" else 0xFF3366
                embed = {
                    "title": f"{alert.get('tier_title')} — BTC {alert.get('direction')}",
                    "description": alert.get("rationale", "High-conviction trading opportunity detected."),
                    "color": dir_color,
                    "fields": [
                        {"name": "🎯 Direction", "value": f"**{alert.get('direction')}**", "inline": True},
                        {"name": "💵 Entry Price", "value": f"${alert.get('entry_price'):,}", "inline": True},
                        {"name": "🚀 Profit Target", "value": f"${alert.get('target_profit_price'):,} (+{alert.get('target_profit_pct')}%)", "inline": True},
                        {"name": "🛑 Stop Loss", "value": f"${alert.get('stop_loss_price'):,} (-{alert.get('risk_pct')}%)", "inline": True},
                        {"name": "⚖️ Risk/Reward", "value": alert.get("risk_reward_ratio", "2:1"), "inline": True},
                        {"name": "🔥 Opportunity Score", "value": f"**{alert.get('opportunity_score')}/100**", "inline": True}
                    ],
                    "footer": {"text": "BTCognitive High-Profit Radar"},
                    "timestamp": alert.get("timestamp")
                }
                payload = {"content": "🚨 **HIGH PROFIT ALERT DETECTED!** 🚨", "embeds": [embed]}
            else:
                # Generic webhook payload
                payload = alert

            res = await self._post_webhook(url, payload, addresses)
            if res.status_code < 300:
                return {"status": "delivered"}
            else:
                return {"status": "failed", "reason": f"Webhook returned HTTP {res.status_code}."}
        except Exception as e:
            return {"status": "failed", "reason": f"Webhook request failed ({type(e).__name__})."}

    async def _send_telegram_alert(self, alert: Dict[str, Any]):
        """Asynchronously sends Telegram Bot message using shared httpx client."""
        is_test = bool(alert.get("is_test"))
        is_research = bool(alert.get("is_research_alert") or alert.get("type") == "RESEARCH_CONDITION_ALERT")
        if not (is_test or is_research):
            return {
                "status": "blocked",
                "reason": "Production forecasts are unavailable; no market alert was sent.",
            }
        bot_token = self.settings.get("telegram_bot_token")
        chat_id = self.settings.get("telegram_chat_id")

        if not bot_token or not chat_id:
            return {"status": "not_configured", "reason": "Telegram bot token or chat ID is not configured."}

        if is_test:
            text = "*BTCognitive notification delivery test*\n\nThis is a test message, not a market signal."
        elif is_research:
            text = (
                f"🔬 *BTCUSD research condition detected*\n\n"
                f"📊 *Condition:* {alert.get('condition_name')}\n"
                f"💵 *Reference Price:* ${alert.get('reference_price_usd', 0):,.2f}\n"
                f"🕒 *Time (UTC):* {alert.get('timestamp')}\n"
                f"💡 *Hypothesis:* {alert.get('condition_hypothesis')}\n"
                f"⚡ *Reason:* {alert.get('trigger_reason')}\n\n"
                f"_{alert.get('limitations')}_\n"
                f"`Alert ID: {alert.get('id')}`"
            )
        else:
            text = (
                f"🚨 *{alert.get('tier_title')}*\n\n"
                f"⚡ *Direction:* {alert.get('direction')}\n"
                f"💵 *Entry:* ${alert.get('entry_price'):,}\n"
                f"🎯 *Target TP:* ${alert.get('target_profit_price'):,} (+{alert.get('target_profit_pct')}%)\n"
                f"🛑 *Stop Loss:* ${alert.get('stop_loss_price'):,} (-{alert.get('risk_pct')}%)\n"
                f"⚖️ *Risk/Reward:* {alert.get('risk_reward_ratio')}\n"
                f"💎 *Opportunity Score:* {alert.get('opportunity_score')}/100\n\n"
                f"_{alert.get('rationale')}_"
            )

        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
            client = get_shared_client()
            res = await client.post(url, json=payload, timeout=5.0)
            if res.status_code == 200 and res.json().get("ok") is True:
                return {"status": "delivered"}
            else:
                return {"status": "failed", "reason": f"Telegram API returned HTTP {res.status_code} or rejected the message."}
        except Exception as e:
            return {"status": "failed", "reason": f"Telegram request failed ({type(e).__name__})."}

    async def evaluate_research_conditions(
        self,
        market_data: Optional[Dict[str, Any]] = None,
        force: bool = False,
        ws_manager = None
    ) -> Dict[str, Any]:
        """
        BTCognitive V21 Research-Condition Alert Evaluator.
        Evaluates documented BTCUSD research conditions on genuine completed data.
        Enforces data freshness, non-execution boundaries, cooldown (15m), and deduplication.
        Records evaluation diagnostics on every execution path for operational visibility.
        """
        now_dt = datetime.now(timezone.utc)
        self.last_worker_heartbeat = now_dt.isoformat()

        def _finish(res_dict: Dict[str, Any]) -> Dict[str, Any]:
            self.last_worker_heartbeat = datetime.now(timezone.utc).isoformat()
            self.last_evaluation = {
                "timestamp": now_dt.isoformat(),
                **res_dict
            }
            return res_dict

        try:
            from api.routes_tournament import get_tournament_engine
            engine = get_tournament_engine()
        except Exception:
            try:
                from research.v12_strategy_tournament_engine import V12StrategyTournamentEngine
                engine = V12StrategyTournamentEngine()
            except Exception as exc:
                return _finish({
                    "status": "NO_ALERT",
                    "reason": "ENGINE_UNAVAILABLE",
                    "message": f"Strategy tournament engine unavailable ({type(exc).__name__})."
                })

        # Check dataset presence
        if engine.df_1h is None or len(engine.df_1h) < 200:
            return _finish({
                "status": "NO_ALERT",
                "reason": "DATA_UNAVAILABLE",
                "message": "Insufficient historical candles for research condition evaluation (<200 bars)."
            })

        latest_candle = engine.df_1h.iloc[-1]
        candle_ts = latest_candle["timestamp"]

        # Freshness verification
        try:
            c_dt = candle_ts.tz_convert(timezone.utc) if getattr(candle_ts, "tz", None) else candle_ts.tz_localize(timezone.utc)
            candle_age_sec = (now_dt - c_dt).total_seconds()
        except Exception:
            candle_age_sec = 0.0

        is_stale = candle_age_sec > 7200.0
        override_freshness = bool(market_data and market_data.get("override_freshness"))
        if is_stale and not override_freshness:
            return _finish({
                "status": "NO_ALERT",
                "reason": "STALE_MARKET_DATA",
                "candle_age_seconds": round(candle_age_sec, 1),
                "message": "Market data exceeds 2-hour freshness threshold; positive alerts rejected."
            })

        # Spot price determination
        spot_price = None
        if market_data and isinstance(market_data, dict):
            p = market_data.get("price") or market_data.get("price_usd")
            if p is not None:
                try:
                    p_val = float(p)
                    if math.isfinite(p_val) and p_val > 0:
                        spot_price = p_val
                except (ValueError, TypeError):
                    pass
        if spot_price is None:
            spot_price = float(latest_candle["close"])

        if spot_price <= 0 or not math.isfinite(spot_price):
            return _finish({
                "status": "NO_ALERT",
                "reason": "INVALID_REFERENCE_PRICE",
                "message": "No valid positive finite reference price available."
            })

        # Market regime
        regime_info = engine.get_current_market_regime()
        active_regime = regime_info.get("regime", "UNKNOWN")
        if active_regime in ("UNKNOWN", "TRANSITION_UNSUPPORTED"):
            return _finish({
                "status": "NO_ALERT",
                "reason": "UNSUPPORTED_REGIME",
                "active_regime": active_regime,
                "message": "Market regime is unconfirmed or unsupported; condition evaluation gated."
            })

        # Evaluate candidate research conditions
        detected_condition = None

        # Condition 1: Volatility-Compression Coiling (Bollinger Bandwidth 20-period compression)
        bbw = float(latest_candle.get("bbw_20", 0.0))
        bbw_pct = float(latest_candle.get("bbw_pct100", 50.0)) if "bbw_pct100" in latest_candle else 50.0
        is_compression = active_regime == "VOL_COMPRESSION_RANGE" or bbw_pct <= 20.0

        # Condition 2: Active Strategy Rule Triggered on Completed Bar
        strat_candidates = ["MTF_MOMENTUM_TREND", "VOL_COMPRESSION_BREAKOUT", "SHORT_HORIZON_MEAN_REVERSION"]
        triggered_strat = None
        for s_id in strat_candidates:
            setup = engine._evaluate_current_setup(s_id, regime_info)
            if setup.get("rule_trigger_status") == "TRIGGERED" and setup.get("is_regime_compatible"):
                triggered_strat = setup
                break

        if triggered_strat:
            s_name = triggered_strat.get("strategy_name", triggered_strat["strategy_id"])
            detected_condition = {
                "condition_id": f"STRAT_{triggered_strat['strategy_id']}",
                "name": f"STRATEGY_RULE_TRIGGERED ({s_name})",
                "hypothesis": f"Candidate research strategy {s_name} satisfied structural entry rules on completed 1h candle in {active_regime}.",
                "reason": f"Rule trigger satisfied under regime {active_regime} with reference spot ${spot_price:,.2f}."
            }
        elif is_compression:
            detected_condition = {
                "condition_id": "VOL_COMPRESSION_COILING",
                "name": "VOLATILITY_COMPRESSION_COILING",
                "hypothesis": "Hourly Bollinger Bandwidth indicates low-dispersion coiling; historical distribution models predict regime expansion.",
                "reason": f"BBW(20) = {bbw:.4f} in {active_regime} (compression percentile <= 20%)."
            }
        elif regime_info.get("hysteresis_status") == "CONFIRMED":
            detected_condition = {
                "condition_id": f"REGIME_{active_regime}",
                "name": f"REGIME_CONFIRMED ({active_regime})",
                "hypothesis": f"Causal Wilder ADX(14) and moving-average filter confirmed persistent 3-candle regime state: {active_regime}.",
                "reason": f"Regime confirmed with ADX(14) = {regime_info.get('adx_14', 0.0):.1f}."
            }

        if not detected_condition:
            return _finish({
                "status": "NO_ALERT",
                "reason": "CONDITIONS_EVALUATED_NONE_MET",
                "active_regime": active_regime,
                "reference_price_usd": round(spot_price, 2)
            })

        cond_id = detected_condition["condition_id"]
        # Deduplication & Cooldown Policy (15 minutes)
        now_epoch = time.time()
        try:
            candle_epoch = int(c_dt.timestamp())
        except Exception:
            candle_epoch = int(now_epoch)
        dedup_key = f"{cond_id}_{int(candle_epoch / 3600)}_{round(spot_price, -2)}"

        last_fired = self.condition_cooldowns.get(cond_id, 0.0)
        cooldown_rem = self.COOLDOWN_SECONDS - (now_epoch - last_fired)

        if not force:
            if cooldown_rem > 0:
                return _finish({
                    "status": "NO_ALERT",
                    "reason": "COOLDOWN_ACTIVE",
                    "condition_name": detected_condition["name"],
                    "cooldown_remaining_seconds": round(cooldown_rem, 1),
                    "last_alert_timestamp": datetime.fromtimestamp(last_fired, timezone.utc).isoformat()
                })
            if dedup_key in self.seen_dedup_hashes:
                return _finish({
                    "status": "NO_ALERT",
                    "reason": "DEDUPLICATED",
                    "condition_name": detected_condition["name"],
                    "message": "Condition already dispatched for this hourly interval."
                })

        # Build auditable alert payload
        dedup_hash = hashlib.sha256(dedup_key.encode()).hexdigest()[:8]
        alert_id = f"rc_{int(now_epoch)}_{dedup_hash}"

        alert_payload = {
            "id": alert_id,
            "type": "RESEARCH_CONDITION_ALERT",
            "tier": "RESEARCH_INTELLIGENCE",
            "tier_title": "BTCUSD research condition detected",
            "badge": "RESEARCH ONLY",
            "timestamp": now_dt.isoformat(),
            "reference_price_usd": round(spot_price, 2),
            "source": "Coinbase Spot OHLCV (Continuous Feed)",
            "data_freshness": "FRESH",
            "condition_name": detected_condition["name"],
            "condition_hypothesis": detected_condition["hypothesis"],
            "trigger_reason": detected_condition["reason"],
            "regime": active_regime,
            "limitations": "Descriptive market research only. Live trading and automated execution are permanently disabled. Not a guaranteed return or directional recommendation.",
            "is_research_alert": True,
            "governance": {
                "product_mode": "ANALYSIS_ONLY",
                "live_trading_enabled": False,
                "order_submission_enabled": False,
                "directional_recommendation_status": "DISABLED",
                "execution_status": "DISABLED_ANALYSIS_ONLY"
            }
        }

        # Update cooldown and deduplication state
        self.condition_cooldowns[cond_id] = now_epoch
        self.seen_dedup_hashes.add(dedup_key)
        self._save_alert_state()

        # Dispatch via all configured pathways
        dispatch_result = await self.dispatch_alert(alert_payload, ws_manager=ws_manager)
        return _finish({
            "status": "ALERT_DISPATCHED",
            "alert": alert_payload,
            "dispatch": dispatch_result
        })


notification_manager = NotificationManager()
