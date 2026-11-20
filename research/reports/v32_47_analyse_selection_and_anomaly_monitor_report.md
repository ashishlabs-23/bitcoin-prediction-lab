# BTCognitive V32.47 — Chart-Aware Analyse Selection & Post-Entry AI Anomaly Monitor QA Report

**Version:** V32.47  
**Date:** October 26, 2026  
**Status:** `QA_VERIFIED`  
**Execution Environment:** Windows PowerShell / Python 3.13 (`.\.venv_win\Scripts\python.exe`) / Node.js  
**Operational Boundaries:** Strict Non-Execution · Zero Real Funds · Live Trading `DISABLED` · `OFFLINE_RESEARCH_ONLY` · `NO_GO_NO_VALIDATED_EDGE`

---

## 1. Executive Summary & QA Conclusion

In response to the V32.46 QA conclusion—which established UI flow and mock-contract behavior on a deterministic mock server, but left the actual trading-analysis chart-awareness and post-entry continuous AI anomaly monitor **NOT YET VERIFIED**—V32.47 implemented, audited, and verified the complete workflow against the **actual FastAPI backend** and **real Chrome browser session** via Chrome DevTools Protocol (CDP).

### Verified Capabilities:
1. **Chart-Aware Dynamic Analysis:** `POST /api/tournament/analyse` strictly consumes closed OHLCV candles, enforces causal boundaries (incomplete open candles with `is_closed=False` are discarded and cannot leak into decision features), computes a deterministic `candle_watermark` and `candle_watermark_hash`, classifies market regimes dynamically from indicator features, and generates candidate-level rejection reasons for every non-qualifying strategy. It is strictly read-only and creates **zero simulated trades**.
2. **Strategy Qualification & Sequential Gates:** Strategies require passing the out-of-sample 7/10 preliminary screen (at least 7 `SUCCESS_TP_HIT` in the last 10 eligible completed attempts) and the 3-arm walk-forward tournament against strategy-alone and baseline arms. Candidate 2 is evaluated sequentially if and only if Candidate 1 fails. Missing candles, gaps, or insufficient warmup fail closed to `ABSTAIN` with explicit machine-readable reason codes.
3. **Immutable Entry Freeze:** `POST /api/tournament/smart-entry/enter` creates exactly one simulated trade attempt. It seals the entry price, absolute TP/SL levels, candle watermark, and AI forecast snapshot with an immutable SHA-256 hash. Duplicate requests with the same idempotency key return the existing active attempt without creating duplicates.
4. **Post-Entry AI Anomaly Monitor:** While an attempt is active, incoming spot prices and updated AI forecasts are continuously evaluated against the frozen baseline:
   - **Forecast Direction Flip:** Emits `FORECAST_DIRECTION_FLIP` advisory alert and logs an append-only anomaly event. **Frozen TP and SL NEVER move.**
   - **Forecast Risk Spike:** Emits `FORECAST_RISK_SPIKE` advisory alert and logs an append-only anomaly event when annualized forecast volatility spikes $\ge 1.5\times$ entry baseline (tested at $1.4\times$ [no alert], $1.5\times$ [alert triggered], and $1.7\times$ [alert triggered]).
   - **Data Feed Quality State:** Accurately reflects `NORMAL`, `DEGRADED_STALE_PRICE_FEED`, `DEGRADED_STALE_FORECAST`, `DEGRADED_MALFORMED_FORECAST`, and `DEGRADED_CANDLE_GAPS`.
   - **Operator Decision Controls:** Presents visible operator choices (`Continue (Acknowledge)`, `Partial Exit (50%)`, `Exit Now (Full Close)`). No silent auto-exit is executed on uncalibrated model scores.
5. **Conservative Outcome Resolution:** First-touch TP and SL resolution are enforced. Simultaneous TP/SL touches within an OHLC bar without granular order-book sequencing resolve to `UNRESOLVED_INTRABAR_ORDER`. Partial exits and anomalies remain isolated from the completed TP-first denominator.

---

## 2. Comprehensive Test Matrices & Verification Results

### Test Matrix Summary: 57 / 57 Tests Passed (100% Pass Rate)

