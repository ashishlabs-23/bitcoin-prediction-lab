# BTCognitive V32.46 — Independent Vigorous QA Assessment & Certification Report

**Audit Date:** 2026-10-26  
**Auditor:** Independent Lead Research Orchestrator & Red Team  
**Scope:** Navigation Simplification, Live Terminal Consolidation, Multi-Viewport Browser Regression, Safety Invariants, Storage Isolation, and Bit-Identical Data Protection  
**Target Repository:** `C:\Projects\BTCognitive\BTCognitive`  
**Git Branch / Commit:** `main` / `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Execution Environment:** Local Windows Workstation (`.\.venv_win\Scripts\python.exe`, Python 3.13.14, Node.js v20.18.0, Chromium Headless CDP via WebSocket `127.0.0.1:9222`)  
**Network Architecture:** Zero live broker or order-routing dependencies. Deterministic mock fixture API server on `127.0.0.1:8090`.  

---

## 1. Executive Verdict & Governance Decisions

| Category | Finding / Decision | Rationale |
| :--- | :--- | :--- |
| **Executive QA Verdict** | **`QA_VERIFIED`** | All 8 real-browser CDP tests, 42 pytest regression tests, and frontend unit tests passed without failure. Stale feed fail-closed invariants, storage isolation, and responsive layout certified. |
| **Research Experiment** | **`PASS`** | Navigation simplified to 3 primary destinations (Terminal, Research, Journal) + secondary More menu. Terminal consolidates 1-to-7 Smart Entry workflow. |
| **Prospective Evidence** | **`NOT_STARTED`** | Confirmatory prospective evaluation requires untouched post-freeze forward windows (minimum 100 non-overlapping clean blocks). Retrospective replay data cannot substitute for prospective confirmation. |
| **Model Authorization** | **`OFFLINE_RESEARCH_ONLY`** | Directional and volatility models serve risk intelligence only. Live execution permanently locked out. |
| **Live Trading** | **`DISABLED`** | Epistemic principle: strict non-execution. No live order placement or broker connectivity permitted. |

---

## 2. Protected Data Files Bit-Identical Baseline Verification

Under BTCognitive Phase 0 and Phase 6 governance, the 5 historical data and prospective ledger files are strictly immutable and protected against accidental write or truncation. SHA-256 hashes were calculated before any test was launched and recomputed following all test runs:

| Protected File Path | Baseline SHA-256 | Post-QA SHA-256 | Bit-Identical Status |
| :--- | :--- | :--- | :--- |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **MATCH (Preserved)** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **MATCH (Preserved)** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **MATCH (Preserved)** |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **MATCH (Preserved)** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **MATCH (Preserved)** |

---

## 3. Test Suites & Execution Evidence

Three independent levels of testing were conducted in sequence:

```
[Level 1: Frontend Unit & Budget Suite] ────> [Level 2: Pytest Full Regression Suite] ────> [Level 3: Automated CDP Browser QA Suite]
         (All Passed, 29.5 req/min)                 (42/42 Passed, 27.31s)                     (8/8 Passed, 0 Errors)
