# BTCognitive V33.4E — End-to-End Analysis Failure Investigation

**Document Reference:** `20261101_330800_v33_4e_e2e_analysis_failure_investigation.md`  
**Date:** November 1, 2026  
**Auditor / Lead Orchestrator:** BTCognitive Research & Epistemic Verification Team  
**Task Type:** Read-Only Diagnostic Investigation (Strictly Zero Fixes Implemented)  
**Governing Standard:** BTCognitive Research Operating Contract (V1.0.0)  

---

## 1. Executive Summary & Diagnostic Findings

This investigation was commissioned to diagnose why users report that dashboard Analysis is "failing or not working," despite recent backend performance optimizations. 

By executing native browser automation against the live application using Chrome DevTools Protocol (CDP), inspecting complete network lifecycles, and profiling React state hooks, we have conclusively identified the root causes.

| Audit Area | Investigation Method | Confirmed Forensic Finding | Status |
| :--- | :--- | :--- | :--- |
| **Part A: Runtime Verification** | Process & OpenAPI inspection | PID 16744, Git commit `25d483f`, Port 8000, App Version 3.0.0. 94 routes verified. | **VERIFIED** |
| **Part B: Real Dashboard Action** | Headless Chrome CDP automation | Button `#btn-analyse-setup` clicked. Dispatched `POST /api/tournament/analyse` (`80.49 ms`, `200 OK`). Rendered `"BACKTEST EVIDENCE UNAVAILABLE"`. | **CONFIRMED DEFECT & CAUSE IDENTIFIED** |
| **Part C: Polling Loop (F03)** | CDP network event tracking | Unstable `loadState` hook fires **207.4 requests/minute** in an infinite loop due to non-deterministic `decision_id` generation. | **CONFIRMED CRITICAL DEFECT** |
| **Part D: Forecast State (F04)** | Frontend AST & render audit | `PredictionPanel` defaults empty telemetry to `direction="SHORT"`, `probability=47.1%`, presenting unauthenticated telemetry as active. | **CONFIRMED DEFECT** |
| **Part D: Price Label (F05)** | Frontend DOM inspection | Historical offline bar close ($76,985.40 from Oct 30) is labelled `"Spot Market Price: Coinbase BTC/USD Feed"` and `"Live price"`. | **CONFIRMED DEFECT** |
| **Part E: Mutex Contention (F02)** | Concurrency matrix tests | When a fresh tournament backtest is triggered, `_analysis_execution_lock` is held for **~120 seconds**, causing 45s client aborts. | **CONFIRMED LATENT BOTTLENECK** |

---

## 2. Part A — Runtime Environment & State Recovery

- **Git Branch:** `main`
- **Git Commit SHA:** `25d483f4c3646661b57311de9d0b53d2be881adb`
- **Working Tree:** Uncommitted files preserved intact without modification or checkout.
- **Server Process ID:** `16744`
- **Command Line:** `"C:\Projects\BTCognitive\BTCognitive\.venv_win\Scripts\python.exe" -m uvicorn api.server:app --host 0.0.0.0 --port 8000`
- **Working Directory:** `C:\Projects\BTCognitive\BTCognitive`
- **Listening Interface:** `0.0.0.0:8000` (Listening on `127.0.0.1:8000` and LAN IP `192.168.0.4:8000`)
- **Process Owner:** `LAPTOP-12TNODNJ\Ashish`
- **Active Application Version:** `3.0.0`
- **Route Registration:** 94 total routes active and serving, including `/api/tournament/analyse` (POST), `/api/tournament/smart-entry/latest` (GET), and `/api/tournament/setup/{strategy_id}` (GET).
- **Process Boundaries:** Server and prospective collectors remained untouched; no restarts performed.

---

## 3. Part B — Live Browser Automation & End-to-End Analysis Action

Native browser automation was executed using headless Google Chrome (`130.0.6723.70`) via the Chrome DevTools Protocol over WebSockets against `http://127.0.0.1:8000/`.

