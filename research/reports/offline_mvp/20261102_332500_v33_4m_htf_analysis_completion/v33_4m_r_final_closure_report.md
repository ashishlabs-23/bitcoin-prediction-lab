# BTCognitive — Milestone V33.4M-R Final Closure Report
## Multi-Agent Verification, Evidence Reconciliation, Targeted Repair and Final Sign-Off

**Mission ID:** V33.4M-R-FINAL  
**Date:** 2 November 2026  
**Project:** BTCognitive BTC/USD Market Monitor & Research Terminal  
**Service URL:** `http://127.0.0.1:8000`  
**Git Branch:** `main`  
**Git Commit SHA:** `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Execution Strategy:** Parallel multi-agent investigation with one coordinating lead  

---

## A. Executive Decision

### **FINAL SIGN-OFF APPROVED**

Milestone **V33.4M-R (Analysis Consistency and Freshness Closure)** has completely and verifiably closed every remaining Analysis requirement. 
- The root cause of the regime classification discrepancy between 168-bar API windows and 42,177-bar historical windows was isolated to an artificial short-circuit in `compute_ema(series, period)` in `engine/regime_strategy_tournament.py` and resolved. Both evaluate identically to `TRENDING_BEARISH`.
- The data freshness calculation was verified to be strictly dynamic (`now_utc - last_closed_candle_utc = 265,075.8s = 73.63h > 2.0h operational threshold`), correctly marking the data `MARKET_DATA_STALE`.
- The three-way status contract is decoupled and fully operational: Market Intelligence calculations succeed (`calculation_status: SUCCESS`), source data freshness is explicitly flagged (`data_freshness_status: MARKET_DATA_STALE`), and live setup evaluation is strictly blocked (`setup_evaluation_eligibility: INELIGIBLE_DATA_STALE`).
- Stale market data and incompatible regimes strictly gate live trade proposals (`setup_status: BLOCKED`, `trigger_status: STALE_DATA_BLOCKED`, `entry_reference: null`, `stop_reference: null`, `target_reference: null`). The 20-bar Donchian channel bounds are segregated under `completed_4h_bar` and never presented as an active stop loss.
- 100% field parity was proven between the backend HTTP response and the browser DOM using Chrome DevTools Protocol for canonical analysis request `ana_ee29321e5f42`.
- All 83 automated unit, contract, and regression tests passed (13 dedicated V33.4M-R + 70 regression tests).
- All 14 protected historical datasets, manifests, and prospective ledgers match their cryptographic SHA-256 baseline hashes bit-for-bit with zero file mutations or hash drift.
- Research governance remains strictly enforced: `OFFLINE_RESEARCH_ONLY`, `live_trading_enabled: false`, zero broker connectivity, and zero simulated trade attempts created (`attempts_created: 0`).

---

## B. Multi-Agent Execution Record

Six specialized subagents were deployed concurrently under the coordinator to investigate independent workstreams:

| Agent | Investigation Stream | Findings & Verification Result | Evidence & Deliverable |
| :--- | :--- | :--- | :--- |
| **Agent 1** | Backend Freshness & Data Lineage | **VERIFIED (PASS)**. Dynamic timestamp arithmetic confirmed (`datetime.now(timezone.utc) - last_dt`). Decoupled 3-status taxonomy operational. Operational threshold 2.0h enforced. | Source line audit in `engine/regime_strategy_tournament.py` (L560–632) & `engine/decoupled_analysis_engine.py` (L57–306); live API verification. |
| **Agent 2** | API Contract & Strategy Logic | **VERIFIED (PASS)**. All 16 contract fields present and typed. 5 canonical regimes mapped. Bearish, range-bound, and unsupported transition strictly BLOCKED. Reference fields strictly null on blocked/inactive setups. Read-only invariant confirmed (`attempts_created: 0`). | Source line audit in `api/routes_tournament.py` (L524–661) & `engine/htf_setup_detector.py` (L41–354); 13/13 acceptance gates passed. |
| **Agent 3** | Frontend & Browser Parity | **VERIFIED (PASS)**. Proved browser dashboard strictly renders backend JSON payload with zero client-side regime classification or freshness arithmetic. Null references safely mapped to "Unavailable". | DOM element mapping in `web/app.js` (L18190–18280); CDP test script validation. |
| **Agent 4** | Test & Execution Evidence | **VERIFIED (PASS)**. Preflight safety confirmed: zero socket leaks outside loopback, zero parquet writes to protected paths, zero mutating SQL queries against persistent DB. All 83 tests passing. | Pytest execution logs; fixture audit in `tests/conftest.py`; test mapping matrix for all 10 acceptance gates. |
| **Agent 5** | Governance, Data Integrity & Git | **VERIFIED (PASS)**. 14 protected research files, ledgers, and manifests match SHA-256 baselines bit-for-bit. Git branch `main`, SHA `25d483f4...`, zero unapproved mutations. Live trading strictly `DISABLED`. | Cryptographic SHA-256 audit across `data/`, `engine/manifests/`, and `research/`; Git status audit. |
| **Agent 6** | Independent Adversarial Review | **CONDITIONAL PASS (PASS AFTER TARGETED REPAIR)**. Verified fail-closed tri-layer safety, zero-mock integrated tests, strict nullity of stop reference. Identified minor JS falsy coercion (`0 \|\| "72.3"`) and explanation timestamp label ambiguity; both cleanly repaired and re-verified. | Adversarial review matrix; source inspections; 13/13 pytest re-run in 99.46s. |

---

## C. Exact Freshness Calculation

The following calculation details were captured during the canonical Analysis execution (`analysis_id: ana_ee29321e5f42`):

- **Analysis Request ID:** `ana_ee29321e5f42`
- **Analysis Request Timestamp (UTC):** `2026-11-02T14:37:55.663979+00:00`
- **Last Observed Hourly Timestamp (UTC):** `2026-10-30T13:00:00+00:00`
- **Last Completed Hourly Timestamp (UTC):** `2026-10-30T13:00:00+00:00`
- **Latest Completed 4-Hour Bar Timestamp (UTC):** `2026-10-30T08:00:00+00:00` (covering closed 4h bucket `08:00–12:00 UTC`; bucket `12:00–16:00 UTC` has only 2/4 closed 1h bars and is causally excluded)
- **Actual Watermark Used by Implementation:** `2026-10-30T13:00:00+00:00` (stored in `candle_watermark["last_closed_timestamp"]`, hash `0caf188f890c45e8`)
- **Formula Source Location:** `engine/regime_strategy_tournament.py` lines 608–609:
  ```python
  now_utc = datetime.now(timezone.utc)
  observed_age_seconds = max(0.0, (now_utc - last_dt).total_seconds())
  ```
- **Exact Age in Elapsed Seconds:** `265,075.8 seconds`
- **Exact Age in Elapsed Hours:** `73.63 hours`
- **Operational Freshness Threshold:** `7,200.0 seconds` (`2.0 hours`)
- **Computed Freshness Status:** `MARKET_DATA_STALE` (`265,075.8s > 7,200.0s`)
- **Setup Evaluation Eligibility:** `INELIGIBLE_DATA_STALE`
- **Live Strategy Action:** `BLOCKED` with reason code `STALE_MARKET_DATA_BLOCKED`

---

## D. API and Browser Parity

Comparison between the live HTTP network response from `POST /api/tournament/analyse` and the real Chrome DevTools Protocol DOM extraction from `#card-primary-htf-assessment` on the identical request `ana_ee29321e5f42`:

