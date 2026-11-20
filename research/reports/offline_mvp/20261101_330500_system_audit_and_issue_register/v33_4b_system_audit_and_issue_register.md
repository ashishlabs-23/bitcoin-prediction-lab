# BTCognitive — Initial System Audit & Permanent Issue Register (V33.4B)

**Audit Date:** November 1, 2026  
**Auditor:** BTCognitive Lead Research Orchestrator & Multi-Agent Verification Stream  
**Scope:** Initial System Audit, Deep-Dive Investigation of Findings F01–F08, and Establishment of the Permanent Issue Register  
**Operational Mode:** `READ-ONLY AUDIT & VERIFICATION` (Zero Code Modifications Applied)  
**Governing Standard:** BTCognitive Operating Contract V1.0.0 & `.agents/skills/btcognitive-research-orchestrator/SKILL.md`  

---

## 1. Executive Summary

In response to executive instructions (*"BTCognitive — Initial system audit"*), this report accomplishes three essential objectives:
1. **Reconciliation of Audit Inconsistencies:** Formally reconciles and corrects the three questions raised by management regarding prospective evidence status, server restart health, and test coverage.
2. **Deep-Dive Investigation of Area 1 (F01 — Repeated Candle Snapshot Hashing):** Exhaustively traces the call graph, identifies the algorithmic bottleneck, and empirically demonstrates a **100% byte-for-byte exact hash match** operating in **0.62 seconds** (a ~20x speedup) compared to the current 12.23-second un-vectorized iteration.
3. **Establishment of the Permanent Issue Register:** Catalogs findings F01 through F08 with verified empirical evidence, impact assessments, root causes, surgical non-breaking proposed solutions, and independent test plans.

All investigations adhere strictly to the **zero-code-modification mandate**: no implementation files have been altered during this audit phase.

---

## 2. Manager Audit Reconciliation

### A. Prospective Evidence Status Reconciliation
Management correctly identified an inconsistency: the previous summary labeled prospective evidence as `COLLECTING`, while the conformal ledger was described as frozen at 7/100 and the HTF shadow ledger as inactive at 0/100.

**Empirical Ground Truth on Disk:**
1. **Conformal Volatility Forecast Ledger (`data/prospective_forecast_ledger.jsonl`):**
   - **Status:** `FROZEN_AT_7_BLOCKS`.
   - **Content:** Exactly 21 lines representing 7 resolved non-overlapping 24h evaluation blocks.
   - **Cryptographic Hash:** SHA-256 `ee58b37c71c5c3ff322af3084d27b306eb0a445a8bd6e01a74b76d8168ccd491`.
   - **Ingestion State:** Frozen by governance. No active collection is executing.
2. **HTF Breakout Strategy Shadow Ledger (`data/prospective_entry_ledger_v2.jsonl` / `data/prospective_shadow_v1.jsonl`):**
   - **Status:** `INACTIVE_0_BLOCKS`.
   - **Content:** The shadow runner status file (`data/prospective_shadow_status.json`) confirms `total_candidates: 0`, `pending_resolution: 0`, and the background collector process is stopped.
   - **Ingestion State:** Inactive. Zero prospective entries have been recorded post-freeze.

**Governed Correction:** Neither ledger is currently `COLLECTING`. Labeling prospective evidence as `COLLECTING` was an epistemic conflation. The formal prospective status is **`FROZEN_PENDING_ACTIVATION`** (or `FROZEN_AT_7_BLOCKS` for conformal volatility, and `INACTIVE_0_BLOCKS` for HTF shadow strategy).

---

### B. Server Process & Port Ownership Reconciliation
Management noted that the execution log showed failed connection checks during server restart before a successful HTTP 200 response was reported.

**Forensic Explanation of Startup Checks:**
1. **Startup Latency Window (~3.5 seconds):**
   - When Uvicorn is spawned, the application executes extensive scientific contract verification before binding the HTTP socket:
     - Scans and loads 6,945 persistent forecast records from SQLite (`observatory.db`).
     - Reconstructs user positions from disk logs.
     - Verifies the scientific freeze contract manifest (`repaired_scientific_contract_manifest.json`) and joblib artifact hash (`har_rs_dow_v1.joblib`).
     - Initializes the feature cache with 500 candles from raw OHLCV parquet.
   - Polling within the first 3.5 seconds resulted in `ConnectionRefusedError: [WinError 10061]` because the socket had not yet opened.