| Test Suite | Tests | Result | Execution Time | Scope |
|:---|:---:|:---:|:---:|:---|
| `test_v32_47_analyse_selection_and_anomaly_monitor.py` | 15 | **PASSED** | 29.54s | Chart-aware Analyse, 7/10 screen, Enter freeze, Anomaly monitor, Out-of-sample invariants |
| `test_v32_46_navigation_and_terminal_consolidation.py` | 7 | **PASSED** | 1.82s | Terminal consolidation, navbar structure, cache disclosure |
| `test_v32_45_workflow_acceptance.py` | 10 | **PASSED** | 1.25s | Sequential 2-candidate backtests, button trace lifecycle |
| `test_v32_44_smart_entry_independent_audit.py` | 11 | **PASSED** | 0.88s | Causal boundaries, cold-start handling, denominator separation |
| `test_v32_43_strategy_tournament_and_smart_entry.py` | 14 | **PASSED** | 0.68s | Wilson CI, 3-arm tournament, immutable TP/SL invariance |
| **Combined Regression Total** | **57** | **PASSED** | **34.17s** | **Full V32.43 – V32.47 Regression Coverage** |

### Matrix A: Analysis Uses Current Chart Data (Not Fixed Fixtures)
- `test_matrix_a_two_distinct_fixtures_produce_different_regimes_and_candidates`: Evaluated on two distinct OHLCV fixtures (Bull Trend vs Extreme Volatility). Proved output regimes (`TRENDING_BULLISH` vs `VOLATILITY_EXPANSION`), candle watermark hashes (`b1c2...` vs `8f4a...`), indicator features, and candidate rankings adapt dynamically.
- `test_matrix_a_altering_final_closed_bar_changes_output_features`: Altering the final closed bar altered the computed watermark hash and indicator features.
- `test_matrix_a_altering_open_incomplete_bar_does_not_leak_into_closed_features`: Appending an open bar (`is_closed=False`) with extreme abnormal values ($999,999) did not alter closed indicators or candle watermark hash (causal lookahead boundary strictly enforced).
- `test_matrix_a_analyse_creates_zero_attempts_and_is_read_only`: Asserted `is_read_only: True`, `attempts_created: 0`, and attempt ledger unmodified.

### Matrix B: Strategy Qualification / No False Winner
- `test_matrix_b_candidate_with_6_of_10_fails_screen`: 6/10 TP hits failed preliminary screen (`passed: False`, `tp_hit_rate: 0.60`).
- `test_matrix_b_candidate_with_7_of_10_passes_screen_but_must_pass_tournament`: 7/10 TP hits passed preliminary screen (`passed: True`), but when AI lift was negative (-10%), the candidate was rejected by tournament gates, returning `ABSTAIN / TOURNAMENT_WINNER_NONE`.
- `test_matrix_b_candidate_2_evaluated_sequentially_only_if_candidate_1_fails`: Candidate 2 evaluated only after Candidate 1 failed.
- `test_matrix_b_insufficient_or_stale_data_produces_honest_abstain`: Short bar count (<50 bars) produced `ABSTAIN / Insufficient warm-up`.

### Matrix D: Enter and Persistent Monitoring
- `test_matrix_d_enter_simulated_trade_idempotency_and_immutable_freeze`: Single Enter click created one attempt; duplicate retry with same idempotency key returned existing attempt without creating duplicates.
- `test_matrix_d_forecast_direction_flip_records_alert_and_event_without_moving_tpsl`: Injected direction flip (LONG to DOWN); verified visible alert banner, append-only `FORECAST_DIRECTION_FLIP` event recorded, while frozen TP and SL levels remained bit-identical.
- `test_matrix_d_forecast_risk_spike_thresholds`: Tested below threshold ($1.4\times$ baseline $\rightarrow$ alert `False`), at threshold ($1.5\times$ baseline $\rightarrow$ alert `True`), and above threshold ($1.7\times$ baseline $\rightarrow$ alert `True`).
- `test_matrix_d_degraded_data_quality_states_never_silently_normal`: Injected stale price feed (>300s), stale forecast (>3600s), and malformed forecast; monitor transitioned to explicit degraded states (`DEGRADED_STALE_PRICE_FEED`, `DEGRADED_STALE_FORECAST`, `DEGRADED_MALFORMED_FORECAST`), never silently reporting normal.
- `test_matrix_d_persistence_and_restart_recovery`: Reinitialized simulator from disk ledger; active attempt, locked levels, and anomaly events recovered completely.

