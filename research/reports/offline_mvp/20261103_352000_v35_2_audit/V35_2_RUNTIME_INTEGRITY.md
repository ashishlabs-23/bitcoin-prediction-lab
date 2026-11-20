# V35.2 Milestone Audit Report — Runtime and API Integrity
**Target Workspace:** `c:\Projects\BTCognitive\BTCognitive`  
**Auditor:** Agent 1 — Runtime & API Integrity Specialist  
**Status:** Audit Complete — All Critical Verification Gates Validated  

---

### Executive Summary

An exhaustive, read-only audit of the complete operational Analysis path in BTCognitive was executed. The inspection traced data flow from upstream exchange network acquisition (Bitstamp public REST API) through the Python backend services (`BitstampMarketDataService`, `DecoupledAnalysisEngine`, `HTFSetupDetector`, `RegimeStrategyTournament`, `FastAPI` server routes) to frontend browser request handling and DOM rendering (`web/app.js`, `web/index.html`).

All 11 failure-injection test modes in `tests/test_v33_8_failure_injection.py`, 10 Bitstamp unit tests in `tests/test_v33_7_bitstamp_integration.py`, 13 HTF setup tests in `tests/test_v33_4m_htf_analysis.py`, and 4 analysis reliability tests in `tests/test_v33_5_analysis_reliability.py` passed with 100% success.

---

### 1. Bitstamp Market-Data Service Architecture & Flow (`engine/bitstamp_market_data_service.py`)

- **Public Endpoint:** Official public market-data REST endpoint:
  `GET https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=3600&limit=1000&exclude_current_candle=true`
- **Transport & TLS Protocol:**
  - *Windows Environment:* Executes `powershell.exe` with `[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12` using the native Windows SChannel TLS 1.2 stack. This cleanly negotiates Imperva Incapsula WAF fingerprint checks that block standard Python OpenSSL/Requests handshakes.
  - *Non-Windows Environment:* Falls back to `httpx.Client(timeout=30.0)` with standard headers.
- **9-Point Multi-Stage Data Validation (`validate_bitstamp_ohlc`):**
  1. *Pair Verification:* Verifies pair is `BTCUSD` or `BTC/USD`.
  2. *Structure Integrity:* Asserts non-empty `ohlc` list.
  3. *Numeric Coercion:* Validates finite positive numeric values for `open`, `high`, `low`, `close`, and non-negative `volume`.
  4. *Positivity Check:* Rejects non-positive price observations ($P \le 0$).
  5. *OHLC Geometric Extrema:* Rejects candles where $High < \max(Open, Close)$, $Low > \min(Open, Close)$, or $High < Low$.
  6. *Completed Candle Invariant:* Asserts $(t_{\text{open}} + 3600) \le t_{\text{retrieval}} + 120s$, strictly rejecting unclosed or in-progress hourly candles.
  7. *Strict Monotonic Ascending:* Rejects out-of-order timestamps ($t_{\text{curr}} \le t_{\text{prev}}$).
  8. *Contiguity / Gap Detection:* Asserts consecutive candle timestamp delta strictly equals 3600 seconds; flags any missing hourly intervals.
  9. *Zero Duplicates:* Strictly rejects duplicate candle timestamps.
- **Source Separation & Atomic Persistence:**
  - Saves validated dataset to `data/providers/bitstamp/BTCUSD_1h.parquet` and metadata to `data/providers/bitstamp/provenance.json`.
  - Atomic file write: writes to temporary files (`.tmp`) before atomic `os.replace`.
  - **Zero Mutation Invariant:** `data/raw/ohlcv.parquet` (Coinbase historical dataset) SHA-256 (`ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`) is completely untouched and isolated.

---

### 2. On-Demand Refresh Mechanism and Cache Behavior

- **Cache TTL & Thread Safety:**
  - In-memory cache TTL: `BITSTAMP_CACHE_TTL_SECONDS = 120.0` (2 minutes).
  - Synchronized via `self._refresh_lock = threading.Lock()`.