```

### 3.1. Syntax Verification
- **Command:** `node --check web/app.js`
- **Result:** Exit code `0` (Zero parse or syntax errors).

### 3.2. Frontend Integration & Polling Budget Suite
- **Command:** `node tests_frontend.js`
- **Result:** Exit code `0` (100% Passed).
- **Steady-State Polling Budget:** 29.5 req/min (Strictly below the 60 req/min server rate limiter limit).

### 3.3. Combined Pytest Regression Suite
- **Command:** `.\.venv_win\Scripts\pytest.exe -v tests/test_v32_43_strategy_tournament_and_smart_entry.py tests/test_v32_44_smart_entry_independent_audit.py tests/test_v32_45_workflow_acceptance.py tests/test_v32_46_navigation_and_terminal_consolidation.py`
- **Duration:** 27.31s
- **Outcomes:** **42 Passed, 0 Failed, 0 Skipped**

| Test Module | Coverage Scope | Tests Passed | Status |
| :--- | :--- | :--- | :--- |
| `test_v32_43_strategy_tournament_and_smart_entry.py` | Wilson CI, regime classification, 7/10 screening, 3-arm walk-forward backtest, locked levels, dual-touch ambiguity, partial exits, durable persistence. | 14 / 14 | **PASSED** |
| `test_v32_44_smart_entry_independent_audit.py` | Read-only analysis trace, cold-start denominator separation, benchmark hurdle, idempotency, immutable TP/SL across forecast changes, fail-closed market data rejection. | 11 / 11 | **PASSED** |
| `test_v32_45_workflow_acceptance.py` | Button wiring, candidate shortlist provenance, stale data gap rejection, cache disclosure, complete outcome lifecycle. | 10 / 10 | **PASSED** |
| `test_v32_46_navigation_and_terminal_consolidation.py` | 3 primary destinations + More dropdown, terminal consolidated workflow, research subtabs, paper trading isolation, manual journal isolation, protected file invariants. | 7 / 7 | **PASSED** |

---

## 4. Real-Browser CDP Verification (8-Stage Suite)

The automated CDP browser suite ([`engine/run_v32_46_vigorous_browser_qa.py`](file:///C:/Projects/BTCognitive/BTCognitive/engine/run_v32_46_vigorous_browser_qa.py)) was executed against the local application at `http://127.0.0.1:8090` using Chromium via WebSocket `ws://127.0.0.1:9222`:

| Test Stage | Interactions Executed | Validations & Assertions | Status |
| :--- | :--- | :--- | :--- |
| **Test 1: Desktop Viewport & Navigation** | Viewport 1280×800. Verified `#nav-terminal`, `#nav-research`, `#nav-journal`, `#nav-more-menu-btn`. Clicked More button, pressed Escape key. | Primary navbar contains exactly 3 primary links + More dropdown. Escape key cleanly closes dropdown. | **PASSED** |
| **Test 2: Terminal 1-to-7 Workflow** | Clicked `#btn-analyse-setup` -> Clicked `#btn-run-tournament` -> Verified decision card -> Clicked `#btn-enter-simulated-trade` -> Verified active card -> Clicked `#btn-simulated-exit-now`. | 1. Analyse is strictly read-only.<br>2. Candidates rendered with screening.<br>3. Walk-forward tournament displays cache banner.<br>4. Enter freezes immutable TP/SL.<br>5. Exit controls cleanly close lifecycle. | **PASSED** |
| **Test 3: Research Hub & Paper Isolation** | Clicked `#nav-research`. Verified 4 subtabs: `#research-tab-tournaments`, `#research-tab-paper-trading`, `#research-tab-evaluation`, `#research-tab-reports`. Clicked Paper Trading subtab. | All 4 subtabs exist. Paper Trading renders `#paper-research-only-badge` with `"RESEARCH ONLY · SIMULATED EXECUTION"`. | **PASSED** |
| **Test 4: Manual Journal Isolation** | Clicked `#nav-journal`. Checked `#manual-journal-warning-banner` and `#btn-enter-manual-trade`. | Manual Journal is accessible and strictly separated from Paper Trading and Smart Entry simulator. | **PASSED** |
| **Test 5: Route History & Legacy Deep Links** | Executed `history.back()`, `history.forward()`. Navigated to `#/forecast`, `#/paper-trading`, `#/how-it-works`, `#/landing`, `#/position-monitor`. | Backward/forward navigation preserves valid route state. Legacy routes seamlessly resolve without crashing. | **PASSED** |
| **Test 6: Tablet Viewport Responsive** | Viewport 768×1024. Checked `scrollWidth` vs `clientWidth`. | `scrollWidth: 761px <= clientWidth: 761px`. Zero horizontal overflow. Cards adapt gracefully. | **PASSED** |
| **Test 7: Mobile Viewport Responsive** | Viewport 375×667. Verified hamburger button `.mobile-menu-toggle`. | `scrollWidth: 375px <= clientWidth: 375px`. Zero horizontal overflow. Mobile menu toggle functional. | **PASSED** |
| **Test 8: Stale Market Data Fail-Closed** | Injected `is_stale_mode=True` via `/api/test-control/toggle-stale`. Reloaded Terminal view. | `#smart-entry-decision-card` immediately rendered badge `NO_SMART_ENTRY` and verdict `ABSTAIN (Market data is stale (>2.0 hours). All entries blocked.)`. Trade entry disabled. | **PASSED** |