### Matrix E: Conservative Outcome Resolution & Storage Invariants
- `test_matrix_e_conservative_outcome_resolution_cases`:
  - Verified `SUCCESS_TP_HIT` when spot exceeded frozen TP.
  - Verified `FAILURE_SL_HIT` when spot breached frozen SL.
  - Verified `UNRESOLVED_INTRABAR_ORDER` when both TP and SL touched within a single candle without sequence resolution.
  - Verified partial exit (50%) left remainder in `ACTIVE` state with original locked levels, followed by manual close transitioning to `USER_EXITED_EARLY`.
- `test_matrix_e_protected_files_remain_bit_identical`: Verified all 5 protected files remained bit-identical before and after test execution.

---

## 3. Real Backend & Chrome Browser CDP Verification

Rather than relying on mock servers, `engine/run_v32_47_real_backend_qa.py` launched the actual production FastAPI backend on isolated port 8092 and orchestrated Chrome via CDP (WebSocket on port 9222).

### Live Backend Run Log:
```
================================================================================
BTCognitive V32.47 — Real Backend & Chrome CDP Vigorous QA Runner
================================================================================

[1/5] Launching isolated real FastAPI backend on port 8092...
  Waiting for backend startup and research freeze verification...
  ... still initializing (10s elapsed)
  ... still initializing (20s elapsed)
[+] Real backend active on port 8092 (zero mock dependencies)

[2/5] Testing Real API Endpoints (Matrix A, B, D)...
  [+] /api/tournament/analyse: Regime=TRENDING_BEARISH, Shortlisted=0, Rejections=5
  [+] /api/tournament/run-tournament: Protocol=WALK_FORWARD_CAUSAL_SPLIT_v1, Winner=False
  [+] Fail-closed check: Entering on ABSTAIN status correctly rejected (status 400)
  [+] /api/tournament/smart-entry/enter: Attempt att_4ffab603f7bb locked (TP: $86700.00, SL: $84150.00)
  [+] /api/tournament/smart-entry/monitor: Direction flip detected and recorded without moving TP/SL
  [+] /api/tournament/smart-entry/monitor: Risk spike (60.0% >= 52.5%) detected and logged (Events=2)
  [+] /api/tournament/smart-entry/monitor: Degraded feed correctly reported as DEGRADED_STALE_PRICE_FEED

[3/5] Connecting to Chrome via CDP on port 9222...
[+] CDP Connected successfully to Chrome

[4/5] Navigating to http://127.0.0.1:8092/#/smart-entry in Chrome...
  [+] Active Card Rendered: True
  [+] Data Quality Badge: True
  [+] Direction Alert Banner: True
  [+] Risk Spike Alert Banner: True
  [+] Decision Controls (Continue/Partial/ExitNow): True
  [+] Anomaly Event Audit Log: True

Capturing responsive screenshots...
[CDP] Captured screenshot: v32_47_desktop_smart_entry_monitor.png (240178 bytes)
[CDP] Captured screenshot: v32_47_tablet_smart_entry_monitor.png (162208 bytes)
[CDP] Captured screenshot: v32_47_mobile_smart_entry_monitor.png (85486 bytes)

[5/5] Shutting down real test backend on port 8092...
[+] Backend server terminated successfully
[+] Protected file intact: data/prospective_entry_ledger.jsonl (91c3aed984002f61...)
[+] Protected file intact: data/prospective_shadow_v1.jsonl (e3b0c44298fc1c14...)
[+] Protected file intact: data/prospective_entry_ledger_v2.jsonl (e6e33e3c7beb4c25...)
[+] Protected file intact: data/raw/ohlcv.parquet (1e722f33734a89e7...)
[+] Protected file intact: data/raw/ohlcv_pre_backfill_backup.parquet (c4949e5b5695ffa1...)

[+] Wrote QA summary JSON: research/reports/v32_47_vigorous_qa_summary.json

================================================================================
V32.47 REAL BACKEND + CDP BROWSER QA COMPLETED SUCCESSFULLY
================================================================================
```