- **Cache Hit / Refresh Decision:**
  - If `not force_refresh` and $(t_{\text{now}} - t_{\text{last}}) < 120s$, returns in-memory cached DataFrame with `meta["cache_status"] = "IN_MEMORY_CACHE_HIT"`.
  - If expired ($> 120s$), executes fresh network acquisition, validates data, atomically updates disk parquet and provenance JSON, and updates in-memory cache with `meta["cache_status"] = "FRESH_NETWORK_ACQUISITION"`.
- **Fail-Closed Upstream Protection:**
  - If upstream HTTP times out, returns HTTP 429, or network fails: the service does NOT overwrite the cache or disk snapshot; returns `(False, None, error_meta)` with `error_code="MARKET_DATA_UNAVAILABLE"`.

---

### 3. API Routes Integrity & Endpoint Analysis

- **`POST /api/tournament/analyse` (`api/routes_tournament.py`):**
  - Schema: `AnalyseRequestModel` (requires `instrument == "BTC-USD"`, `timeframe == "1h"`).
  - Concurrency Lock: `_analysis_execution_lock.acquire(timeout=10.0)` returning HTTP 503 if the analysis engine is busy processing a concurrent request.
  - Guardrail: Rejects requests with `force_fresh_tournament=True` with HTTP 400. Interactive analysis strictly consumes pre-computed/cached evidence.
  - Deduplication: `_analysis_request_cache` (size 128) maps `request_id` -> cached response; `_analysis_digest_cache` (size 64, 10s TTL) absorbs unkeyed rapid clicks.
  - Source Resolution: Calls `get_bitstamp_service().get_or_refresh_bitstamp_data()`. If successful, sets `data_source_name = "BITSTAMP"`.
  - Network Failure Handling: If Bitstamp fails, sets `bitstamp_fetch_failed = True`. Fallback candles are used only to compute baseline historical technical context, while `status`, `data_freshness_status`, and `htf_setup.setup_status` are explicitly overwritten to `BLOCKED` with reason code `BITSTAMP_RETRIEVAL_FAILED`.
  - Data Provenance Attachment: Attaches `data_provenance` containing `instrument`, `timeframe`, `source`, `analyzed_closed_candle_count`, `analyzed_window_sha256`, and `latest_closed_timestamp`.

---

### 4. Market Intelligence Calculation & Decoupled Analysis Engine (`engine/decoupled_analysis_engine.py`)

- **Output A: Market Intelligence Report:**
  - Always available on-demand, even when trading is blocked.
  - Realized Volatility Term Structure: Annualized realized volatility for 1h, 4h, 24h, 7d, 30d.
  - Volatility Regime: Wilder ADX 14, Bollinger Band Width %, ATR(14) in USD, EMAs.
  - **Source Calibration Gate:** When `source_exchange == "BITSTAMP"`, conformal envelope returns `status: "UNAVAILABLE"` and `CALIBRATION_SOURCE_MISMATCH` because HAR-RS-DOW and C2 conformal models are calibrated strictly on Coinbase historical data.
  - Excursion Estimates: 24h P10..P90 MFE/MAE price boundaries via `RangeForecastService` with Mondrian conformal scaling.
- **Output B: 5-Question Trade Authorization Gate:**
  - Evaluates Q1 (Regime), Q2 (Directional Evidence), Q3 (Entry Location), Q4 (Risk/Reward Economics), Q5 (Calibration).
  - All 5 questions must PASS for eligibility; Q1, Q3, Q4, Q5 cannot override Q2 directional insufficiency.
  - Defaults safely to ABSTAIN.
  - Strictly non-execution: `attempts_created = 0`, `is_read_only = True`.

---

### 5. Strategy Assessment & HTF Setup Detector (`engine/htf_setup_detector.py`)

- **4-Hour Bucket Aggregation:**
  - Groups 1h bars into completed 4h buckets.
  - Incomplete 4h candle rejection: If the latest bucket has $< 4$ hourly bars, it is identified as incomplete and excluded from breakout evaluation.
- **Donchian Breakout Channel:**
  - 20-bar Donchian window on completed 4h candles, shifted by 1 bar (`[t-20, t-1]`).
  - Requires at least 21 completed 4h bars (84 hourly bars) to prevent NaN channel bounds.