### 3.1 Initial DOM & Navigation Trace
- Navigation link `#tab-btn-smart-entry` selected the Smart Entry workstation pane.
- Feed status displayed in DOM:  
  `"BTC-USD · 1h · Feed: Degraded source (LOCAL_HISTORICAL_SNAPSHOT) · Latest chart bar: 2026-10-30T13:00:00.000Z · Live price: $76,985.4"`
- Initial state text:  
  `"Ready to analyze the closed candles currently shown on the chart."`
- The user action button was identified as `<button id="btn-analyse-setup">🔬 Analyse Setup</button>`.

### 3.2 Single-Click Execution Evidence
At timestamp `T=0`, `#btn-analyse-setup` was clicked exactly once.

1. **Frontend Request Dispatched:**
   - **Method:** `POST`
   - **URL:** `http://127.0.0.1:8000/api/tournament/analyse`
   - **Request ID:** `e9463b8b-53e6-45a8-b5c3-0f6004ea2324`
   - **Payload Captured:**
     ```json
     {
       "instrument": "BTC-USD",
       "timeframe": "1h",
       "data_source": "LOCAL_HISTORICAL_SNAPSHOT",
       "request_id": "e9463b8b-53e6-45a8-b5c3-0f6004ea2324",
       "live_price": 76985.4,
       "enforce_freshness": false,
       "max_age_hours": 2,
       "candles": [168 closed hourly candles],
       "auto_tournament": true
     }
     ```
2. **Server Response Received:**
   - **HTTP Status:** `200 OK`
   - **Network Latency:** `80.49 ms`
   - **Internal Server Timings:** `total: 68.673 ms` (`analysis_screening: 68.608 ms`, `tournament_or_evidence_check: 0.043 ms`, `final_decision: 0.014 ms`)
   - **Payload Structure:**
     - `market_regime`: `VOLATILITY_EXPANSION`
     - `shortlisted_candidates`: 2 strategies (`HTF_RANGE_EXPANSION_BREAKOUT`, `VOL_COMPRESSION_BREAKOUT`)
     - `candidate_rejections`: 3 strategies
     - `tournament.final_verdict`: `"ABSTAIN"`
     - `tournament.execution_source`: `"CACHED_WALK_FORWARD_UNAVAILABLE"`
     - `decision.status`: `"NO_SMART_ENTRY"`
     - `decision.action`: `"ABSTAIN"`
     - `decision.reason`: `"No verified walk-forward manifest matches the registered candidate strategies and frozen protocol. A fresh three-arm evaluation is also unavailable because aligned point-in-time AI forecasts and a matched baseline series are not supplied. No arm metrics were computed or reused."`
3. **Frontend DOM State Rendered:**
   - **Progress Status:**  
     - `Validate closed candles: Complete`  
     - `Compute features/regime and rank candidates: Complete · 68.6 ms`  
     - `Verify or run eligible tournament: Not run — verified arm evidence unavailable · 0.0 ms`  
     - `Form final decision: Complete · 0.0 ms`  
     - `Request e9463b8b-53e6-45a8-b5c3-0f6004ea2324 · Total 68.7 ms`
   - **Outcome Heading:** `"BACKTEST EVIDENCE UNAVAILABLE"`
   - **Outcome Message:** `"No verified walk-forward manifest matches the registered candidate strategies and frozen protocol..."`
   - **Rejections Rendered:** `"Why candidates were rejected (3)"`

### 3.3 Repeat Request Verification (Step 9)
When `#btn-analyse-setup` was clicked a second time:
- A new request ID was generated: `a08b7add-75e4-4e54-bbe0-568d4e5ab415`.
- `POST /api/tournament/analyse` returned `200 OK` in **144.16 ms**.
- The UI updated identically with the new request ID and timings.

---

## 4. Part C — Polling & Runaway Request Investigation (F03)

### 4.1 Measured Polling Telemetry
Over a baseline observation window of **19.10 seconds**, the browser dispatched **66 HTTP API requests**:
- **Average Request Rate:** **3.46 requests / second**
- **Calculated Request Velocity:** **207.4 requests / minute**
- **Polled Endpoints Breakdown:**
  - `GET /api/tournament/smart-entry/evaluation`: **22 calls**
  - `GET /api/tournament/smart-entry/attempts`: **22 calls**
  - `GET /api/tournament/smart-entry/latest`: **22 calls**

