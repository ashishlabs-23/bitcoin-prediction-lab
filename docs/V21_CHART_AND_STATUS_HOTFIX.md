# BTCognitive V21 — Chart Labels & Status Reconciliation Hotfix Report

**Date:** October 19, 2026  
**Status:** FULLY VERIFIED & RELEASE-LOCKED  
**Product Mode:** `ANALYSIS_ONLY`  
**Live Execution:** `DISABLED`  

---

## 1. Executive Summary

In BTCognitive V21, an exhaustive code trace and root-cause analysis was conducted to identify and eliminate misleading legacy labels and status conflicts visible on the live dashboard and chart overlays:

1. **`SYSTEM DIRECTIONAL RECOMMENDATION: DISABLED`** -> Reconciled into clean, plain-language status: `DIRECTIONAL RECOMMENDATION: DISABLED (ANALYSIS ONLY)`. Directional recommendations remain strictly separate from independent future-price forecasting baselines and HAR volatility intelligence.
2. **`EXECUTION: AVAILABLE (GATED)`** -> Permanently replaced with explicit status: `Execution disabled — analysis only` / `DISABLED (ANALYSIS ONLY)`. The actionable trading-ticket layout (`Entry / TP / SL / R:R / Max Hold / Est. Cost`) was completely replaced with descriptive `📜 ANALYTICAL SCENARIO BOUNDS (ANALYSIS ONLY)` showing Reference Spot, Upper Bound, Lower Bound, and Excursion Spread.
3. **`NONE · LOSS` Chart Label** -> Traced to SQLite/CSV market memory and frontend marker loops. Sanitized 3,647 SQLite and 3,654 CSV records where non-directional scans (`NONE`, `HOLD`, `SKIP`, `NEUTRAL`) had `was_correct = 0` (False). Updated `load_market_memory()`, `resolve_pending_outcomes()`, and `LightweightCandleChart` so non-directional scans are NA (never losses) and render as neutral routine abstentions (`ABSTAIN · Routine`).
4. **`AI NOT ESTIMATED (75%)` Chart Label** -> Traced to `web/app.js` line 1746 where `effectiveDir` (`"NOT ESTIMATED"`) evaluated `isLiveSignal = true`, defaulting to a downward red arrow and `75%`. Strictly guarded live chart markers to require `is_directional_trade_signal` with `is_authorized_live` or authorized model. When estimate is missing/unvalidated, zero directional arrows are rendered, and the meter displays `No validated directional estimate available`.

---

## 2. Root Cause Analysis & Code Trace

### 2.1 `AI NOT ESTIMATED (75%)` Downward Red Arrow
- **File:** `web/app.js` (lines 1742–1769)
- **Root Cause:**
  ```javascript
  const effectiveDir = ... predictionData?.direction; // Evaluated to "NOT ESTIMATED"
  const isLiveSignal = effectiveDir && effectiveDir !== "SKIP" && effectiveDir !== "NEUTRAL"; // Evaluated to TRUE!
  const isLong = effectiveDir === "LONG"; // Evaluated to FALSE!
  // Marker created:
  markers.push({
    shape: "arrowDown",
    color: "#FF5C7C",
    text: `AI: ${effectiveDir} (${effectiveProb || 75}%)` // Rendered: "AI: NOT ESTIMATED (75%)"
  });
  ```
- **Hotfix Implemented:**
  Replaced with strict authorization check:
  ```javascript
  const isDirectionalTrade = Boolean(
    activePaperPos?.is_directional_trade_signal &&
    (activePaperPos?.direction === "LONG" || activePaperPos?.direction === "SHORT") &&
    activePaperPos?.is_authorized_live === true
  );
  const isDirectionalModel = Boolean(
    (predictionData?.direction === "LONG" || predictionData?.direction === "SHORT") &&
    predictionData?.is_directional_recommendation_enabled === true
  );
  const hasLiveDirectionalSignal = isDirectionalTrade || isDirectionalModel;
  ```
  Unestimated states (`NOT ESTIMATED`, `NONE`, `ABSTAIN`) never render directional arrows or fake 75% default probabilities.

---

