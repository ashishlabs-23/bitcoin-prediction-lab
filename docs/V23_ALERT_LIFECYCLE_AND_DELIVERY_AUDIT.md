# BTCognitive V23 — Research-Condition Alert Lifecycle & Notification Reliability Audit

**Version:** 1.0.0  
**Effective Date:** 19 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Scope:** Priority 4 end-to-end audit of condition evaluation, background lifespan scheduling, restart persistence, and channel delivery reporting.

---

## 1. Executive Summary

BTCognitive includes an automatic research-condition background worker designed to notify researchers when specific, well-defined quantitative conditions occur in fresh market data. It is an informational risk alert mechanism—not an automated trading bot or order dispatcher.

### Key Audit Findings:
1. **Lifespan Worker:** Successfully starts in `api/server.py` lifespan and evaluates conditions every 60 seconds on fresh completed candles.
2. **Deduplication & Cooldown:** Employs a 15-minute (900s) cooldown per condition and SHA-256 event fingerprinting to prevent alert fatigue.
3. **Restart Persistence:** Cooldown timestamps and seen hashes are persisted to `data/research_alert_state.json`, surviving application reboots.
4. **Fail-Closed Delivery Reporting:** When delivery channels (Webhook, Telegram, SMTP) are unconfigured in environment variables, the system truthfully returns `NOT_CONFIGURED` rather than fabricating success.
5. **RBAC Protection:** The manual bypass endpoint `/api/notifications/research-alerts/evaluate?force=true` strictly requires `UserRole.ADMIN`, returning HTTP 403 Forbidden to unauthorized requests.

---

## 2. Research Conditions Evaluated

The worker evaluates three documented quantitative research conditions:
1. **Hourly Volatility Compression (`volatility_compression`):**
   - Rationale: Realized variance below 15th historical percentile.
   - Purpose: Signals potential transition into an explosive excursion regime.
2. **Extreme Z-Score Price Stretch (`extreme_mean_reversion_deviation`):**
   - Rationale: Price deviation $> 3.0$ standard deviations from short-term rolling mean.
   - Purpose: Identifies high-excursion tail-risk boundaries.
3. **Confirmed High-Volatility Regime (`confirmed_high_vol_regime`):**
   - Rationale: Realized variance expansion above 85th percentile.
   - Purpose: Alerts researcher to wider uncertainty bounds on forecasts.

---

## 3. Condition-to-Alert Data Flow & Security Gates

```mermaid
graph TD
    TICK[Background Worker (60s)] --> FRESH{Fresh Market Data? (< 2h)}
    FRESH -- No --> REJECT[NO_ALERT: STALE_MARKET_DATA]
    FRESH -- Yes --> COND[Evaluate 3 Quantitative Conditions]
    COND --> DEDUP{Hash Seen or Cooldown Active?}
    DEDUP -- Yes --> SKIP[Suppress Duplicate Event]
    DEDUP -- No --> PERSIST[Save State to disk: research_alert_state.json]
    PERSIST --> DISPATCH[Dispatch to Channels]
    DISPATCH --> CHANNELS{Channels Configured?}
    CHANNELS -- No --> HONEST[Report NOT_CONFIGURED - No Mock Delivery]
    CHANNELS -- Yes --> EXT[Deliver External Webhook/Telegram/Email]
```

### Security & Non-Execution Invariants:
- **No Order Placement:** Alerts never trigger buy/sell orders, paper trades, or balance changes.
- **Fail-Closed Stale Check:** Data older than 2 hours is strictly rejected with reason `STALE_MARKET_DATA`.
- **Admin-Gated Force Route:** `POST /api/notifications/research-alerts/evaluate?force=true` returns HTTP 403 unless an admin API key is supplied.

---

## 4. Channel Configuration & Test Evidence

In the local evaluation environment:
- `WEBHOOK_URL`: Not configured $\to$ reports `NOT_CONFIGURED`.
- `TELEGRAM_BOT_TOKEN`: Not configured $\to$ reports `NOT_CONFIGURED`.
- `SMTP_HOST`: Not configured $\to$ reports `NOT_CONFIGURED`.
- `Browser In-App Alerts`: Enabled $\to$ dispatches via WebSocket to connected frontend clients.

*External Live Smoke Test Verdict:* `NOT EXECUTED — EXTERNAL CHANNELS NOT CONFIGURED IN WORKSPACE ENVIRONMENT`. This honest classification adheres to Epistemic Principle #5 (No Synthetic Fabrication).