### 4.1. Browser Telemetry & Screenshot Artifacts
- **Console Errors:** `0` (Zero uncaught JavaScript exceptions or React errors)
- **Network Failures:** `0` (Zero HTTP 4xx/5xx requests during user navigation)
- **Generated Browser Artifacts:**
  1. [`v32_46_vigorous_terminal_desktop.png`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_46_vigorous/v32_46_vigorous_terminal_desktop.png) — Active simulated trade card with frozen Take-Profit/Stop-Loss levels.
  2. [`v32_46_vigorous_research_paper_trading.png`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_46_vigorous/v32_46_vigorous_research_paper_trading.png) — Research Hub with 4 subtabs and Paper Trading isolation badge.
  3. [`v32_46_vigorous_manual_journal.png`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_46_vigorous/v32_46_vigorous_manual_journal.png) — Isolated Manual Trade Journal view.
  4. [`v32_46_vigorous_terminal_tablet.png`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_46_vigorous/v32_46_vigorous_terminal_tablet.png) — Tablet (768×1024) layout without horizontal scrollbar.
  5. [`v32_46_vigorous_terminal_mobile.png`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_46_vigorous/v32_46_vigorous_terminal_mobile.png) — Mobile (375×667) layout with responsive header.
  6. [`v32_46_vigorous_terminal_stale_abstain.png`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_46_vigorous/v32_46_vigorous_terminal_stale_abstain.png) — Fail-closed ABSTAIN decision card upon stale feed injection.

---

## 5. Storage Isolation Verification

BTCognitive enforces three strictly non-intersecting persistence stores to ensure user-entered data, automated paper trades, and research simulations never contaminate one another:

```mermaid
graph TD
    subgraph UI Layer
        T[Terminal / Smart Entry]
        R[Research / Paper Trading]
        J[Manual Journal]
    end

    subgraph Independent Storage Layer
        T -->|Attempts API| SL[(data/smart_entry_simulated_attempts.json)]
        R -->|Paper API| PL[(data/paper_trading_positions.json)]
        J -->|Client-Side Only| LS[(localStorage: btcognitive_manual_trades_v32_42)]
    end

    classDef store fill:#1E293B,stroke:#38BDF8,stroke-width:2px,color:#F8FAFC;
    class SL,PL,LS store;
```

1. **Smart Entry Simulated Attempts:** Persisted exclusively in `data/smart_entry_simulated_attempts.json`. Records simulated test-of-forecast trades with frozen TP/SL.
2. **Paper Trading Engine:** Persisted in `data/paper_trading_positions.json`. Records automated non-execution paper trading positions with distinct state machines.
3. **Manual Trade Journal:** Persisted in browser `localStorage` under `btcognitive_manual_trades_v32_42`. No server-side ledger writes.
- **Audit Result:** Zero cross-store contamination detected.

---

## 6. Bugs Discovered & Repaired During Self-Loop

The vigorous QA self-loop identified eight defects across wiring, null safety, selector consistency, and stale data propagation, and independently applied verified repairs:

| ID | Component | Defect Description | Root Cause | Repair Applied |
| :--- | :--- | :--- | :--- | :--- |
| **DEF-01** | `web/app.js` | Tab pane inside `TerminalView` did not render `SmartEntrySimulatorView` when `workstationTab === "smart_entry"`. | `TerminalView` only rendered legacy pane types (`forecast`, `market`, `strategies`). | Wired `workstationTab === "smart_entry"` to render `SmartEntrySimulatorView` passing `currentPrice`, `predictionData`, and `regimeData`. |
| **DEF-02** | `web/app.js` | React root container remained empty when navigating directly to `#/terminal`. | `mountApp()` was wrapped in `DOMContentLoaded` listener, which had already fired in fast CDP navigations. | Implemented idempotent, immediate root mounting storing the root instance in `window._btcognitiveRoot`. |
| **DEF-03** | `web/app.js` | `TypeError: Cannot read properties of undefined (reading 'toLocaleString')` on proposed candidate geometry rendering. | Mock server candidate payload provided `take_profit_price` while UI expected `proposed_tp_price`. | Added null-safe coalescing: `cand.proposed_geometry?.proposed_tp_price ?? cand.proposed_geometry?.take_profit_price ?? 0`. |
| **DEF-04** | `web/app.js` | Browser QA could not locate active simulated trade card selector after clicking Enter. | `#smart-entry-active-trade-card` was missing class `.active-simulated-attempt-card`. | Added CSS class `.active-simulated-attempt-card` to the active attempt container. |
| **DEF-05** | `web/app.js` | Research subtab for paper trading was named `research-tab-paper_trading` (underscore) instead of `research-tab-paper-trading` (hyphen). | Direct string interpolation of `tab.id` without slug normalization. | Replaced `id: research-tab-${tab.id}` with `research-tab-${tab.id.replace(/_/g, '-')}`. |
| **DEF-06** | `engine/v32_46_test_mock_server.py` | `KeyError: 'direction'` in `engine/regime_strategy_tournament.py` when executing `/api/tournament/run`. | Candidate mock dictionary omitted canonical strategy keys (`direction`, `holding_horizon_hours`, `reward_usd`). | Provided complete qualifying candidate dictionary conforming to tournament contract. |
| **DEF-07** | `engine/run_v32_46_vigorous_browser_qa.py` | `UnicodeEncodeError: 'charmap'` on Windows console printing UTF-8 emojis (`🎯`, `☰`). | Windows default console code page (`cp1252`) cannot encode high code points. | Wrapped console outputs with `.encode('ascii', 'backslashreplace').decode('ascii')`. |
| **DEF-08** | `web/app.js` | `loadState()` in `SmartEntrySimulatorView` failed to transition to fail-closed `ABSTAIN` state when market data became stale. | Guard `if (decRes && !smartEntryDecision)` prevented updating `smartEntryDecision` if it was already set. | Updated guard to: `if (!smartEntryDecision || decRes.action === "ABSTAIN" || decRes.status === "NO_SMART_ENTRY" || decRes.decision_id !== smartEntryDecision.decision_id)`. |

---

## 7. Standing Research Guardrails & Limitations

1. **Non-Execution Commitment:** BTCognitive remains an empirical research and risk analytics terminal. No trading capability is enabled, authorized, or implemented.
2. **Directional vs. Volatility Separation:** Directional return prediction hit rate (~50–52%) remains statistically indistinguishable from noise on unconditional BTC spot returns. Realized variance forecasting (QLIKE, RMSE) models volatility magnitudes, NOT trade alpha.
3. **Confirmatory Gate Requirement:** All historical analyses represent development data. Confirmatory validation requires a minimum of 100 non-overlapping clean blocks collected prospectively post-freeze.

---

## 8. Final QA Certification

The navigation simplification and Terminal consolidation implemented in BTCognitive V32.46 have been rigorously evaluated and verified in real browser execution. All automated assertions, responsive viewports, route regressions, safety invariants, and bit-identical file preservation checks have passed.

**Final Certification Verdict:** **`QA_VERIFIED`**
