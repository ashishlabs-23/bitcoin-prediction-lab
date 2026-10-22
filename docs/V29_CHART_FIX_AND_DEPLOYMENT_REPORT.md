# BTCognitive V29 Session Report — AI Forecast Chart Repair & Production Deployment Guide

**Version:** 29.0.0  
**Session Date:** October 22, 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Baseline Commit:** `01f87ca`  
**Governed Policy:** `OFFLINE_RESEARCH_ONLY` · Live Trading `DISABLED`

---

## 1. Executive Summary

This session executed two core workstreams:

1. **AI Forecast Chart Repair:**
   - **Root Cause Identified:** `ChartTopBar` in `web/app.js` directly accessed properties on `latestIndicators` (`latestIndicators.rsi`, `.atr`, `.adx`, `.bbw`). In `App()`, `latestIndicators` is initialized via `useState(null)`. JavaScript ES6 default parameters (`latestIndicators = {}`) only fire on `undefined`, NOT on explicit `null`. Consequently, on initial component mount before indicator calculation callbacks fired, `ChartTopBar` threw `TypeError: Cannot read properties of null (reading 'rsi')`. This unhandled exception caused the React component tree to crash and unmount, leaving the chart container blank and preventing candlestick history and forecast diffusion overlays from rendering.
   - **Cache Invalidation:** In addition to the code fix (`const indicators = latestIndicators ?? {};`), the static asset version query parameters in `web/index.html` were bumped from `v=18.0.1` to `v=29.0.0` to invalidate the 24-hour HTTP cache (`max-age=86400`) enforced by `SecurityHeadersMiddleware`.
   - **Visual Research Guardrail:** The chart overlay status badge was updated to explicitly read:
     `● Forecast Active · 1h Persistence Baseline + Diffusion Bands (RESEARCH ONLY · LIVE TRADING DISABLED)`.
   - **Browser Verification:** Real browser sessions verified that the workstation renders with zero JavaScript errors, displays live Coinbase candles, renders the cyan dashed forecast persistence line and diffusion envelope, and reports live indicators (RSI 31.8, ATR $423.44, ADX 40.7, BBW 5.32%).

2. **Deployment Documentation & Reconciliation:**
   - Authored comprehensive [docs/DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) (12,000+ bytes) covering local setup (Windows/macOS/Linux), environment configuration, FastAPI runtime, static asset delivery, frontend test runner, Docker & Docker Compose, cloud deployments (Fly.io as recommended persistent container path, Render.com with `/ping` health check, Railway, Netlify SPA redirect), OWASP ASVS 5.0 security hardening, and troubleshooting.
   - Updated root [README.md](../README.md) with quickstart commands, direct links to the deployment guide, verified test suite commands, and clear epistemic distinctions between live market data, research baselines, and locked production trading.

---

## 2. Phase 0 — Repository Ground Truth & Environment

- **Git Root:** `c:\Projects\BTCognitive\BTCognitive`
- **Remote:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab.git` (origin)
- **Branch:** `main` (tracking `origin/main`)
- **Baseline Commit:** `01f87ca feat(validation): stages 2-12 validation integrity, causal calibration, and forward evaluation`
- **Runtime Environment:** Python 3.13 / FastAPI 0.111 / Uvicorn 0.30 / React 18 / TradingView Lightweight Charts 4.1.3

---

## 3. Phase 1 — Technical Forensics: AI Forecast Chart

### Data Flow Tracing
```
Coinbase Spot REST / WebSocket
          │
          ▼
engine/coinbase_15m_adapter.py (validates non-overlapping, strictly increasing 15m candles)
          │
          ▼
engine/forecast_engine_15m.py (generates empirical persistence baseline + sqrt-time scaled diffusion band)
          │
          ▼
api/market_monitor_routes.py (`/api/forecast/latest?horizon=15m`)
          │
          ▼
web/app.js (`api.fetchForecastLatest(interval)`)
          │
          ▼
LightweightCandleChart (`renderForecast` sets points & risk bands on series)
          │
          ▼
