import os
import json
import time
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

    def get_settings(self) -> Dict[str, Any]:
        settings = self.settings.copy()
        for key in (
            "smtp_password",
            "smtp_user",
            "smtp_from",
            "email_recipient",
            "telegram_bot_token",
            "webhook_url",
        ):
            settings.pop(key, None)
        settings["smtp_password_configured"] = bool(self.settings.get("smtp_password"))
        settings["email_configured"] = bool(
            self.settings.get("smtp_user") and self.settings.get("smtp_password")
        )
        settings["telegram_bot_token_configured"] = bool(self.settings.get("telegram_bot_token"))
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

    async def dispatch_alert(self, alert_payload: Dict[str, Any], ws_manager=None) -> Dict[str, Any]:
        """Dispatch neutral delivery tests; market signals remain blocked until validated."""
        if not alert_payload.get("is_test"):
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
                ws_msg = {
                    "type": "HIGH_PROFIT_ALERT",
                    "data": alert_payload,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await ws_manager.broadcast(json.dumps(ws_msg))
                channels["websocket"] = {"status": "delivered"}
            except Exception as e:
                channels["websocket"] = {"status": "failed", "reason": type(e).__name__}
        else:
            channels["websocket"] = {"status": "not_configured"}

        if self.settings.get("email_enabled"):
            channels["email"] = await self._send_email_alert(alert_payload)
        else:
            channels["email"] = {"status": "disabled"}

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

    async def _send_email_alert(self, alert: Dict[str, Any]):
        """Asynchronously formats and sends rich HTML email alert to user(s)."""
        if alert.get("is_test"):
            return await self._send_test_email_alert(alert)
        return {
            "status": "blocked",
            "reason": "Production forecasts are unavailable; no market alert was sent.",
        }

        raw_recipients = self.settings.get("email_recipient", "")
        recipients = [r.strip() for r in raw_recipients.split(",") if r.strip()] if isinstance(raw_recipients, str) else list(raw_recipients)
        
        if not recipients:
            return {"status": "not_configured", "reason": "No email recipient is configured."}

        smtp_host = self.settings.get("smtp_host", "smtp.gmail.com")
        smtp_port = int(self.settings.get("smtp_port", 587))
        smtp_user = self.settings.get("smtp_user", "")
        smtp_password = self.settings.get("smtp_password", "").replace(" ", "").strip()
        smtp_from = self.settings.get("smtp_from", smtp_user)

        direction = alert.get("direction", "LONG")
        is_long = direction == "LONG"
        dir_color = "#00E5A8" if is_long else "#FF5C7C"
        dir_symbol = "🚀 BUY / LONG" if is_long else "🔻 SELL / SHORT"

        subject = f"⚡ [BTCognitive Signal] BTC {direction} (+{alert.get('target_profit_pct')}%) | {alert.get('tier_title', 'Opportunity Alert')}"
        recipient_str = ", ".join(recipients)

        ts_now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        regime_label = alert.get('regime', 'NORMAL')
        score_val = alert.get('opportunity_score', 85)
        rr_val = alert.get('risk_reward_ratio', '2.0 : 1')
        entry_p = alert.get('entry_price', 0)
        tp_p = alert.get('target_profit_price', 0)
        sl_p = alert.get('stop_loss_price', 0)
        tp_pct = alert.get('target_profit_pct', 2.0)
        sl_pct = alert.get('risk_pct', 1.0)
        rationale_text = alert.get('rationale', 'Adaptive AI Regime model identified asymmetric risk-adjusted opportunity.')

        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BTCognitive Institutional Signal</title>
<style>
  body {{ margin: 0; padding: 0; background-color: #040711; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #F1F5F9; -webkit-font-smoothing: antialiased; }}
  .email-wrapper {{ width: 100%; background-color: #040711; padding: 32px 12px; }}
  .email-container {{ max-width: 620px; margin: 0 auto; background: #0B1120; border: 1px solid #1E293B; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7); }}
  .header-bar {{ background: linear-gradient(90deg, #0d172e, #131d38); padding: 20px 24px; border-bottom: 1px solid #1E293B; }}
  .header-brand {{ font-size: 19px; font-weight: 800; color: #00F0FF; letter-spacing: -0.02em; }}
  .header-sub {{ font-size: 11px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 2px; }}
  .badge-tag {{ display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; background: rgba(0, 240, 255, 0.12); color: #00F0FF; border: 1px solid rgba(0, 240, 255, 0.3); }}
  
  .hero-signal {{ padding: 24px; text-align: center; background: radial-gradient(circle at center, rgba(0, 229, 168, 0.08) 0%, rgba(11, 17, 32, 0) 70%); border-bottom: 1px solid #1E293B; }}
  .signal-pill {{ display: inline-block; padding: 8px 18px; border-radius: 30px; font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; background: {dir_color}18; color: {dir_color}; border: 1.5px solid {dir_color}; }}
  .signal-price {{ font-size: 32px; font-weight: 800; color: #FFFFFF; font-family: 'JetBrains Mono', 'Courier New', monospace; margin-top: 12px; }}
  .signal-sub {{ font-size: 13px; color: #94A3B8; margin-top: 4px; }}
  
  .content-body {{ padding: 24px; }}
  .narrative-box {{ background: rgba(255, 255, 255, 0.03); border-left: 3px solid #00F0FF; padding: 14px 16px; border-radius: 0 8px 8px 0; font-size: 13px; line-height: 1.6; color: #CBD5E1; margin-bottom: 24px; }}
  
  .kpi-grid {{ width: 100%; border-collapse: separate; border-spacing: 10px; margin-bottom: 24px; }}
  .kpi-card {{ background: rgba(15, 23, 42, 0.8); border: 1px solid #1E293B; border-radius: 10px; padding: 14px; text-align: left; vertical-align: top; }}
  .kpi-label {{ font-size: 11px; text-transform: uppercase; color: #94A3B8; font-weight: 600; letter-spacing: 0.04em; margin-bottom: 4px; }}
  .kpi-value {{ font-size: 18px; font-weight: 700; color: #FFFFFF; font-family: 'JetBrains Mono', 'Courier New', monospace; }}
  
  .cta-block {{ text-align: center; margin-top: 10px; margin-bottom: 24px; }}
  .btn-primary {{ display: inline-block; width: 88%; background: linear-gradient(135deg, #00F0FF 0%, #00E5A8 100%); color: #040711 !important; font-weight: 800; font-size: 15px; text-align: center; text-decoration: none; padding: 15px 24px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0, 240, 255, 0.3); }}
  
  .audit-bar {{ background: rgba(0, 0, 0, 0.35); border-top: 1px solid #1E293B; padding: 16px 24px; font-size: 11px; color: #64748B; line-height: 1.5; }}
  .audit-row {{ display: flex; justify-content: space-between; margin-bottom: 4px; }}
</style>
</head>
<body>
<div class="email-wrapper">
  <div class="email-container">
    
    <!-- Top Header -->
    <div class="header-bar">
      <table width="100%" border="0" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <div class="header-brand">⚡ BTCognitive</div>
            <div class="header-sub">Adaptive Quantitative Intelligence</div>
          </td>
          <td align="right">
            <span class="badge-tag">💎 {alert.get('tier_title', 'ALPHA SIGNAL')}</span>
          </td>
        </tr>
      </table>
    </div>

    <!-- Signal Banner -->
    <div class="hero-signal">
      <div class="signal-pill">{dir_symbol}</div>
      <div class="signal-price">${entry_p:,.2f}</div>
      <div class="signal-sub">BTC / USD · Binance Coin-M & Coinbase Reference</div>
    </div>

    <!-- Main Content -->
    <div class="content-body">
      <div class="narrative-box">
        <strong style="color: #F8FAFC;">Executive Rationale:</strong><br>
        {rationale_text}
      </div>

      <!-- Key Execution Parameters Grid -->
      <table class="kpi-grid" width="100%">
        <tr>
          <td class="kpi-card" width="50%" style="border-left: 3px solid #00E5A8;">
            <div class="kpi-label">🎯 Take-Profit Target</div>
            <div class="kpi-value" style="color: #00E5A8;">${tp_p:,.2f}</div>
            <div style="font-size: 11px; color: #00E5A8; margin-top: 2px;">+{tp_pct}% · 2.0x ATR Exit</div>
          </td>
          <td class="kpi-card" width="50%" style="border-left: 3px solid #FF5C7C;">
            <div class="kpi-label">🛑 Invalidation Stop-Loss</div>
            <div class="kpi-value" style="color: #FF5C7C;">${sl_p:,.2f}</div>
            <div style="font-size: 11px; color: #FF5C7C; margin-top: 2px;">-{sl_pct}% · 1.5x ATR Protection</div>
          </td>
        </tr>
        <tr>
          <td class="kpi-card" width="50%">
            <div class="kpi-label">⚖️ Risk / Reward Multiple</div>
            <div class="kpi-value" style="color: #00F0FF;">{rr_val}</div>
            <div style="font-size: 11px; color: #94A3B8; margin-top: 2px;">Asymmetric Alpha Hurdle</div>
          </td>
          <td class="kpi-card" width="50%">
            <div class="kpi-label">⭐ Opportunity Score</div>
            <div class="kpi-value" style="color: #FFD700;">{score_val} <span style="font-size: 12px; color: #94A3B8;">/ 100</span></div>
            <div style="font-size: 11px; color: #94A3B8; margin-top: 2px;">4-Factor Calibrated</div>
          </td>
        </tr>
        <tr>
          <td class="kpi-card" width="50%">
            <div class="kpi-label">📊 Market Regime</div>
            <div class="kpi-value" style="font-size: 15px; color: #A78BFA;">{regime_label}</div>
            <div style="font-size: 11px; color: #94A3B8; margin-top: 2px;">Entropy Filter Passed</div>
          </td>
          <td class="kpi-card" width="50%">
            <div class="kpi-label">🛡️ Net Alpha Drag</div>
            <div class="kpi-value" style="font-size: 15px; color: #F8FAFC;">10.0 bps</div>
            <div style="font-size: 11px; color: #94A3B8; margin-top: 2px;">Fee (5bps) + Slip (5bps)</div>
          </td>
        </tr>
      </table>

      <!-- CTA Button -->
      <div class="cta-block">
        <a href="http://127.0.0.1:8000/#/terminal" class="btn-primary">⚡ Open Trading Terminal & Review Matrix</a>
      </div>
    </div>

    <!-- Institutional Footer & Audit -->
    <div class="audit-bar">
      <table width="100%">
        <tr>
          <td>Timestamp: <b>{ts_now_str}</b></td>
          <td align="right">Model: <b>Ensemble RF + XGB v2.1</b></td>
        </tr>
      </table>
      <div style="margin-top: 8px; color: #475569; font-size: 10px;">
        CONFIDENTIAL & PROPRIETARY — Automated alert dispatched to {recipient_str}. Simulated paper-trading environment. Past performance does not guarantee future results.
      </div>
    </div>

  </div>
</div>
</body>
</html>
"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = recipient_str
        msg.attach(MIMEText(html_body, "html"))

        print(f"[EMAIL] Triggered High-Profit Alert to {recipient_str} | Direction: {direction} | Profit Target: +{alert.get('target_profit_pct')}%")

        # If SMTP credentials are provided, send via SMTP server
        if smtp_user and smtp_password:
            try:
                loop = asyncio.get_running_loop()
                def _send():
                    with smtplib.SMTP(smtp_host, smtp_port) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_password)
                        server.sendmail(smtp_from, recipients, msg.as_string())
                await loop.run_in_executor(None, _send)
                print(f"[EMAIL SUCCESS] Delivered email alert to {recipient_str} via {smtp_host}:{smtp_port}")
                return {"status": "delivered"}
            except Exception as e:
                print(f"[EMAIL WARNING] SMTP Delivery error via {smtp_host}:{smtp_port}: {e}")
                return {"status": "failed", "reason": f"SMTP delivery failed ({type(e).__name__})."}
        else:
            return {"status": "not_configured", "reason": "SMTP credentials are not configured."}

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
        if not alert.get("is_test"):
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
            if alert.get("is_test") and w_type == "discord" and "discord.com" in url:
                embed = {
                    "title": "BTCognitive notification delivery test",
                    "description": alert.get("rationale", "Test only; not a market signal."),
                    "color": 0x00F0FF,
                    "footer": {"text": "Test message · no market signal"}
                }
                payload = {"content": "BTCognitive test message; this is not a trading signal.", "embeds": [embed]}
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
        if not alert.get("is_test"):
            return {
                "status": "blocked",
                "reason": "Production forecasts are unavailable; no market alert was sent.",
            }
        bot_token = self.settings.get("telegram_bot_token")
        chat_id = self.settings.get("telegram_chat_id")

        if not bot_token or not chat_id:
            return {"status": "not_configured", "reason": "Telegram bot token or chat ID is not configured."}

        if alert.get("is_test"):
            text = "*BTCognitive notification delivery test*\n\nThis is a test message, not a market signal."
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


notification_manager = NotificationManager()