| Parameter | Backend API Response (`POST /api/tournament/analyse`) | Browser DOM Extraction (`#card-primary-htf-assessment`) | Parity Status |
| :--- | :--- | :--- | :---: |
| **Analysis Request ID** | `ana_ee29321e5f42` | `#text-htf-analysis-id`: `ana_ee29321e5f42` | **MATCH (100%)** |
| **Outcome Heading** | N/A (Derived in UI) | `#analysis-outcome-heading`: `HTF SETUP BLOCKED` | **MATCH (100%)** |
| **Outcome Subtitle** | `smart_entry_decision.reason` | `#analysis-outcome-sub`: `Market data is stale (73.6h old > 2.0h operational limit; latest completed 4h bar 2026-10-30T08:00:00+00:00)...` | **MATCH (100%)** |
| **Observed Regime** | `TRENDING_BEARISH` | `#text-htf-regime`: `TRENDING_BEARISH` | **MATCH (100%)** |
| **Setup Status** | `BLOCKED` | `#badge-htf-setup-status`: `SETUP STATUS: BLOCKED` | **MATCH (100%)** |
| **Trigger Status** | `STALE_DATA_BLOCKED` | `#text-htf-trigger`: `STALE_DATA_BLOCKED` | **MATCH (100%)** |
| **Data Freshness** | `MARKET_DATA_STALE` (73.6h old) | `#badge-htf-freshness`: `Data Freshness: MARKET_DATA_STALE (73.6h old)` | **MATCH (100%)** |
| **Entry Reference** | `null` | `#text-htf-entry`: `Unavailable` | **MATCH (100%)** |
| **Stop Reference** | `null` | `#text-htf-stop`: `Unavailable` | **MATCH (100%)** |
| **Target Reference** | `null` | `#text-htf-target`: `Unavailable` | **MATCH (100%)** |
| **20-Bar Donchian Range** | `[$76,301.02 – $81,890.00]` | `#text-htf-candle-details`: `20-bar Donchian Range: [$76,301.02 – $81,890]` | **MATCH (100%)** |
| **Historical Trades** | 194 trades | `#metric-historical-trades`: `194 Historical Trades` | **MATCH (100%)** |
| **Historical Win Rate** | 43.81% | `#metric-historical-winrate`: `43.81% Overall Win Rate` | **MATCH (100%)** |
| **All-Trade Net EV** | +9.57 bps | `#metric-historical-expectancy`: `+9.57 bps All-Trade Net Expectancy` | **MATCH (100%)** |
| **Retained Subgroup** | 110 retained / 84 excluded (+59.25 bps) | `#metric-historical-retained`: `110 / 84 Retained / Excluded (+59.25 bps on 110 retained)` | **MATCH (100%)** |
| **Simulated Attempts Created**| `0` (read-only execution) | `0` (zero order forms or attempts in UI) | **MATCH (100%)** |
| **Console Errors** | None | 0 JavaScript runtime errors | **MATCH (100%)** |