2. **Network Interface Transition:**
   - The host machine's Wi-Fi interface transitioned from `192.168.0.3` to `192.168.0.4`. An earlier daemon bound specifically to `192.168.0.3` suffered an asynchronous proactor error (`WinError 64: The specified network name is no longer available`).
   - The process was killed, and the current instance was bound to `0.0.0.0:8000`.

**Verified Active Process State:**
- **Process ID (PID):** `23720`
- **Port Owner:** TCP `0.0.0.0:8000` owned exclusively by PID `23720`.
- **Command Line:** `"C:\Projects\BTCognitive\BTCognitive\.venv_win\Scripts\python.exe" -m uvicorn api.server:app --host 0.0.0.0 --port 8000`
- **Working Directory:** `C:\Projects\BTCognitive\BTCognitive`
- **Health Response:** Verified HTTP 200 via `http://127.0.0.1:8000/api/health` and `http://192.168.0.4:8000/api/health` (`product_mode: ANALYSIS_ONLY`).

---

### C. Test Coverage Scope Reconciliation
Management noted that the seven passing tests in `tests/test_v33_4_htf_prospective_protocol.py` only demonstrate that the protocol schema and manifest invariants pass, not that the Analysis endpoint, dashboard, polling, or frontend/backend integration work correctly.

**Reconciliation & Acknowledgment:**
- This distinction is entirely accurate and valid.
- `test_v33_4_htf_prospective_protocol.py` validates:
  1. Protocol constants and invariants.
  2. Ledger path separation (`prospective_forecast_ledger.jsonl` vs `prospective_entry_ledger_v2.jsonl`).
  3. JSON schema validation for shadow ledger records.
  4. Inactive collector assertion (`lock_file.exists() == False`).
  5. Frozen conformal ledger line count (21) and SHA-256 hash.
  6. Manifest version 1.7.0 dataset hashes.
  7. Governance invariants (`OFFLINE_RESEARCH_ONLY`, `DISABLED`).
- **Missing Coverage:** The test suite does **not** exercise `_post_analyse_market()` under load, does not benchmark execution latency against the 45-second client timeout, does not test the frontend polling debouncing, and does not assert that UI badges match API payloads.
- An end-to-end integration test (`tests/test_v33_4b_analysis_integration.py`) must be pre-registered to verify these components once repair authorization is granted.

---

## 3. Deep-Dive Investigation: Finding F01 (Candle Window Hashing)

### 3.1 Trace of the Call Graph
`_closed_candle_window_hash(df_1h)` is invoked at three distinct points in a single `POST /api/tournament/analyse` request:
1. **Invocation 1 (`engine/regime_strategy_tournament.py`, line 763):**
   ```python
   watermark_data = {
       ...
       "candle_window_sha256": _closed_candle_window_hash(df_closed),
       "total_closed_candles": len(df_closed)
   }
   ```
2. **Invocation 2 (`engine/regime_strategy_tournament.py`, line 595, inside `check_data_freshness_and_gaps`):**
   ```python
   dataset_fingerprint = _closed_candle_window_hash(df_1h)
   ```
   Invoked immediately at line 767 of `analyse_current_market()`.
3. **Invocation 3 (`engine/decoupled_analysis_engine.py`, line 102, inside `compute_market_intelligence_report`):**
   ```python
   freshness_res = check_data_freshness_and_gaps(df_closed, max_age_hours=max_age_hours)
   ```
   Invoked at line 777 of `analyse_current_market()` via `decoupled_analysis_engine.execute_decoupled_analysis()`.