- **Trigger & Status States:**
  - `NO_SETUP`: Price inside Donchian channel.
  - `SETUP_FORMING`: Price within ATR-adaptive buffer (clamped between 0.5% and 1.5% of range high).
  - `SHADOW_CANDIDATE` / `TRIGGER_CONFIRMED`: Completed 4h close strictly $> 20$-bar high under compatible regime.
  - `BLOCKED`: Incompatible regime (`TRENDING_BEARISH`, `RANGE_BOUND`, `TRANSITION_UNSUPPORTED`) or stale market data.
  - `DATA_UNAVAILABLE`: Insufficient bars or NaN bounds.
- **Stale Data Blocking:**
  - If data age exceeds 2.0 hours, setup is forced to `BLOCKED` with `reason_codes: ["STALE_MARKET_DATA_BLOCKED"]`.
- **Governance Status:**
  - Setup returns `authorization_status: "OFFLINE_RESEARCH_ONLY"`, `prospective_validation_status: "FROZEN_PENDING_ACTIVATION"`, live trading `DISABLED`.

---

### 6. Data Freshness, Boundary Cutoffs, and Timestamp Semantics

- **Freshness Formula:**
  `observed_age_seconds = now_utc - latest_completed_candle_end_utc`
  where `latest_completed_candle_end_utc` is `available_time` ($t_{\text{open}} + 3600$).
- **Policy Limit:** 2.0 hours (7200 seconds). If observed age exceeds 7200s, status is `MARKET_DATA_STALE`.
- **Causal Boundary:** Point-in-time features are evaluated strictly on closed candles ($t_{\text{feature}} \le t_{\text{issue}} < t_{\text{maturity}}$).

---

### 7. End-to-End Request Trace: Button Click to DOM

1. **User Action:** User clicks `#btn-analyse-setup` in `web/app.js`.
2. **Frontend Validation:**
   - Drops duplicate clicks if `analysisInFlightRef.current == true`.
   - Checks `chartTimeframe === "1h"`, `chartCandleSnapshot.status === "ready"`, `closedCandles.length >= 168`, `curPrice > 0`.
   - Generates idempotency key `analysisRequestIdRef.current = crypto.randomUUID()`.
3. **HTTP Dispatch:** Sends `POST /api/tournament/analyse` with payload:
   `{ instrument: "BTC-USD", timeframe: "1h", data_source: "BITSTAMP", request_id: "...", live_price: ..., enforce_freshness: true, max_age_hours: 2, auto_tournament: true, candles: [...] }`.
4. **Server Execution:**
   - Acquires `_analysis_execution_lock` (10s timeout).
   - Validates payload JSON and checks idempotency caches.
   - Refreshes Bitstamp data via `BitstampMarketDataService`.
   - Executes `execute_integrated_analyse_and_tournament()`:
     - Generates `analysis_id` (e.g. `ana_a1b2c3d4e5f6`).
     - Computes closed candle window hash `analyzed_window_sha256` and watermark.
     - Runs `HTFSetupDetector.detect_setup()`.
     - Attaches unified `data_provenance`.
5. **DOM Rendering:**
   - Frontend receives response and updates `setAnalysisData(res)`.
   - Renders `#card-primary-htf-assessment`:
     - `#text-htf-analysis-id`: displays `analysisData.analysis_id`.
     - `#badge-htf-setup-status`: displays `analysisData.htf_setup.setup_status`.
     - `#badge-htf-provider`: displays `BITSTAMP (BTC/USD)`.
     - `#badge-htf-freshness`: displays `FRESH` or `MARKET_DATA_STALE`.
     - Watermark line: displays `closed through ${analysisData.data_provenance?.latest_closed_timestamp}`.
     - `#text-htf-candle-details`: displays 4h close, 20-bar Donchian range `[low - high]`, and any incomplete candle notice.
   - **Provenance Invariant:** `analysis_id`, `analyzed_window_sha256`, and candle watermark match exactly across backend response and frontend DOM.

---

### 8. Architectural Findings & Vulnerability Analysis

1. **Shadowed Route (`/api/market/candles`):**
   - Both `api/routes_market.py` and `api/market_monitor_routes.py` define `@router.get("/candles")` / `@router.get("/api/market/candles")`.
   - In `api/server.py`, `market_monitor_router` is included before `market_router`, so `market_monitor_routes.py` shadows `routes_market.py`.
   - *Recommendation:* Deprecate and remove redundant `get_candles` in `routes_market.py` to prevent route ambiguity.