**Visual Screenshot Evidence:** Saved to `artifacts/v33_4m_analysis_dashboard.png` and mirrored in the brain artifact repository.

---

## E. Test Execution Results

All test suites were executed in the repository's local environment (`.venv_win\Scripts\python.exe`, Python 3.13.14, pytest 8.4.1):

| Test Suite Module | Test Scope | Passed | Failed | Skipped | Duration | Exit Code |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_v33_4m_htf_analysis.py` | Dedicated V33.4M-R acceptance gates (Gates 1–10 + 3 unit) | **13** | 0 | 0 | 70.51s | **0** |
| `tests/test_v33_4l_historical_evidence.py` | Historical evidence loader, 110/84 partition, SHA-256 validation | **10** | 0 | 0 | 4.88s | **0** |
| `tests/test_v33_4h_backtest_isolation.py` | Zero fresh backtests in analysis, HTTP 400 rejection, 6-state taxonomy | **6** | 0 | 0 | 7.91s | **0** |
| `tests/test_v33_4f_decision_stability.py` | Decision ID determinism, watermark invariance, strategy awareness | **4** | 0 | 0 | 3.12s | **0** |
| `tests/test_v33_4g_presentation_integrity.py` | No hardcoded forecast fallbacks, execution disabled, provenance checks | **6** | 0 | 0 | 3.65s | **0** |
| `tests/test_v32_49_scenario_qa.py` | Warm-up boundary, candle corruption fail-closed, atomic idempotency | **44** | 0 | 0 | 46.10s | **0** |

**Total Test Count:** **83 passed, 0 failed, 0 skipped across all test suites (100% pass rate).**

---

## F. Governance and Data Integrity Invariants

| Governance Dimension | Requirement | Observed Verification Evidence | Invariant Status |
| :--- | :--- | :--- | :---: |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` | Hardcoded in `models/authoritative_model_registry.py` and returned in `trade_authorization.research_authorization_status`. | **VERIFIED** |
| **Live Trading Gate** | Strictly `DISABLED` | `live_trading_enabled: false` verified across all routes (`/health`, `/api/tournament/analyse`). | **VERIFIED** |
| **Broker Execution** | Zero broker connectivity | Zero order submission adapters, broker SDKs, or trading endpoints exist. | **VERIFIED** |
| **Attempt Counter** | `attempts_created: 0` | Hardcoded invariant contract on read-only queries. Zero orders written to disk. | **VERIFIED** |
| **Prospective Evidence** | `NOT_VALIDATED`, N=0 | Verified via `HistoricalEvidenceLoader`: 0 shadow events, collector status `INACTIVE_AWAITING_MANAGEMENT_AUTHORIZATION`. | **VERIFIED** |
| **Historical Evidence** | Retrospective & non-confirmatory | Explicitly stamped as `RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY` across API and UI. | **VERIFIED** |
| **Cryptographic Integrity** | 100% match on protected hashes | All 14 protected data files and ledgers match registered SHA-256 baselines bit-for-bit. | **VERIFIED** |

---

## G. Initial and Final Git Status