### 3.2 Exact Code Implementation & Complexity Analysis
In `engine/regime_strategy_tournament.py` (lines 633–648):
```python
def _closed_candle_window_hash(df_1h: pd.DataFrame) -> str:
    """Fingerprint the complete normalized candle window, not just its endpoints."""
    ts_col = "timestamp" if "timestamp" in df_1h.columns else "timestamp_utc"
    timestamps = pd.to_datetime(df_1h[ts_col], utc=True, errors="raise")
    records = []
    for index, row in df_1h.reset_index(drop=True).iterrows():
        records.append({
            "timestamp_utc": timestamps.iloc[index].isoformat(),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        })
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

**Why it consumes 12.23 seconds:**
- `df_1h.reset_index(drop=True).iterrows()` instantiates 42,326 individual `pd.Series` objects.
- `timestamps.iloc[index].isoformat()` calls Python's ISO formatting 42,326 times.
- 42,326 separate Python dictionary objects are allocated in memory.
- `json.dumps()` serializes the entire 42,326-element dictionary array into a ~5.8 MB JSON string.
- When repeated three times sequentially: $12.23 \times 3 = \mathbf{36.69\text{ seconds}}$ of pure CPU blocking time!

### 3.3 Verification of Identity Preservation (Exact-Match Benchmark)
To address management's requirement:
> *"We must verify that a faster hash preserves the original snapshot identity, including timestamps and all required fields, before changing it."*

We constructed a benchmark testing whether the identical canonical JSON string and SHA-256 hash can be produced in a vectorized manner without altering a single field or character.

**Benchmark Implementation Tested:**
```python
# Vectorized timestamp ISO formatting with timezone preserved:
iso_ts = pd.to_datetime(df[ts_col], utc=True).dt.strftime('%Y-%m-%dT%H:%M:%S%z').values
iso_ts = [ts[:-2] + ':' + ts[-2:] if ts.endswith('+0000') else ts for ts in iso_ts]

# Columnar extraction avoiding iterrows:
c_list = df['close'].astype(float).tolist()
h_list = df['high'].astype(float).tolist()
l_list = df['low'].astype(float).tolist()
o_list = df['open'].astype(float).tolist()
v_list = df['volume'].astype(float).tolist()

records = [
    {'close': c, 'high': h, 'low': l, 'open': o, 'timestamp_utc': ts, 'volume': v}
    for c, h, l, o, ts, v in zip(c_list, h_list, l_list, o_list, iso_ts, v_list)
]
canonical = json.dumps(records, sort_keys=True, separators=(',', ':'), allow_nan=False)
fast_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

**Empirical Verification Results (42,326 closed hourly rows):**
- **Existing Implementation Hash:** `142f759ff02d50f7156c2f9d1d9b2d4bab7388c250c81ac9a9db458e43cf9248`
- **Vectorized Implementation Hash:** `142f759ff02d50f7156c2f9d1d9b2d4bab7388c250c81ac9a9db458e43cf9248`
- **Hash Match:** **`EXACT MATCH (100% IDENTICAL)`**
- **Existing Runtime:** **12.2334 seconds**
- **Vectorized Runtime:** **0.6256 seconds**
- **Speedup Factor:** **19.55x faster**

**Conclusion:** Vectorized columnar generation preserves 100% byte-for-byte fidelity with the canonical schema, includes all 6 required fields (`timestamp_utc`, `open`, `high`, `low`, `close`, `volume`), and drops execution time to ~0.62s. Combined with caching or parameter passing across Invocations 2 and 3, total hashing time drops from **36.7s to 0.62s** (a 98.3% latency reduction).

---

## 4. The Permanent Issue Register

The following register contains confirmed system defects and design weaknesses identified during V33.4A and V33.4B audits. All items are maintained in `CONFIRMED_AUDIT_ONLY` status pending governed implementation authorization.