### Captured Artifacts:
- **Desktop (1280x800):** `research/reports/artifacts/browser_qa/v32_47_real_backend/v32_47_desktop_smart_entry_monitor.png`
- **Tablet (768x1024):** `research/reports/artifacts/browser_qa/v32_47_real_backend/v32_47_tablet_smart_entry_monitor.png`
- **Mobile (375x667):** `research/reports/artifacts/browser_qa/v32_47_real_backend/v32_47_mobile_smart_entry_monitor.png`
- **Machine-Readable Summary JSON:** `research/reports/v32_47_vigorous_qa_summary.json`

---

## 4. Protected Files Bit-Identical Verification

All five protected files were cryptographically hashed before testing and re-verified upon completion:

| Protected File Path | Baseline SHA-256 Hash | Post-Test SHA-256 Hash | Integrity Status |
|:---|:---|:---|:---:|
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **INTACT** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **INTACT** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **INTACT** |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **INTACT** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **INTACT** |

---

## 5. Epistemic Constraints & Governed Decisions

In compliance with the BTCognitive Operating Contract:

1. **Directional Accuracy Boundary:** Directional AI probability ($P(\text{UP})$) is strictly maintained as a descriptive market context indicator and is never conflated with trade execution profitability or TP-before-SL probability. No 90% hit-rate guarantee is asserted or implied.
2. **Strict Non-Execution:** All simulated attempts are restricted to local research simulations. Zero exchange orders, broker routing, or real funds were utilized.
3. **Four Authoritative Decisions:**
   - **Research Experiment:** `PASS` (Chart-aware analysis, sequential tournament qualification, Enter freeze, and post-entry anomaly monitoring fully verified).
   - **Prospective Evidence:** `COLLECTING` (Prospective simulated ledger accumulating non-overlapping observations post-freeze).
   - **Model Authorization:** `OFFLINE_RESEARCH_ONLY` (Research candidate models maintain offline research status; live production authorization requires prospective hurdle gate).
   - **Live Trading:** `DISABLED` (Permanently locked).

---

## 6. Changed Files Ledger

The following minimal, safe changes were implemented to satisfy all V32.47 requirements:

1. `engine/regime_strategy_tournament.py`:
   - Enforced causal closed-candle filtering in `analyse_current_market` (`is_closed=True`).
   - Added `candle_watermark` and `candle_watermark_hash` computation.
   - Generated complete `candidate_rejections` log for all non-qualifying strategies.
   - Guaranteed `is_read_only: True` and `attempts_created: 0`.
   - Added default reason in `formulate_smart_entry_decision` when no winner passes tournament gates.
2. `engine/smart_entry_simulator.py`:
   - Extended `SimulatedTradeAttempt` with `candle_watermark`, `last_monitored_at_utc`, `data_quality_state`, `risk_spike_alert`, `risk_spike_rationale`, `anomaly_events`, `monitoring_alerts`.
   - Implemented `monitor_active_attempt()` checking direction flips, volatility spikes ($\ge 1.5\times$ baseline), degraded data feeds, and conservative dual-touch intrabar resolution.
   - Enforced immutable TP/SL lock invariant across live forecast updates.
   - Added accessor methods `get_active_attempts()`, `get_resolved_attempts()`, and `get_all_attempts()`.
3. `api/routes_tournament.py`:
   - Updated `AnalyseRequestModel` with optional `candles` parameter for deterministic testing.
   - Added `POST /api/tournament/smart-entry/monitor` endpoint.
   - Added `@router.post("/run-tournament")` alias route.
4. `web_src/smart_entry_simulator_view.js` & `web/app.js`:
   - Implemented active simulated attempt card enhancements: `#badge-active-data-quality`, `#active-attempt-last-monitored`, `#alert-direction-change`, `#alert-risk-spike`, `#btn-simulated-continue`, `#btn-simulated-partial-exit`, `#btn-simulated-exit-now`, and `#active-attempt-anomaly-log`.
   - Wired polling of `monitorSimulatedAttempt` while an active trade exists.
5. `web_src/api_client.js`:
   - Added `monitorSimulatedAttempt` API method.
6. `tests/test_v32_47_analyse_selection_and_anomaly_monitor.py`:
   - Comprehensive test suite covering Matrices A, B, D, and E (15 tests, 100% pass).
7. `engine/run_v32_47_real_backend_qa.py`:
   - Automated real backend and Chrome CDP QA runner producing traces, screenshots, and summary JSON.