2. **Candles Endpoint vs. Parquet Age Verification:**
   - `/api/market/candles` serves `BITSTAMP_PARQUET_PATH` with `"status": "LIVE"` based on file presence without evaluating its age, whereas `/api/tournament/analyse` strictly checks timestamp age against 2.0h policy limit.
   - *Recommendation:* Align `/api/market/candles` to compute and report `freshness_status` (`FRESH` vs `MARKET_DATA_STALE`) from parquet metadata before setting `"status": "LIVE"`.
3. **Startup Gate Latency:**
   - `verify_scientific_contract()` in `api/server.py` lifespan launches `verify_freeze_manifest.py` as a subprocess, which hashes multi-gigabyte historical parquets and takes ~30-40 seconds.
   - *Recommendation:* Keep this gate for production startup integrity, but allow a lightweight bypass flag for unit test environments that do not require full historical replay re-hashing.
4. **Exception Handling & Security:**
   - All uncaught exceptions are intercepted by `sanitized_exception_handler` in `api/security_middleware.py`, logging the internal error to `security_audit` while returning an uninformative sanitized JSON error with a unique `request_id`, fully complying with OWASP ASVS 5.0.

---

### 9. Failure-Injection Test Suite Results (`tests/test_v33_8_failure_injection.py`)

| Test Mode | Injected Fault | Expected Behavior | Observed Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Mode 1** | HTTP Timeout ($> 15s$) | Fail-closed, `MARKET_DATA_UNAVAILABLE`, `UPSTREAM_TIMEOUT` | Handled cleanly, no crash | **PASS** |
| **Mode 2** | HTTP 429 Rate Limit | Fail-closed, `MARKET_DATA_UNAVAILABLE`, `RATE_LIMIT_EXCEEDED` | Handled cleanly, no retry loop | **PASS** |
| **Mode 3** | Malformed JSON Structure | Missing `ohlc` list rejected with `EMPTY_OR_MISSING_OHLC` | Validation rejected immediately | **PASS** |
| **Mode 4** | Empty Response (`ohlc: []`) | Zero candles rejected with `EMPTY_OR_MISSING_OHLC` | Validation rejected immediately | **PASS** |
| **Mode 5** | Duplicate Candle Timestamps | Identical consecutive timestamps rejected | `DUPLICATE_TIMESTAMP` detected | **PASS** |
| **Mode 6** | Hourly Interval Gap | 2-hour gap injected between candles 4 and 5 | `INTERVAL_GAP_DETECTED` | **PASS** |
| **Mode 7** | Invalid Extrema ($H < L$ / $H < O$) | Geometric invalidity rejected | `HIGH_BELOW_OPEN_CLOSE` caught | **PASS** |
| **Mode 8** | Stale Response ($> 2.0h$) | `MARKET_DATA_STALE`, setup forced to `BLOCKED` | `STALE_MARKET_DATA_BLOCKED` | **PASS** |
| **Mode 9** | Provider Outage / Unreachable | Host unreachable returns `MARKET_DATA_UNAVAILABLE` | Handled cleanly, disk preserved | **PASS** |
| **Mode 10** | Rapid Repeated Clicks | Subsequent request within 120s TTL hits in-memory cache | `IN_MEMORY_CACHE_HIT` | **PASS** |
| **Mode 11** | File Preservation | `data/raw/ohlcv.parquet` SHA-256 remains bit-identical | Hash verified `ba06fb5...` | **PASS** |

**Total Failure Injection Tests:** 11 passed, 0 failed in 0.74s.

---

### Conclusion & Verification Verdict

The runtime and API integrity of BTCognitive for Milestone V35.2 is **VERIFIED AND INTACT**.
- Market data acquisition, validation, and caching satisfy all fail-closed criteria.
- Decoupled intelligence and strategy assessment maintain strict non-execution boundaries.
- Provenance watermarks and analysis IDs are fully consistent from button click to DOM.
- No live trading is authorized (`OFFLINE_RESEARCH_ONLY`).