| ID | Component | Summary | Evidence & Code Location | Impact | Root Cause | Proposed Non-Breaking Solution | Pre-Conditions & Test Plan | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **F01** | Analysis Engine | 42,326-row candle snapshot is hashed 3 times in series using un-vectorized `iterrows()` | `engine/regime_strategy_tournament.py` (L633–648, L595, L763); `engine/decoupled_analysis_engine.py` (L102). 36.7s out of 38.1s total isolated runtime. | **Critical** | Un-vectorized `df.iterrows()` and repeated invocation across sub-engines without parameter passing or caching. | 1. Replace `iterrows()` with columnar zip generation (0.62s, 100% identical SHA-256).<br>2. Add optional `dataset_fingerprint` argument to `check_data_freshness_and_gaps()` to reuse precomputed hash. | Assert exact SHA-256 match on `ohlcv.parquet`; assert runtime $< 1.0\text{s}$; verify `test_v32_49_scenario_qa.py` passes unchanged. | `CONFIRMED_AUDIT_ONLY` |
| **F02** | Request Handling | Global mutex `_analysis_execution_lock` serializes all Analysis requests | `api/routes_tournament.py` (L512): `with _analysis_execution_lock: return _post_analyse_market(req)`. | **Critical** | Threading lock blocks concurrent requests; 38s baseline causes second request to wait 76s, exceeding 45s client timeout. | 1. Once F01 reduces runtime to $<1.5\text{s}$, lock contention drops to $<1.5\text{s}$.<br>2. Cache recent analysis results by `request_digest` to return identical repeated requests in $<5\text{ms}$. | Simulate 2 concurrent requests via `asyncio.gather()`; assert both complete successfully within 5.0 seconds without 45s timeout. | `CONFIRMED_AUDIT_ONLY` |
| **F03** | Frontend Polling | Smart-entry monitor polling loop triggers HTTP 429 Rate Limit | `web/app.js` (L17400–17420): `loadState` in `useEffect` has `[loadState]` dependency where `loadState` depends on volatile state `[smartEntryDecision, curPrice, predictionData]`. | **High** | Rapid re-creation of `loadState` on every price tick/render re-fires `useEffect`, cancelling timer and hammering endpoint every few milliseconds. | 1. Refactor `useEffect` to use a stable interval reference independent of volatile props.<br>2. Enforce minimum 8-second debounce and exponential backoff on HTTP 429. | Monitor access log during 60s active browser run; assert total calls to `/api/tournament/smart-entry/monitor` $\le 10$ per minute. | `CONFIRMED_AUDIT_ONLY` |
| **F04** | Forecast Presentation | Green `FORECAST RECEIVED` badge renders when directional forecast is unavailable | `web/app.js` (L17878–17891): `predictionData ? "FORECAST RECEIVED" : "FORECAST UNAVAILABLE"`. | **High** | Truthiness check on telemetry polling object rather than validated directional forecast fields (`model_id`, `direction`, `timestamp_utc`). | Update condition to `Boolean(predictionData?.model_id && predictionData?.timestamp_utc && predictionData?.direction !== "NOT_ESTIMATED")`. | Render dashboard with empty/telemetry-only forecast; assert badge renders neutral/warn `FORECAST UNAVAILABLE`. | `CONFIRMED_AUDIT_ONLY` |
| **F05** | Price Presentation | Historical candle snapshot price is unconditionally labelled `Live price` | `web/app.js` (L17817): hardcoded string `· Live price: $${fmt(data.live_price)}`. | **High** | String literal ignores `data_source === "LOCAL_HISTORICAL_SNAPSHOT"`. | Dynamically label price based on source: `Live price` for live feeds; `Snapshot close` for local historical files. | Assert UI displays `Snapshot close: $76,985.40` when using local parquet, eliminating false real-time impressions. | `CONFIRMED_AUDIT_ONLY` |
| **F06** | Strategy Registry | Primary candidate `HTF_RANGE_EXPANSION_BREAKOUT` has only 4 mock attempts in registry | `engine/regime_strategy_tournament.py` (L324–329, L385): hardcoded `recent_htf` array with 4 mock trials. | **High** | Hardcoded demonstration mock array in `VersionedStrategyRegistry` conflated with real empirical evidence (194 trades) and prospective ledger (0 trades). | Formally separate: 1. Authoritative model registry (`models/authoritative_model_registry.py`). 2. Historical research backtest ledger. 3. Prospective shadow ledger. Document in registry metadata. | Assert registry metadata explicitly cites evidence provenance without confusing mock sample with empirical backtest. | `CONFIRMED_AUDIT_ONLY` |
| **F07** | Regime Classifier & Hysteresis | Terminology mismatch (`RANGE_BOUND` vs `CONSOLIDATION_RANGE`) and 0-candidate tournament result | `engine/regime_strategy_tournament.py` (L690–710) emits `RANGE_BOUND`; `web/app.js` and PRD V12 refer to `CONSOLIDATION_RANGE`. All 6 strategies disqualified under current regime. | **Medium** | Historical naming divergence between V12 and V32 engines; strict regime filtering blocks breakouts during low-volatility compression. | 1. Harmonize regime alias map (`RANGE_BOUND` $\leftrightarrow$ `CONSOLIDATION_RANGE`).<br>2. Clarify in UI that 0 candidates under consolidation is a legitimate risk control, not a system failure. | Verify regime mapping passes across tournament engine and frontend views; assert clear explanatory rejection reasons are displayed. | `CONFIRMED_AUDIT_ONLY` |
| **F08** | Server Lifecycle | Server startup latency (~3.5s) causes transient connection refused errors; network adapter change causes socket hang | `api/server.py` lifespan and Uvicorn socket handling. Windows proactor `WinError 64` when IP lease changes. | **Medium** | Synchronous heavy initialization during lifespan startup; socket binding to specific IP rather than wildcard `0.0.0.0`. | 1. Ensure production/daemon runner binds to `0.0.0.0` with proper allowed hosts.<br>2. Add health retry loop with 5s timeout in test runners and management scripts. | Run automated startup test verifying clean shutdown, port release, and successful startup within 5 seconds. | `CONFIRMED_AUDIT_ONLY` |