- **Initial Git State:**
  - Branch: `main`
  - Commit SHA: `25d483f4c3646661b57311de9d0b53d2be881adb`
  - Pre-existing state: 82 modified files, 289 untracked files from earlier milestones (preserved intact).
- **Final Git State:**
  - Branch: `main` (no new branches created)
  - Commit SHA: `25d483f4c3646661b57311de9d0b53d2be881adb` (zero commits or pushes performed)
  - Modified files for Milestone V33.4M-R:
    1. `engine/regime_strategy_tournament.py` (fixed `compute_ema` short-circuit so 168 bars and full history evaluate to `TRENDING_BEARISH`; enforced stale blocking).
    2. `engine/htf_setup_detector.py` (reference semantics: `stop_reference`, `entry_reference`, `target_reference` strictly `None` when inactive; clarified explanation string).
    3. `engine/decoupled_analysis_engine.py` (added decoupled `calculation_status`, `data_freshness_status`, `setup_evaluation_eligibility`).
    4. `web/app.js` (rendered freshness badge `#badge-htf-freshness`, added `#text-htf-target`, added outcome IDs `#analysis-outcome-heading` and `#analysis-outcome-sub`, fixed falsy check on `data_age_hours`).
    5. `tests/test_v33_4m_htf_analysis.py` (13 dedicated acceptance tests covering Gates 1–10).
    6. `tests/test_v33_4h_backtest_isolation.py` (included `BLOCKED` in decoupled strategy assessment taxonomy).
    7. `scripts/qa/v33_4m_browser_verification.py` (Chrome DevTools Protocol browser verification script).
  - All pre-existing user modifications and untracked files remain strictly preserved.

---

## H. Defects and Targeted Repairs

During the course of the V33.4M-R closure investigation, four specific issues were identified and addressed under strict Limited Repair Authority:

1. **Defect 1: Regime Inconsistency Between API and Browser (Manager Review Finding 1)**
   - *Reproduction:* API evaluated direct dataset (42,177 bars) to `TRENDING_BEARISH`, while browser requested 168 bars and evaluated to `VOLATILITY_EXPANSION`.
   - *Root Cause:* `compute_ema(series, period)` had an artificial short-circuit: `if len(series) < period: return float(series[-1])`. Over 168 bars, `compute_ema(series, 200)` returned `series[-1]`, setting `ema200 == close` and causing the bear trend check to fail.
   - *Repair:* Replaced `compute_ema` with unconditional exponential moving average: `pd.Series(series).ewm(span=period, adjust=False).mean().iloc[-1]`. Over 168 bars, `ewm(200)` evaluates to $80,250.85, establishing `close ($76,985.40) < ema50 ($79,116.58) < ema200 ($80,250.85)` with `ADX=40.73 >= 20.0`.
   - *Verification:* Both 168 bars and 42,177 bars now evaluate identically to `TRENDING_BEARISH`. Verified by Test Gate 1 and CDP browser test.

2. **Defect 2: Active Stop Exposure on Blocked/Inactive Setups (Manager Review Finding 3)**
   - *Reproduction:* When `setup_status` was `NO_SETUP` or `BLOCKED`, the 20-bar Donchian channel low ($76,301.02) was returned in `stop_reference`.
   - *Root Cause:* `HTFSetupDetector` assigned `stop_reference = range_low` regardless of setup status.
   - *Repair:* In `engine/htf_setup_detector.py`, `stop_reference`, `entry_reference`, and `target_reference` are strictly `None` when `setup_status` is `NO_SETUP`, `BLOCKED`, `SETUP_FORMING`, or `DATA_UNAVAILABLE`. Channel boundaries are segregated in `completed_4h_bar` (`donchian_channel_high_20_4h` and `donchian_channel_low_20_4h`).
   - *Verification:* Verified by Test Gate 2, Gate 4, Gate 5, Gate 6, Gate 9, and CDP browser test.

3. **Defect 3: Missing Outcome Heading and Subtitle Element IDs (Agent 3 Finding)**
   - *Reproduction:* CDP DOM extraction queried `#analysis-outcome-heading` and `#analysis-outcome-sub`, returning empty strings.
   - *Root Cause:* In `web/app.js:18191`, the `<h2>` and `<p>` tags lacked `id` attributes.
   - *Repair:* Added `id: "analysis-outcome-heading"` and `id: "analysis-outcome-sub"` in `web/app.js`.
   - *Verification:* DOM extraction now extracts `"HTF SETUP BLOCKED"` and the complete factual explanation verbatim.

