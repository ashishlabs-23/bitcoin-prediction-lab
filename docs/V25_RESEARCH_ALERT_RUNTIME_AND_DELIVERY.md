# BTCognitive V25 — Research Alert Runtime & Delivery Verification Audit

**Specialist Role:** Agent D (Alert Lifecycle Engineer)  
**Date:** 19 October 2026  
**Status:** Runtime Verification Complete — Operational Lifecycle Verified  
**Primary Modules Audited:**
- Lifespan Task: `api/server.py` (`_research_alert_worker`)
- Notification Engine: `api/notifications.py` (`NotificationManager`)
- Notification API Routes: `api/routes_notifications.py`
- Persisted State Store: `data/research_alert_state.json`

---

## 1. Executive Summary & Alert State Taxonomy

BTCognitive operates an autonomous, background-evaluated risk notification pipeline. A foundational principle is the strict separation between detecting a market condition and verifying that an external delivery channel successfully accepted a payload.

### Explicit Lifecycle State Taxonomy:

| Event State | Formal Definition | API / Log Representation |
| :--- | :--- | :--- |
| **`CONDITION_DETECTED`** | Market features met documented risk threshold on a closed hourly candle. | Stored in memory / evaluated event payload |
| **`BLOCKED_COOLDOWN`** | Event matched condition, but was suppressed because < 15 minutes elapsed since last alert. | `suppressed=True`, reason=`COOLDOWN_ACTIVE` |
| **`DISPATCH_ATTEMPTED`** | Event passed deduplication; delivery payload constructed and HTTP call initiated. | Logged in dispatch audit trail |
| **`DELIVERED`** | External webhook or bot returned HTTP 200/204 confirmation of message receipt. | `delivery_status="DELIVERED"` |
| **`NOT_CONFIGURED`** | No external webhook URL, Telegram token, or Slack hook provided in `.env`. | `delivery_status="NOT_CONFIGURED"` |
| **`FAILED`** | External endpoint returned HTTP 4xx/5xx or timed out after configured retries. | `delivery_status="FAILED"`, `error="..."` |

---

## 2. Lifespan Execution & Clean Teardown

1. **Single Worker Instance:** In `api/server.py`, the worker `_research_alert_worker()` is created strictly during FastAPI application startup inside the `@asynccontextmanager lifespan(app: FastAPI)` block. It runs on a 60-second loop.
2. **Clean Shutdown:** On application termination, the task is explicitly cancelled:
   ```python
   _research_alert_worker_task.cancel()
   await asyncio.gather(_research_alert_worker_task, return_exceptions=True)
   ```
   All pending event writes to `data/research_alert_state.json` are flushed before shutdown completes.

---

## 3. Cooldown & Deduplication Persistence

1. **15-Minute Cooldown Window:** Each condition type enforces a mandatory 900-second (15-minute) minimum cooldown. Repeated evaluations of the same price bar or sustained regime do not flood channels.
2. **Atomic Disk Serialization:** Alert state is serialized to `data/research_alert_state.json` using atomic replace (`tempfile` + `os.replace`).
3. **Restart Resilience:** On server reboot, `NotificationManager` reloads the last alert timestamp and event hashes from disk, guaranteeing that restarting the process cannot bypass cooldown or trigger duplicate notifications.

---

## 4. Truthful Channel Reporting & Credential Protection

1. **Truthful Channel State:** When channel credentials are not configured in environment variables, the system reports `NOT_CONFIGURED`. It never reports a mocked or simulated success as genuine external delivery.
2. **Credential Sanitization:** All sensitive credentials (webhook secrets, Telegram bot tokens, API keys) are redacted with `***` before serialization in `GET /api/notifications/status` and `GET /api/notifications/history`.
3. **Role-Based Access Control:** Manual trigger endpoints (`POST /api/notifications/test` and `POST /api/notifications/evaluate?force=true`) require valid `ADMIN` authorization header (`X-API-Key`). Unauthorized or reader keys are rejected with HTTP 403 Forbidden.

---

## 5. Non-Execution Commitment

Research alerts notify users of quantitative research conditions (e.g., elevated volatility compression, trend regime crossover). They are explicitly non-actionable, contain zero broker execution instructions, and never recommend placing live or paper trades.
