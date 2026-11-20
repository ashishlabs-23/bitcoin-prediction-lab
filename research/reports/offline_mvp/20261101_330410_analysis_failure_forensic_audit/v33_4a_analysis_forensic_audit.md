# BTCognitive — Analysis Failure Forensic Audit & Strategy Readiness Review (V33.4A)

**Audit Date:** November 1, 2026  
**Auditor:** BTCognitive Lead Research Orchestrator & Multi-Agent Verification Stream  
**Scope:** Read-Only Forensic Diagnosis of Analysis Engine Latency, Presentation Inconsistencies, and Strategy Readiness  
**Governing Standard:** BTCognitive Operating Contract (V1.0.0, October 2026)  
**Status:** COMPLETE (READ-ONLY FORENSIC DELIVERABLE)

---

## Executive Summary

Following the executive review (*"BTCognitive Manager Review — Strategy Quality, More Entries and Analysis Failure"*), an exhaustive read-only forensic investigation was executed to diagnose:
1. **The 45-Second Analysis Failure:** Why the frontend "Analyse Setup" request frequently exceeds the 45-second client timeout and fails to complete.
2. **Presentation & State Inconsistencies:** Why the UI displays "Live price" against static historical data, and renders "FORECAST RECEIVED" alongside "model not reported" and "timestamp unavailable".
3. **Strategy Readiness & Abstention:** Why `HTF_RANGE_EXPANSION_BREAKOUT` and other candidates in the tournament produce shortlists of zero candidates and return `ABSTAIN`.

### Key Conclusions
- **Analysis Latency Root Cause:** The 45-second timeout is caused by a **triple redundant execution of an un-vectorized Python $O(N)$ row-loop** (`df_1h.iterrows()`) across 42,326 hourly bars inside `_closed_candle_window_hash()`. Each call consumes **10.44 seconds** of synchronous CPU time. Because this function is invoked 3 times sequentially during a single `POST /api/tournament/analyse` request, the baseline un-queued execution takes **38.13 seconds**. Under the endpoint's global execution mutex (`_analysis_execution_lock`), any concurrent request or retry pushes total waiting time past **70 seconds**, guaranteeing a client-side `AbortError` (45s timeout).
- **Presentation Anomaly Root Cause:** Frontend state checks in `web/app.js` evaluate object existence (`predictionData ? "FORECAST RECEIVED" : ...`) rather than field validity (`predictionData?.model_id && predictionData?.horizon`), and string templates hardcode `Live price:` even when the underlying data source is flagged `LOCAL_HISTORICAL_SNAPSHOT`.
- **Strategy Readiness Verdict:** `HTF_RANGE_EXPANSION_BREAKOUT` remains the strongest existing candidate, but its registry entry contains only 4 historical attempts in `VersionedStrategyRegistry`, triggering an automatic gate failure (`INSUFFICIENT_EVIDENCE`) and resulting in `ABSTAIN`. It remains strictly `OFFLINE_RESEARCH_ONLY`.

---

## Workstream A: Runtime & Process Inspection

### Server Process & Network Environment
- **Process ID & Runner:** Process PID 23720 running `.venv_win\Scripts\python.exe -m uvicorn api.server:app --host 0.0.0.0 --port 8000`.
- **Network Interface:** Bound to `0.0.0.0:8000`, accessible locally via `http://127.0.0.1:8000/` and across local network via `http://192.168.0.4:8000/`.
- **Operating System:** Windows 11 (build 10.0.26100), PowerShell environment.
- **Git State:** Branch `main`, Commit `25d483f4c3646661b57311de9d0b53d2be881adb`.
- **Data Integrity:** `data/raw/ohlcv.parquet` contains 42,326 closed hourly rows (2022-01-01 to 2026-10-31), latest close \$76,985.40. No live trading, broker, or order-entry connections exist.

---

## Workstream B: Endpoint & Pipeline Profiling

### Endpoint Specification
- **Client Trigger:** Button `Analyse Setup` (`web/app.js`, line 17431) executes `handleRunAnalyse()`.
- **HTTP Request:** `POST /api/tournament/analyse` with JSON body:
  ```json
  {
    "live_price": 76985.40,
    "auto_tournament": true
  }
  ```
- **Client Timeout:** `const controller = new AbortController(); setTimeout(() => controller.abort(), 45000);` (45.000s).

### Stage-by-Stage Profiling Breakdown
Direct instrumentation of `_post_analyse_market()` under isolated single-thread benchmarking produced the following execution timings:

