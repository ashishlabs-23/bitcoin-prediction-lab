import os
import json
import time
import urllib.request
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class NotificationManager:
    """
    Manages delivery of high-profit opportunity notifications across channels
    (Gmail SMTP, WebSockets, Browser Desktop Push, Discord, Telegram, Webhooks).
    """

    def __init__(self):
        self._load_env_file()
        
        smtp_user = os.getenv("SMTP_USER", "manuashi2018@gmail.com")
        smtp_pw = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()
        smtp_from = os.getenv("SMTP_FROM", smtp_user or "manuashi2018@gmail.com")

        self.settings = {
            "browser_alerts_enabled": True,
            "sound_alerts_enabled": True,
            "min_profit_threshold_pct": 1.5,
            "min_opportunity_score": 75,
            "email_enabled": True,
            "email_recipient": os.getenv("EMAIL_RECIPIENT", "manuashi2018@gmail.com"),
            "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", 587)),
            "smtp_user": smtp_user,
            "smtp_password": smtp_pw,
            "smtp_from": smtp_from,
            "webhook_enabled": False,
            "webhook_url": "",
            "webhook_type": "discord",  # "discord", "telegram", "generic"
            "telegram_bot_token": "",
            "telegram_chat_id": ""
        }
        self.recent_alerts: List[Dict[str, Any]] = []

    def _load_env_file(self):
        """Loads .env file into os.environ if present."""
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception as e:
                print(f"Error loading .env file: {e}")

    def get_settings(self) -> Dict[str, Any]:
        return self.settings.copy()

    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in new_settings.items():
            if k in self.settings:
                self.settings[k] = v
        return self.settings.copy()

    def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(reversed(self.recent_alerts[-limit:]))

    def record_alert(self, alert_payload: Dict[str, Any]):
        self.recent_alerts.append(alert_payload)
        if len(self.recent_alerts) > 100:
            self.recent_alerts.pop(0)

    async def dispatch_alert(self, alert_payload: Dict[str, Any], ws_manager=None) -> Dict[str, Any]:
        """
        Dispatches alert across configured channels:
        1. In-memory history
        2. WebSocket broadcast
        3. Email to user (manuashi2018@gmail.com)
        4. Webhooks (Discord / Telegram / Custom HTTP)
        """
        self.record_alert(alert_payload)

        # 1. WebSocket broadcast if manager provided
        if ws_manager is not None:
            try:
                ws_msg = {
                    "type": "HIGH_PROFIT_ALERT",
                    "data": alert_payload,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await ws_manager.broadcast(json.dumps(ws_msg))
            except Exception as e:
                print(f"Error broadcasting alert over WebSocket: {e}")

        # 2. Email dispatch to user (manuashi2018@gmail.com)
        if self.settings.get("email_enabled") and self.settings.get("email_recipient"):
            asyncio.create_task(self._send_email_alert(alert_payload))

        # 3. Webhook / External Notification
        if self.settings.get("webhook_enabled") and self.settings.get("webhook_url"):
            asyncio.create_task(self._send_external_webhook(alert_payload))

        if self.settings.get("telegram_bot_token") and self.settings.get("telegram_chat_id"):
            asyncio.create_task(self._send_telegram_alert(alert_payload))

        return {"status": "dispatched", "alert_id": alert_payload.get("id")}

    async def _send_email_alert(self, alert: Dict[str, Any]):
        """Asynchronously formats and sends rich HTML email alert to user(s)."""
        raw_recipients = self.settings.get("email_recipient", "manuashi2018@gmail.com, amshithv24cs@rnsit.ac.in")
        recipients = [r.strip() for r in raw_recipients.split(",") if r.strip()] if isinstance(raw_recipients, str) else list(raw_recipients)
        
        if not recipients:
            return

        smtp_host = self.settings.get("smtp_host", "smtp.gmail.com")
        smtp_port = int(self.settings.get("smtp_port", 587))
        smtp_user = self.settings.get("smtp_user", "manuashi2018@gmail.com")
        smtp_password = self.settings.get("smtp_password", "").replace(" ", "").strip()
        smtp_from = self.settings.get("smtp_from", smtp_user or "manuashi2018@gmail.com")

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
            except Exception as e:
                print(f"[EMAIL WARNING] SMTP Delivery error via {smtp_host}:{smtp_port}: {e}")
        else:
            print(f"[EMAIL QUEUED] Email formatted and ready for {recipient_str}. (To send live, set SMTP_PASSWORD in .env or Settings modal).")

    async def _send_external_webhook(self, alert: Dict[str, Any]):
        """Asynchronously sends Discord or generic HTTP webhook."""
        url = self.settings.get("webhook_url")
        w_type = self.settings.get("webhook_type", "discord")

        try:
            if w_type == "discord" and "discord.com" in url:
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
                payload = {"content": f"🚨 **HIGH PROFIT ALERT DETECTED!** 🚨", "embeds": [embed]}
            else:
                # Generic webhook payload
                payload = alert

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "BTCognitive/2.0"})
            
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=5))
            print(f"Webhook notification delivered to {url}")
        except Exception as e:
            print(f"Error sending webhook notification: {e}")

    async def _send_telegram_alert(self, alert: Dict[str, Any]):
        """Asynchronously sends Telegram Bot message."""
        bot_token = self.settings.get("telegram_bot_token")
        chat_id = self.settings.get("telegram_chat_id")

        if not bot_token or not chat_id:
            return

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
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=5))
            print("Telegram notification delivered successfully.")
        except Exception as e:
            print(f"Error sending Telegram notification: {e}")


notification_manager = NotificationManager()