### 4.2 Exact Root Cause Mechanism of the Polling Defect
In `web/app.js` (lines 17313–17363):

```javascript
  const loadState = useCallback(async () => {
    try {
      const [attRes, evRes, decRes] = await Promise.all([
        window.api.fetchSimulatedAttempts(),
        window.api.fetchSmartEntryEvaluation(),
        window.api.fetchSmartEntryLatest()
      ]);
      ...
      if (decRes) {
        if (!smartEntryDecision || decRes.action === "ABSTAIN" || decRes.status === "NO_SMART_ENTRY" || decRes.decision_id !== smartEntryDecision.decision_id) {
          setSmartEntryDecision(decRes);
        }
      }
    } catch (err) { ... }
  }, [smartEntryDecision, curPrice, predictionData]);

  useEffect(() => {
    loadState();
    const interval = setInterval(loadState, 8000);
    return () => clearInterval(interval);
  }, [loadState]);
```

1. **Non-Deterministic Backend Decision ID:**  
   Every single `GET /api/tournament/smart-entry/latest` calls `formulate_smart_entry_decision()`, which generates:
   `decision_id: f"dec_{hashlib.sha256(decision_ts.encode()).hexdigest()[:12]}"` based on `datetime.now(timezone.utc)`.
2. **Infinite Condition Trigger:**  
   Because `decision_id` is newly generated on every millisecond request, `decRes.decision_id !== smartEntryDecision.decision_id` is **always true**.
3. **State Mutation & Callback Re-creation:**  
   `setSmartEntryDecision(decRes)` is executed on every tick. This state change forces React to re-render `SmartEntrySimulatorView`.
4. **Interval Destruction & Instant Re-execution:**  
   Because `smartEntryDecision` is in `loadState`'s dependency array, `useCallback` creates a new function reference. This causes `useEffect` to execute its cleanup (`clearInterval`), immediately call `loadState()`, and schedule a new interval.
5. **Impact on User Experience:**  
   The application is trapped in an infinite loop firing 3 requests every ~800ms. In production environments behind Cloudflare or NGINX (with 60–120 req/min limits), this flood triggers **HTTP 429 Too Many Requests**, dropping user requests and breaking Analysis.

---

## 5. Part D — The Real Root Causes of Perceived "Analysis Failure"

Why does the user perceive that Analysis is "broken" or "failed"? We separate confirmed engineering facts from user perception:

### Defect 1: The "Failure" is Actually an "Abstain with Unavailable Evidence"
- When the user clicks "Analyse Setup", the backend executes perfectly in 80ms.
- However, because walk-forward evidence is unavailable offline, the engine adheres to strict safety invariants and returns:
  `action: "ABSTAIN"`, `status: "NO_SMART_ENTRY"`, `candidate_setup: None`.
- The UI renders a large banner reading **"BACKTEST EVIDENCE UNAVAILABLE"** and hides the proposal card.
- **User Perception:** The user clicks "Analyse Setup", sees a message about missing backtest evidence, and assumes the software threw an error or failed to run.

### Defect 2: Forecast State Telemetry Leakage (F04)
In `web/app.js` (lines 5164–5180, `PredictionPanel`):
```javascript
  const statusStr = predictionData?.status || "online";
  const probPct = predictionData?.probability_pct !== undefined ? predictionData.probability_pct : 47.1;
  const direction = predictionData?.direction || "SHORT";
  const setupName = predictionData?.setup_detected || "A1 (Liquidity Sweep / Reclaim)";
  const modelName = predictionData?.model || "LightGBM Meta-Model (B4)";
```
When `predictionData` is unauthenticated or empty, it falls back to hardcoded strings indicating a live meta-model predicting `SHORT` with `47.1%` probability. This gives the false impression of an active forecast when no model is authorized.