ChartTopBar (`latestIndicators` badge ribbon) ──[ CRASH: null.rsi ]──> React Tree Unmount
```

### The Fix
1. In `web/app.js` (`ChartTopBar`):
   ```javascript
   // Guard against null being passed explicitly (useState(null) bypasses default params)
   const indicators = latestIndicators ?? {};
   ```
   All references updated to use `indicators.rsi`, `indicators.atr`, `indicators.adx`, `indicators.bbw`.
2. In `web/app.js` (`LightweightCandleChart`):
   Cleared overlays on null/empty/failure (`setData([])`), and labeled the active forecast badge with `(RESEARCH ONLY · LIVE TRADING DISABLED)`.
3. In `web/index.html`:
   Bumped script and style queries:
   ```html
   <link rel="stylesheet" href="/styles.css?v=29.0.0" />
   <script src="/app.js?v=29.0.0"></script>
   ```

---

## 4. Phase 2 & 3 — Live Endpoint & Contract Verification

### 4.1 `/api/forecast/latest?horizon=15m`
- **Status:** `200 OK`
- **Payload:**
  - `status`: `"FORECAST_AVAILABLE_RESEARCH_ONLY"`
  - `forecast_id`: `"fc_15m_1792679400_1792680626"`
  - `reference_price`: `81765.95`
  - `points`: 5 timestamps (`1792679400`, `+900s`, `+1800s`, `+2700s`, `+3600s`)
  - `upper_band`: 5 points scaled by 15m Parkinson volatility
  - `lower_band`: 5 points scaled by 15m Parkinson volatility
  - `directional_signal`: `"ABSTAIN"`
  - `live_trading`: `"DISABLED"`

### 4.2 Health & Probes
- `/ping`: `{"pong": true, "timestamp": 1792680834}` (used by Render `render.yaml`)
- `/health`: `{"status": "ok", "product_mode": "ANALYSIS_ONLY", "research_status": "AUTHORIZED_FOR_PRODUCTION", ...}` (used by Fly.io and Docker)

---

## 5. Phase 6 — Test Suite & Red-Team Execution Evidence

### 5.1 Frontend Build & Unit Smoke Verification
```bash
node build_frontend.js
```
**Result:**
- Checking `web/app.js`... OK
- Checking `web_src/api_client.js`... OK
- Checking `web_src/websocket.js`... OK
- Checking `web_src/formatters.js`... OK
- Checking `tests_frontend.js`... OK
- Polling budget: 29.5 req/min (server limiter: 60 req/min) — PASSED
- **Exit Code: 0 (SUCCESS)**

### 5.2 Python Regression & Contract Gate
```bash
pytest tests/test_v10_market_data_and_forecast_chart.py \
       tests/test_frontend_contracts.py \
       tests/test_candle_manager.py \
       tests/test_v29_status_contract_and_decision_anatomy.py -v
```
**Result: 28 passed, 0 failures in 34.14s (Exit Code: 0)**
- `test_15m_dataset_and_manifest_exist` PASSED
- `test_15m_candles_strictly_increasing_and_aligned` PASSED
- `test_15m_forecast_contract_mathematics` PASSED
- `test_api_market_candles_15m` PASSED
- `test_api_forecast_latest_15m` PASSED
- `test_active_frontend_is_the_research_terminal_and_discloses_forecast_gate` PASSED
- `test_v29_service_online_but_forecast_blocked` PASSED
- `test_v29_status_contract_invariants` PASSED
- `test_v29_execution_endpoints_strictly_disabled` PASSED

### 5.3 Live Browser Verification
- **Tool:** Antigravity Browser Subagent
- **Target URL:** `http://127.0.0.1:8000/`
- **Observed Behavior:**
  - Page loaded cleanly with HTTP 200.
  - Zero unhandled console exceptions.
  - Live TradingView candlestick canvas active and animated.
  - Live indicator badges rendered: `RSI(14): 31.8`, `ATR(14): $423.44`, `ADX(14): 40.7`, `BBW: 5.32%`.
  - Forecast badge active: `● Forecast Active · 1h Persistence Baseline + Diffusion Bands (RESEARCH ONLY · LIVE TRADING DISABLED)`.

---

## 6. Governed Decisions

| Dimension | Verdict | Rationale |
|---|---|---|
| **Research Experiment** | `PASS` | Chart null-pointer defect eliminated; fail-closed contract behavior verified. |
| **Prospective Evidence** | `COLLECTING` | Forward evidence accumulation continues without live capital execution. |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` | Volatility baseline authorized for risk intelligence; directional models remain locked. |
| **Live Trading** | `DISABLED` | Permanently disabled across all code paths, endpoints, and containers. |
