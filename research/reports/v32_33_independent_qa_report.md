# BTCognitive V32.33 — Independent QA & Adversarial Review Report

**Date:** 2026-10-25  
**Version:** V32.33  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Lead Independent QA Specialist:** Agent G  
**Software Verification Verdict:** `SOFTWARE_QA_PASS`  

---

## 1. Adversarial Review Charter & Boundaries

Agent G operates under strict adversarial independence:
- Does not accept developer self-reported claims without verifiable execution traces.
- Independently reproduces test results and executes full regression suites.
- Launches the actual application server and exercises real user workflows through a browser.
- Injects edge cases, checks console cleanliness, tests multiple device viewports, and audits protected-file hashes.
- Never weakens assertions or edits criteria to manufacture a passing grade.

---

## 2. Automated Test Suite Execution Evidence

All test runs were executed against the active repository worktree on Python 3.13 (win32):

### 2.1 Core Pipeline, API, Directional, Collector, & L2 Gating Suite (86 tests)
```powershell
python -m pytest tests/test_strategy_to_alert_pipeline.py tests/test_entry_contracts_and_resolver.py tests/test_smart_entry_api.py tests/test_v32_25_directional_integration.py tests/test_prospective_shadow_collector.py tests/test_prospective_worker_and_resilience.py tests/test_isolated_real_http_server.py tests/test_coinbase_l2_collector_and_gating.py -v
```
- **Result:** `86 passed, 3 warnings in 20.48s`
- **Coverage Highlights:**
  - `test_reconciled_cost_accounting_87bps` PASSED
  - `test_candidate_setup_immutability` PASSED
  - `test_smart_entry_endpoint_live_terminal_telemetry_flow` PASSED
  - `test_v32_25_directional_gbdt_inference_probabilities` PASSED
  - `test_l2_collector_disabled_by_default` PASSED
  - `test_cont_kukanov_stoikov_ofi_known_answer` PASSED
  - `test_protected_files_isolation_assertion` PASSED
  - `test_real_http_smart_entry_pipeline_post` (loopback TCP) PASSED

### 2.2 V9 Acceptance & Data Integrity Suite (5 tests)
```powershell
python -m pytest tests/test_v9_data_integrity.py -v
```
- **Result:** `5 passed, 1 warning in 1.98s`
- **Coverage Highlights:**
  - `test_fourier_first_passage_invariants` PASSED
  - `test_scenario_contract_subhourly_preserves_verified_hourly_metadata` PASSED
  - `test_counterfactual_lab_metadata_and_drag_itemization` PASSED
  - `test_meie_ignition_reproduction` PASSED (41.5 gross, 9.3 drag, 32.2 net)
  - `test_arena_active_paper_position_returns_typed_subhourly_state` PASSED

### 2.3 Strategy Selection & Audit Resolution Suite (15 tests)
```powershell
python -m pytest tests/test_strategy_selection_engine.py tests/test_v32_16_audit_resolutions.py -v
```
- **Result:** `15 passed in 0.84s`
- **Coverage Highlights:**
  - `test_all_five_archetypes_evaluated_independently` PASSED
  - `test_hard_eligibility_gate_filters_low_sample_n` PASSED
  - `test_user_direction_preference_rejection_guardrail` PASSED
  - `test_dynamic_market_shift_vacuum_wins_on_liquidity_thinning` PASSED
  - `test_single_cost_source_consistency` PASSED
  - `test_spot_short_maps_strictly_to_cash` PASSED

### 2.4 Frontend Unit & Polling Budget Suite (8 test areas)
```powershell
node tests_frontend.js
```
- **Result:** `All Frontend Unit Tests Passed Successfully!`
- **Coverage Highlights:**
  - Formatters: PASSED
  - In-flight request deduplication: PASSED
  - TTL response caching: PASSED
  - 429 backoff handling: PASSED
  - Polling budget: `29.5 req/min` (Server limiter: 60 req/min) PASSED
  - Smart Entry dashboard integration markers: PASSED
  - V32.31 Coinbase L2 Microstructure Gating UI markers: PASSED

**Total Automated Tests:** **114 Passed, 0 Failed (100% Pass Rate)**

---

## 3. Independent Browser QA Session

An independent browser subagent launched against `http://127.0.0.1:8000/` performed an exhaustive inspection of all views, controls, and error states:

### 3.1 Route & Interaction Verification
1. **Live Terminal (`#/terminal`):**
   - Verified live spot price ($80,603.99), 24h change, high/low, realized vol.
   - Tested interval toggles (1m, 5m, 15m, 1H, 4H, 1D): series updated dynamically without redraw glitches.
   - Tested Focus / Pro Quant mode toggle: expanded telemetry rendered properly.
   - Verified header safety badges: `READY · AUTHORIZED (VOLATILITY RISK)` / `EXECUTION DISABLED — ANALYSIS ONLY`.
2. **Smart Entry (`#/smart-entry`):**
   - Clicked "Evaluate Real-Time Setup": Candidate geometry or abstain note rendered with zero DOM errors.
   - Clicked "Load Synthetic Vol Breakout Demo": Injected expansion parameters, updated candidate cards and directional hypothesis table live.
   - Inspected Coinbase L2 Gating Card: Badges `COLLECTOR: DISABLED BY DEFAULT` and `LIVE TRADING: DISABLED` displayed.
3. **AI Experiment Arena (`#/arena`):**
   - Inspected strategy leaderboard, virtual bankroll, and paper trade position telemetry.
   - Verified that all strategies are penalized with realistic transaction drag.
4. **Archived Research Evidence (`#/research`):**
   - Navigated longitudinal research report catalog.
   - Clicked "Inspect Source Markdown ↗" on report card: Safe modal overlay opened with sanitized markdown content.
   - Tested modal dismissal via close button "✕" and Escape key.

### 3.2 Viewport Responsiveness
- **Desktop (1536x800):** Clean multi-column grid, zero horizontal scrollbar on body, full chart visibility.
- **Tablet (768x1024):** Sidebar collapsed into responsive stack, touch-friendly tap targets, no text clipping.
- **Mobile (375x812):** Single-column layout, horizontal scroll preserved for wide data tables, cards resize cleanly.

### 3.3 Console Log Inspection
- **Total Console Errors:** **0**
- **Total Unhandled Exceptions:** **0**
- **Network Request Failures:** **0** (All API requests returned HTTP 200)

---

## 4. Protected-File SHA-256 Audit

The 5 explicitly protected files were audited before and after all modifications:

| File Path | Initial Baseline SHA-256 | Post-Verification SHA-256 | Bit-Identical? |
| :--- | :--- | :--- | :---: |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **YES (MATCH)** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **YES (MATCH)** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **YES (MATCH)** |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **YES (MATCH)** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **YES (MATCH)** |

**Integrity Verification:** 100% PASS. Zero bytes altered in protected artifacts.

---

## 5. Process & Socket Hygiene Confirmation

- Post-test PowerShell command: `Get-NetTCPConnection -LocalPort 8000 -State Listen`
- **Result:** No listening connections found (Exit code 1).
- **Daemon Status:** Cleanly stopped; 0 orphaned background tasks.

---

## 6. Independent QA Release Verdict

Based on 114 passing tests, zero console errors, full multi-viewport responsiveness, clean socket teardown, and 100% protected file integrity:

$$\mathbf{SOFTWARE\_QA\_PASS}$$

*Note: In accordance with BTCognitive operating rules, this software QA pass does NOT imply or authorize live trading or economic alpha. The research posture remains `OFFLINE_RESEARCH_ONLY` with live trading `DISABLED`.*
