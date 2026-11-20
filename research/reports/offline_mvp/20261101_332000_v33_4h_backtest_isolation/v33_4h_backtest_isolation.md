# BTCognitive V33.4H — F02 Backtest Isolation and Analysis Reliability Report

**Execution Timestamp:** 2026-11-01T23:22:00+05:30  
**Commit SHA Baseline:** `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Milestone:** V33.4H (Issue F02 Resolution)  
**Governance Scope:** Offline Research & Operational Reliability Only  
**Live Trading Execution Status:** `DISABLED` (Zero capital deployment)  

---

## 1. Executive Summary & Problem Resolution

### Finding F02 Root Cause
Prior to V33.4H, the interactive analysis route `POST /api/tournament/analyse` acquired a global lock `_analysis_execution_lock` and could invoke `run_strategy_tournament_backtest(force_fresh=True)`. Multi-year walk-forward backtests evaluate three arms across thousands of hourly bars, requiring ~120 seconds of CPU-intensive computation. While holding `_analysis_execution_lock`, all subsequent interactive user requests were queued until they exceeded the frontend's 45-second timeout window, failing with unhandled client errors.

### V33.4H Remediation Architecture
1. **Strict Decoupling of Analysis from Backtests:**
   - Ordinary interactive Analysis (`POST /api/tournament/analyse`) never launches or invokes fresh historical multi-year backtests (Invariant: 0 historical backtest invocations initiated by `/analyse`).
   - Ordinary Analysis consumes only pre-existing, validated research evidence manifests.
   - Any attempt to pass `force_fresh_tournament=True` via `/api/tournament/analyse` is rejected with `HTTP 400 Bad Request` (`"Fresh multi-year tournament backtest cannot be executed through the interactive Analysis endpoint"`).
2. **Independent Dual Output Pipelines:**
   - **Output A (Market Intelligence):** Decoupled volatility term structure, conformal risk envelopes, and regime classifications return successfully independent of strategy assessment or evidence availability.
   - **Output B (Strategy Assessment):** Six explicit taxonomies are strictly maintained:
     - `NOT_EVALUATED`: Market data failed continuity/quality gates.
     - `EVIDENCE_UNAVAILABLE`: Strategy candidates shortlisted, but no matching validated walk-forward backtest manifest exists.
     - `NOT_VALIDATED`: Manifest found, but candidate failed predefined performance gates.
     - `NO_SETUP`: Market regime detected, but no candidate met setup conditions.
     - `SHADOW_ELIGIBLE`: Candidate passed all screening and backtest gates.
     - `BLOCKED`: Quarantined strategy.
3. **Out-of-Process Research Execution:**
   - Historical backtesting has been moved strictly out-of-process via CLI (`scripts/run_offline_strategy_research.py`).
   - Offline research operates without acquiring `_analysis_execution_lock` and writes versioned manifests to `engine/manifests/`.
4. **Lock Bounding & Idempotency Safeguards:**
   - `_analysis_execution_lock.acquire(timeout=10.0)` prevents indefinite thread blocking; if saturated, returns `HTTP 503 Service Unavailable`.
   - Request-ID idempotency returns identical cached results for matching payloads and `HTTP 409 Conflict` for modified payloads with reused IDs.

---

## 2. Verification Evidence & Metrics

### A. Headless Chrome CDP Browser Verification
Executed via `scripts/qa/v33_4h_browser_verification.py`:
- **Target Page:** `http://127.0.0.1:8000/` -> `#tab-btn-smart-entry`
- **User Action:** Single click on `#btn-analyse-setup`
- **Network Metrics:**
  - HTTP Request: `POST /api/tournament/analyse`
  - HTTP Status: `200 OK`
  - Roundtrip Latency: **393.31 ms** (vs. 45,000 ms timeout)
- **Payload Invariants:**
  - `is_read_only`: `True`
  - `attempts_created`: `0`
  - `market_intelligence.status`: `SUCCESS`
  - `strategy_assessment.status`: `EVIDENCE_UNAVAILABLE`
  - `decision.action`: `ABSTAIN`
  - `decision.strategy_assessment_status`: `EVIDENCE_UNAVAILABLE`
- **DOM Rendering Inspection:**
  - `#analysis-market-intelligence-bar`: Present, displaying *"Operational (Independent from Strategy Assessment)"*
  - `#badge-strategy-assessment`: Present, displaying *"STRATEGY ASSESSMENT: EVIDENCE_UNAVAILABLE"*
  - `#badge-smart-entry-status`: Present, displaying *"NO_SMART_ENTRY"*
  - `#analysis-progress`: Present, clean explanation without alert dialogs.
  - Console Errors / Uncaught Exceptions: **0**

### B. Python Regression Test Suite
Executed via `.venv_win\Scripts\pytest.exe`:
- **Total Test Cases Executed:** 67
- **Passed:** 67 / 67 (100%)
- **Failed:** 0
- **Suites Verified:**
  - `tests/test_v33_4h_backtest_isolation.py` (6/6 passed)
  - `tests/test_v33_4g_presentation_integrity.py` (6/6 passed)
  - `tests/test_v33_4f_decision_stability.py` (4/4 passed)
  - `tests/test_v33_4_htf_prospective_protocol.py` (7/7 passed)
  - `tests/test_v32_49_scenario_qa.py` (44/44 passed)

### C. Concurrency & Idempotency Testing
- 5 concurrent `/api/tournament/analyse` requests completed in aggregate **< 1.5 seconds**.
- Duplicate retry with identical `request_id` returned identical `decision_id` in **< 10 ms**.
- Modified payload with reused `request_id` triggered `HTTP 409 Conflict`.

---

## 3. Four-Point Handover Decision

1. **Research Experiment:** `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`  
   - HTF range expansion breakout remains the primary research candidate.
   - Historical backtest evidence is isolated from runtime interactive analysis.
2. **Prospective Evidence:** `FROZEN_PENDING_ACTIVATION`  
   - Conformal forecast ledger remains frozen at 7 clean blocks (`ee58b37c...`).
   - HTF shadow ledger remains inactive at 0 blocks pending prospective activation.
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`  
   - All models strictly restricted to offline research.
4. **Live Trading:** `DISABLED`  
   - Zero capital risk, zero order placement.