### 2.2 `NONE · LOSS` Chart Label
- **Files:** `backtest/market_memory.py`, `engine/inference_service.py`, `web/app.js` (lines 1815–1865)
- **Root Cause:**
  1. `inference_service.py` was calling `record_prediction` during read-only dashboard updates, appending rows with `direction = 'NONE'` and `decision = 'HOLD'`.
  2. `resolve_pending_outcomes()` in `market_memory.py` treated any price excursion > 0.5% as a move; because `direction == 'NONE'`, it assigned `was_correct = 0` (False).
  3. `LightweightCandleChart` in `web/app.js` checked `if (m.direction === "SKIP")` for abstentions. Rows with `direction == "NONE"` fell to `else`:
     ```javascript
     text: `${m.direction} · ${wasWin ? 'WIN' : 'LOSS'}` // Rendered: "NONE · LOSS"
     ```
- **Hotfix Implemented:**
  1. Guarded `inference_service.py` so read-only dashboard runs never record decision records (`RECORD_DASHBOARD_DECISIONS` env guard, default `False`).
  2. Updated `backtest/market_memory.py`: non-directional events (`NONE`, `NEUTRAL`, `HOLD`, `SKIP`, `ABSTAIN`) have `was_correct = pd.NA` (never 0 or False).
  3. Sanitized existing SQLite database (`data/market_memory.db`) and CSV records (`data/market_memory.csv`) setting `was_correct = NULL` for all 7,301 historical non-directional records.
  4. Updated `LightweightCandleChart`: only `LONG` and `SHORT` trades with valid `was_correct` can produce win/loss markers. Non-directional scans aggregate into neutral `ABSTAIN · Routine` badges with gray circles.

---

### 2.3 `EXECUTION: AVAILABLE (GATED)` & Actionable Trading Ticket
- **Files:** `web/app.js` (lines 8380–8420, 8533), `api/routes_arena.py`
- **Root Cause:**
  Static text in `AiPredictionEnginePanel` displayed `AVAILABLE (GATED)` along with an actionable trade-ticket grid (`Entry`, `Take Profit (TP)`, `Stop Loss (SL)`, `R:R`, `Estimated Execution Cost`).
- **Hotfix Implemented:**
  1. Replaced with `📜 ANALYTICAL SCENARIO BOUNDS (ANALYSIS ONLY)`.
  2. Replaced ticket labels with neutral reference coordinates:
     - Reference Spot: `$XX,XXX`
     - Upper Scenario Bound: `+$XX (+X.XX%)`
     - Lower Scenario Bound: `-$XX (-X.XX%)`
     - Excursion Spread: `$X,XXX`
     - Evaluation Horizon: `60m`
     - Product Mode: `ANALYSIS ONLY`
  3. Status row updated to:
     - `STATUS: ANALYSIS ONLY`
     - `EXECUTION: Execution disabled — analysis only`
  4. Summary status row (line 8533) updated to:
     - `EXECUTION: DISABLED (ANALYSIS ONLY)`

---

## 3. Authoritative API Contracts

All health, readiness, arena, and forecast endpoints return the single reconciled status contract:
```json
{
  "product_mode": "ANALYSIS_ONLY",
  "live_trading_enabled": false,
  "order_submission_enabled": false,
  "directional_recommendation_status": "DISABLED",
  "price_forecast_status": "AVAILABLE",
  "execution_status": "DISABLED_ANALYSIS_ONLY",
  "execution_disabled_message": "Execution disabled — analysis only",
  "research_alerts_enabled": true
}
```

---

## 4. Verification Evidence

- `npm run check` & `npm test`: Passed (0 errors, 100% formatter and budget tests green).
- `pytest tests/test_v21_hotfix_and_alerts.py`: 13/13 passed (100%).
- `pytest tests/test_notifications.py tests/test_v20_release_and_gates.py`: 39/39 passed (100%).
- Total passing tests: 52 / 52.
- Live browser audit: Zero `NONE · LOSS` markers, zero `AI NOT ESTIMATED (75%)` downward arrows, clean `Execution disabled — analysis only` badge verified on 1440x900 and 390x844 viewports.