### Defect 3: Offline Historical Snapshot Labelled as Live Feed (F05)
In `HeroSection` (line 4417) and `SmartEntrySimulatorView` (line 17817):
- The close price of the final historical bar ($76,985.40 from October 30, 2026) is displayed under the labels:
  - `"Spot Market Price: Coinbase BTC/USD Feed: $76,985.40"`
  - `"Live price: $76,985.4"`
- Users observing a stationary price believe the feed has frozen or crashed.

---

## 6. Part E — Concurrency, Mutex Contention & 2-Minute Backtest Lock

### 6.1 Idempotency & RFC Standard Alignment
- **Same `request_id`, Same Payload:** Returns cached 200 OK instantaneously (RFC 9110).
- **Same `request_id`, Altered Payload:** Immediately rejected with **HTTP 409 Conflict** (RFC 9110 Section 15.5.10).
- **Unkeyed Rapid Debounce:** Dispatches within 10.0 seconds hit `_analysis_digest_cache` (0.0001s).

### 6.2 Latent Lock Contention Bottleneck (F02)
- While cached / short-screen analysis requests complete in ~70–80 ms, `POST /api/tournament/analyse` has a catastrophic latent serialization risk:
- When `force_fresh_tournament=True` is passed (or when an un-cached multi-year tournament runs), `run_strategy_tournament_backtest()` executes **synchronously** inside `_post_analyse_market()` under `_analysis_execution_lock`.
- Measured runtime of a fresh multi-year backtest across 42,326 bars: **~120 seconds (2 full minutes)**!
- During these 120 seconds, `_analysis_execution_lock` is held continuously.
- Any subsequent client request to `/api/tournament/analyse` is queued behind this mutex lock.
- Any client enforcing a 45-second timeout (including the UI's `AbortController` at 45s) **aborts and throws an `AbortError` timeout**.

---

## 7. Minimal Proposed Corrective Changes (Read-Only Plan)

The following changes are designed to resolve F02–F05 with minimal diffs and zero strategy contract changes:

1. **Fix F03 (Runaway Polling Loop):**
   - In `web/app.js`: Remove `smartEntryDecision` from `loadState`'s dependency array.
   - Use a React `useRef` for `smartEntryDecisionRef` to perform idempotency comparisons without triggering re-renders.
   - In `engine/regime_strategy_tournament.py`: Make `decision_id` deterministic by hashing the decision contents rather than the millisecond timestamp: `decision_id = f"dec_{hashlib.sha256(f'{action}_{reason}_{current_regime}'.encode()).hexdigest()[:12]}"`.
2. **Fix F04 (Forecast State Fallbacks):**
   - In `PredictionPanel`: If `predictionData` is null or unauthenticated, display an explicit `"FORECAST_UNAVAILABLE"` state. Remove hardcoded fallbacks (`47.1%`, `"SHORT"`, `"LightGBM Meta-Model"`).
3. **Fix F05 (Price & Data Source Labels):**
   - In `HeroSection` and `TerminalView`: When `data_source === "LOCAL_HISTORICAL_SNAPSHOT"`, label the price as `"Snapshot Close (Oct 30, 2026): $76,985.40"` instead of `"Spot Market Price: Coinbase BTC/USD Feed"`.
4. **Fix F02 (Async Tournament Offloading):**
   - Decouple synchronous 120s tournament backtesting from the immediate 80ms chart screening endpoint. Return screening results immediately with `tournament: "PENDING_OR_BACKGROUND"`, preventing `_analysis_execution_lock` from blocking the server for 2 minutes.

---

## 8. Governed Four-Point Decision Handover

```
1. Research Experiment:    RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY
                           HTF_RANGE_EXPANSION_BREAKOUT with MarketRegimeClassifier retained
                           as priority research candidate; production promotion prohibited.

2. Prospective Evidence:   FROZEN_PENDING_ACTIVATION
                           Conformal volatility ledger frozen at 7 blocks (SHA-256: ee58b37c...).
                           HTF prospective shadow ledger inactive (0 blocks).

3. Model Authorization:    OFFLINE_RESEARCH_ONLY
                           Governed strictly under offline research contracts.

4. Live Trading:           DISABLED
                           Strict non-execution guardrails enforced.
```