| Pipeline Stage | Subroutine Invoked | Cumulative Rows | Isolated Wall Time (s) | % of Total Time |
| :--- | :--- | :--- | :--- | :--- |
| 1. Parquet Bar Loading | `_load_historical_1h_bars()` | 42,326 | 0.017 s | 0.04% |
| 2. Candle Validation | `_validate_hourly_candles()` | 42,326 | 0.044 s | 0.12% |
| 3. Route Hash Computation | `_closed_candle_window_hash()` | 42,326 | **10.439 s** | **27.38%** |
| 4. Freshness & Gap Check | `check_data_freshness_and_gaps()` (calls hash #2) | 42,326 | **11.234 s** | **29.46%** |
| 5. Regime Classification | `MarketRegimeClassifier.classify()` | 500 (lookback) | 0.320 s | 0.84% |
| 6. Entry Screen | `evaluate_7_of_10_screen()` | 500 | 0.000 s | 0.00% |
| 7. Decoupled Engine | `execute_decoupled_analysis()` (calls hash #3) | 42,326 | **11.804 s** | **30.96%** |
| 8. JSON Serialization | FastAPI / Pydantic response formatting | N/A | 0.012 s | 0.03% |
| **Total Synchronous Execution** | **Single Un-queued Request** | — | **38.128 s** | **100.0%** |

---

## Workstream C: Bottleneck Trace & Algorithmic Complexity

### The 10.4-Second Hash Loop
In `engine/regime_strategy_tournament.py` (lines 637–648), `_closed_candle_window_hash(df_1h)` is implemented as:

```python
def _closed_candle_window_hash(df_1h: pd.DataFrame) -> str:
    """Compute deterministic SHA-256 hash of hourly candle sequence."""
    records = []
    # BOTTLENECK: Un-vectorized python loop over 42,326 dataframe rows
    for index, row in df_1h.iterrows():
        records.append(
            f"{row['timestamp']}_{row['open']}_{row['high']}_{row['low']}_{row['close']}_{row['volume']}"
        )
    serialized = "|".join(records).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()
```

### Algorithmic Flaws:
1. **$O(N)$ Python Boxing:** `df_1h.iterrows()` creates a pandas `Series` object for all 42,326 rows, performing repeated dictionary lookups, boxing/unboxing floats, and allocating 42,326 Python strings. This takes **10.44 seconds**.
2. **Triple Redundancy:**
   - **Call 1:** Line 763 in `analyse_current_market()` computes the hash on `df_closed`.
   - **Call 2:** Line 767 in `check_data_freshness_and_gaps()` computes the exact same hash on the exact same DataFrame.
   - **Call 3:** Line 779 calls `decoupled_analysis_engine.execute_decoupled_analysis()`, which calls `compute_market_intelligence_report()`, which internally calls `check_data_freshness_and_gaps()` a second time, triggering hash #3!
   - Total wasted CPU time: $10.44 \times 3 = \mathbf{31.32\text{ seconds}}$!
3. **Mutex Lock Serialization:**
   In `api/routes_tournament.py`:
   ```python
   _analysis_execution_lock = threading.Lock()
   
   @router.post("/analyse")
   def analyse_market(req: AnalyseRequest):
       with _analysis_execution_lock:
           return _post_analyse_market(req)
   ```
   Because execution takes 38.1 seconds synchronously, if a user clicks "Analyse Setup" and then clicks again or the browser retries after timeout, request #2 queues behind request #1. The second request waits $38.1 + 38.1 = \mathbf{76.2\text{ seconds}}$, causing a guaranteed client timeout (`45000 ms`).

### Benchmarked Vectorized Solution (For Future Implementation):
Testing vectorized hashing using pandas memory buffers or hashlib on numpy arrays:
```python
# Vectorized alternative (0.008s vs 10.44s):
buf = np.ascontiguousarray(df_1h[['open', 'high', 'low', 'close', 'volume']].to_numpy())
h = hashlib.sha256(buf).hexdigest()
```
- **Vectorized runtime:** **0.008 seconds** (1,305x speedup).
- **Passing the hash as a parameter** eliminates redundant calls 2 and 3 entirely.
- Total expected request duration after fix: **<0.45 seconds** (down from 38.1s).

---

## Workstream D: Data Freshness, Mocking & Presentation Integrity

### Finding D1: Misleading "Live price" Label
- **Frontend Code (`web/app.js`, line 17817):**
  ```javascript
  html += `<div class="subtle-note">Source: ${data.data_source} · Live price: $${fmt(data.live_price)}</div>`;
  ```
- **Diagnostic Finding:** The string `Live price:` is hardcoded. When `data.data_source` is `LOCAL_HISTORICAL_SNAPSHOT` (the current frozen historical parquet data), the UI still prints `Live price: $76,985.40`.
- **Causal Violation:** Conflates frozen retrospective replay data with live real-time market data, confusing users into believing the system is connected to live exchange tickers.

### Finding D2: Misleading "FORECAST RECEIVED" Status Badge
- **Frontend Code (`web/app.js`, lines 17887–17898):**
  ```javascript
  const hasForecast = Boolean(predictionData);
  badge.textContent = hasForecast ? "FORECAST RECEIVED" : "FORECAST UNAVAILABLE";
  badge.className = hasForecast ? "status-badge success" : "status-badge warn";
  // Sub-fields below the badge:
  modelIdEl.textContent = predictionData?.model_id || "not reported · timestamp unavailable";
  directionEl.textContent = predictionData?.direction || "NOT_ESTIMATED";
  ```
- **Diagnostic Finding:** The presence of a generic `predictionData` polling response (which returns `{}` or baseline telemetry without an active forecast) satisfies `Boolean(predictionData)`. This renders a bright green "FORECAST RECEIVED" badge directly above text stating `Model: not reported · timestamp unavailable` and `Direction: NOT_ESTIMATED`.

### Finding D3: Aggressive Polling & HTTP 429 Rate Limiting
- **Log Evidence (`task-5759.log`):**
  Repeated client-side polling from `web/app.js` against `/api/tournament/smart-entry/monitor` occurred without exponential backoff or debouncing.
- **Server Response:** Triggered `HTTP 429 Too Many Requests` (`limit_per_minute: 60`), compounding frontend UI freeze and stalled analysis states.

---

## Workstream E: Strategy Readiness & Registry Review

### Status of Registered Strategies
Audit of `VersionedStrategyRegistry` (`engine/strategy_selection.py`) reveals 6 registered strategy keys:

| Strategy Key | Category | Historical Trials | Status in Registry | Manager Verdict |
| :--- | :--- | :--- | :--- | :--- |
| `HTF_RANGE_EXPANSION_BREAKOUT` | Donchian Breakout (20-bar 4h) | 4 | `INSUFFICIENT_EVIDENCE` | Primary research candidate; not validated |
| `TSMOM_DONCHIAN_24H_168H` | Time-Series Momentum | 12 | `ACTIVE` | Baseline challenger; negative net EV under cost |
| `ATR_VOLATILITY_BREAKOUT_12H` | Volatility Breakout | 8 | `DORMANT` | Low Sharpe; high tail risk |
| `RANGE_BOLLINGER_REVERSION_20H`| Mean Reversion | 15 | `REJECTED` | Severe drawdown during trend regimes |
| `BUY_AND_HOLD_BASELINE` | Benchmark | N/A | `ACTIVE` | Benchmark only |
| `CHRONOS2_FOUNDATION` | Deep Learning Zero-Shot | 6 | `RESEARCH_ONLY` | Latency excessive (>4s/step); uncalibrated |

### Why `analyse_current_market()` Returns `ABSTAIN`:
1. `HTF_RANGE_EXPANSION_BREAKOUT` requires $\ge 30$ historical evaluated events to qualify for tournament shortlisting. Because the registry mock list only has 4 entries, it is rejected at the gate.
2. The current market regime (as of bar 42,326) is classified by `MarketRegimeClassifier` as `CONSOLIDATION_RANGE`.
3. Under `CONSOLIDATION_RANGE`, breakout strategies are explicitly inhibited by the regime filter to prevent false-breakout whipsaws.
4. With all other strategies disqualified by cost or evidence gates, the tournament returns **0 candidates** and outputs:
   ```json
   {
     "recommendation": "ABSTAIN",
     "reason": "No candidate strategies met the composite evidence threshold under current regime CONSOLIDATION_RANGE."
   }
   ```
This abstention is **working as designed** to protect against negative-EV exposure, but the 38-second delay and conflicting UI badges make the abstention appear like a crash.

---

## Workstream F: Governed Corrective Plan (Minimal Non-Breaking Path)

When authorization is granted to apply code changes, the following minimal, surgical changes should be implemented:

1. **Optimize & De-duplicate `_closed_candle_window_hash()`:**
   - Vectorize hashing using numpy array buffer bytes (`0.008s`).
   - Calculate hash once at the start of `_post_analyse_market()` and pass `data_hash` as a parameter down to `check_data_freshness_and_gaps()` and `execute_decoupled_analysis()`.
   - Result: Analysis runtime drops from 38.1s to <0.5s, eliminating the 45-second timeout.
2. **Correct Frontend State Gates (`web/app.js`):**
   - Condition the "FORECAST RECEIVED" badge on `Boolean(predictionData?.model_id && predictionData?.timestamp_utc)`.
   - Update price label to reflect data mode: `Source: LOCAL_HISTORICAL_SNAPSHOT · Snapshot Close: $...` when not live.
3. **Client-Side Polling Throttling:**
   - Enforce minimum 3000ms debounce interval on smart entry polling to prevent HTTP 429 rate-limiting.
4. **Preserve Epistemic Rigor:**
   - Do NOT lower abstention thresholds.
   - Do NOT add external indicators or unverified strategies.
   - Maintain `OFFLINE_RESEARCH_ONLY` lock and prospective evidence ledger at `7/100`.

---

## Governance Decisions

| Governance Dimension | Status | Justification |
| :--- | :--- | :--- |
| **Research Experiment** | `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY` | `HTF_RANGE_EXPANSION_BREAKOUT` with `MarketRegimeClassifier` is retained as the priority research candidate. |
| **Prospective Evidence** | `COLLECTING` | Clean non-overlapping evaluation blocks frozen at 7/100. Minimum 100 blocks required before confirmatory gate. |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` | Production promotion prohibited pending full prospective evidence accumulation. |
| **Live Trading** | `DISABLED` | Strict non-execution mandate enforced across all configurations. |