---

## 5. Candidate Components for Simplification or Redesign

In accordance with management guidance, we distinguish components that provide genuine risk protection from those that are redundant, unverified, or misleading:

| Component | Current Concern | Value Assessment | Recommended Next Action |
| :--- | :--- | :--- | :--- |
| **Repeated Snapshot Hashing** | Invoked 3 times sequentially on identical data. | **Zero Added Value (Pure Waste)** | Optimize to columnar zip and cache across sub-calls once authorized. |
| **Mock Historical Strategy Attempts** | 4 to 10 hardcoded mock trials in `VersionedStrategyRegistry`. | **Misleading Demonstration Code** | Replace with references to versioned research manifests or mark explicitly as `UI_DEMONSTRATION_FIXTURE_ONLY`. |
| **Ordinary Analysis vs Tournament Coupling** | Running full tournament backtest during routine market intelligence checks. | **High Computational Cost** | Decouple: allow lightweight Market Intelligence reports without triggering full strategy tournament backtest unless requested. |
| **Smart-Entry Monitor Polling** | Unthrottled polling loop re-executing on every state change. | **Self-Inflicted Instability** | Debounce to stable 8s interval with exponential backoff on HTTP 429. |
| **Duplicate Strategy Names** | `CONSOLIDATION_RANGE` vs `RANGE_BOUND`. | **Confusion / Friction** | Introduce canonical regime enumeration with backward-compatible aliases. |
| **Safety Guardrails (Regime Gate, Cost Model, Abstention)** | Inhibits breakout entries during consolidation; enforces 26 bps costs. | **Critical Risk Value** | **DO NOT REMOVE.** Retain all evidence, cost, and regime gates. |

---

## 6. Governed Four-Point Decisions

In compliance with the BTCognitive Operating Contract V1.0.0:

| Dimension | Governed Determination | Rationale |
| :--- | :--- | :--- |
| **1. Research Experiment** | **`RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`** | `HTF_RANGE_EXPANSION_BREAKOUT` with `MarketRegimeClassifier` is retained as the priority research candidate. No unverified strategies or synthetic indicators added. |
| **2. Prospective Evidence** | **`FROZEN_PENDING_ACTIVATION`** | Reconciled: Conformal volatility ledger is `FROZEN_AT_7_BLOCKS` (SHA-256 `ee58b37c...`). HTF shadow strategy ledger is `INACTIVE_0_BLOCKS`. Neither is currently collecting. |
| **3. Model Authorization** | **`OFFLINE_RESEARCH_ONLY`** | Production promotion prohibited pending full prospective evidence accumulation (100 clean non-overlapping blocks). |
| **4. Live Trading** | **`DISABLED`** | Strict non-execution boundary preserved across all endpoints, configuration layers, and runners. |