4. **Defect 4: JavaScript Falsy Coercion on Fresh Data (Agent 6 Adversarial Finding)**
   - *Reproduction:* `data_age_hours || "72.3"` in `web/app.js` evaluates `0` as falsy, displaying `"72.3"` when data age is `0`.
   - *Root Cause:* Use of logical OR `||` instead of nullish coalescing check.
   - *Repair:* Replaced with `analysisData.htf_setup.data_age_hours != null ? analysisData.htf_setup.data_age_hours : "unavailable"`.
   - *Verification:* Syntax verified with `node -c web/app.js`; CDP browser test passed.

---

## I. Final Acceptance Matrix

| ID | Acceptance Criterion | Required Evidence | Status |
| :---: | :--- | :--- | :---: |
| **A01** | Analysis calculations execute correctly | Realized volatility term structure, conformal risk envelopes, and excursion bounds computed | **PASS** |
| **A02** | Calculation status is distinct from data freshness | `calculation_status: SUCCESS` decoupled from `data_freshness_status: MARKET_DATA_STALE` | **PASS** |
| **A03** | Freshness is calculated dynamically | `observed_age_seconds = (now_utc - last_dt).total_seconds()` evaluated dynamically | **PASS** |
| **A04** | Source watermark is correct | SHA-256 fingerprint `0caf188f890c45e8` matches underlying 168-bar candle window | **PASS** |
| **A05** | Stale data blocks current setup eligibility | Age 73.6h > 2.0h operational threshold locks `setup_status = BLOCKED`, `trigger_status = STALE_DATA_BLOCKED` | **PASS** |
| **A06** | Regime mapping is canonical | 5 canonical regimes mapped; `TRENDING_BEARISH`, `RANGE_BOUND`, `TRANSITION_UNSUPPORTED` blocked | **PASS** |
| **A07** | API and dashboard regime match | Both API and browser DOM report `TRENDING_BEARISH` for identical `analysis_id: ana_ee29321e5f42` | **PASS** |
| **A08** | Browser displays the same API response | 100% field congruence verified between HTTP payload and DOM elements via CDP | **PASS** |
| **A09** | Stop/target semantics are correct | `stop_reference`, `entry_reference`, `target_reference` are strictly `null` (DOM: `Unavailable`) | **PASS** |
| **A10** | Historical evidence remains non-confirmatory | Explicitly stamped as `RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY` (+59.25 bps on 110 retained) | **PASS** |
| **A11** | Prospective validation remains N=0 | Verified `NOT_VALIDATED` (0 shadow events accumulated; collector inactive) | **PASS** |
| **A12** | Read-only Analysis creates zero attempts | `is_read_only: True`, `attempts_created: 0`; zero orders or simulated attempts written to database | **PASS** |
| **A13** | Live trading remains disabled | `live_trading_enabled: false` verified across all routes; zero broker execution adapters | **PASS** |
| **A14** | Dedicated V33.4M tests pass | 13/13 passed in 70.51s (`tests/test_v33_4m_htf_analysis.py`) | **PASS** |
| **A15** | All five regression suites pass | 70/70 passed in 65.66s (`test_v33_4l`, `test_v33_4h`, `test_v33_4f`, `test_v33_4g`, `test_v32_49`) | **PASS** |
| **A16** | Browser CDP verification passes | Headless Chrome CDP verification passed with zero errors (`scripts/qa/v33_4m_browser_results.json`) | **PASS** |
| **A17** | Protected data remains unchanged | 14/14 protected files, ledgers, and manifests match SHA-256 baselines bit-for-bit | **PASS** |
| **A18** | Git worktree is preserved | Branch remains `main`, commit SHA `25d483f4...`, zero uncommitted deletions or resets | **PASS** |
| **A19** | No unapproved process or collector launched | Process inspection confirmed zero background loops, collectors, or external data feeds | **PASS** |
| **A20** | Adversarial review finds no unresolved critical issue | Agent 6 adversarial review findings completely resolved and re-verified | **PASS** |

**Final Matrix Status: 20 of 20 criteria PASSED (100% COMPLIANT).**

---

## J. Manager Recommendation

Milestone **V33.4M-R** is complete, mathematically reconciled, and verified end-to-end.

**Recommendation:**
1. Formally close **Milestone V33.4M-R**.
2. Terminate all interactive Analysis feature development. The Analysis function is fully decoupled, causally bounded, and displays verified market intelligence alongside strict fail-closed strategy gating.
3. Transition directly to the next governed research phase: **Prospective Shadow Evidence Collection Protocol Activation** (milestone V33.5), strictly subject to management authorization to begin accumulating untouched out-of-sample forward blocks.

