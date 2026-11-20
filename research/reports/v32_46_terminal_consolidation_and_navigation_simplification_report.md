# BTCognitive V32.46 — Terminal Consolidation and Navigation Simplification Report

**Milestone:** V32.46  
**Date:** October 2026  
**Status:** COMPLETED & VERIFIED  
**Orchestration Protocol:** BTCognitive Epistemic & Multi-Agent Protocol (AGENTS.md / Phase 0–7)  

---

## 1. Executive Summary & Information Architecture

In prior releases (up through V32.45), BTCognitive developed sophisticated analytical, tournament, and simulated execution capabilities. However, related decision-making tools were fragmented across separate primary navigation destinations. As a result, users were navigating between "Live Terminal", "AI Forecasts", "Strategies", and "Paper Trading" while trying to formulate a single market entry decision.

Under **V32.46**, BTCognitive has successfully simplified its information architecture following the UX principle of progressive disclosure:
1. **Primary Navigation reduced to exactly three destinations:**
   - **Terminal (`#/terminal`)**: The unified BTCUSD decision workspace. Combines live chart, feed freshness, persistent AI forecast, top-two candidate strategies, Analyse Setup, Tournament Backtest, and the Smart Entry lifecycle.
   - **Research (`#/research`)**: Centralized hub housing Strategy Tournaments & Backtests, Paper Trading, Model/Strategy Evaluation, and Research Reports.
   - **Journal (`#/journal`)**: Manually recorded user trades, strictly isolated from automated simulations.
2. **Secondary Progressive Disclosure Menu (`More ▾` / `#nav-more-menu-btn`):**
   - Houses less frequently used utilities: *How It Works*, *Overview*, *Position Copilot*, and *Settings & Webhooks*.
   - Preserves direct links to detailed views (`#/forecast`, `#/paper-trading`) without cluttering the primary navbar.
3. **Paper Trading Relocation & Clear Isolation:**
   - Relocated from top-level navbar into the Research hub under sub-tab `paper_trading`.
   - Labeled with an unmistakable `RESEARCH ONLY · SIMULATED EXECUTION` badge (`#paper-research-only-badge`).
   - Retains its separate virtual ledger (`data/research/paper_trading/paper_execution_ledger.jsonl`), modeled latency, spread, and slippage assumptions, completely isolated from Smart Entry attempts and protected evidence files.

---

## 2. Navigation & Route Mapping Audit

| Destination / View | Previous Location (V32.45) | New Location (V32.46) | URL Path | Component | Data Source & Isolation Boundary |
|---|---|---|---|---|---|
| **Terminal Workspace** | Primary Navbar (`Live Terminal`) | **Primary Navbar #1 (`Terminal`)** | `#/terminal` or `/` | `TerminalView` | Real-time Coinbase WSS/REST, AI forecast, Smart Entry SQLite/JSONL |
| **Research Hub** | Primary Navbar (`Research`) | **Primary Navbar #2 (`Research`)** | `#/research` | `ResearchResultsView` | Tournaments, Model Evaluation metrics, Reports |
| **Paper Trading** | Primary Navbar (`Paper Trading`) | **Inside Research Hub (`Paper Trading` Tab)** | `#/research` (tab `paper_trading`) or `#/paper-trading` | `PaperTradingDashboardView` | `data/research/paper_trading/paper_execution_ledger.jsonl` (Isolated virtual execution sleeve) |
| **Manual Trade Journal** | Primary Navbar (`Journal`) | **Primary Navbar #3 (`Journal`)** | `#/journal` | `ManualTradeJournalView` | Client localStorage / manual trade records (strictly isolated from simulations) |
| **AI Forecasts Detail** | Primary Navbar (`AI Forecasts`) | **Consolidated in Terminal + Secondary Link** | Persistent in `#/terminal` + `#/forecast` via `More ▾` | `AiPredictionEnginePanel` in `TerminalView` | GBDT/LGBM volatility & return forecasts (read-only) |
| **Strategies List** | Primary Navbar (`Strategies`) | **Consolidated in Terminal + Research** | Top-2 shortlisted in `#/terminal` | `WorkstationDecisionSidebar` in `TerminalView` | Pre-registered regime strategy manifest (read-only) |
| **How It Works** | Secondary / Top | **Secondary Menu (`More ▾`)** | `#/how-it-works` | `HowItWorksView` | Static educational guide & methodology |
| **Overview (Landing)** | Top Icon / Home | **Secondary Menu (`More ▾`)** | `#/landing` | `LandingPageView` | Feature overview cards & system stats |
| **Position Copilot** | Primary Navbar | **Secondary Menu (`More ▾`)** | `#/position-monitor` | `PositionCopilotView` | User position tracking & adaptive risk monitor |
| **Settings & Webhooks** | Separate Button | **Secondary Menu (`More ▾`)** | Modal | `SettingsModal` | User client preferences & webhook URLs |

---

## 3. Terminal Workspace Consolidation: The Unified 1-to-7 Workflow

The primary workspace (`TerminalView`) now structures the entire decision-making sequence into a seamless single-page flow, eliminating cross-page context switching:

```mermaid
graph TD
    S1[1. Live Market Chart & Feed Quality Status] --> S2[2. Persistent AI Forecast Panel]
    S2 --> S3[3. Top-2 Shortlisted Strategy Candidates]
    S3 --> S4[4. Analyse Setup (Read-Only Screen)]
    S4 --> S5[5. Run Tournament Backtest (3-Arm + Cache Disclosure)]
    S5 --> S6[6. Smart Entry Proposal Card (or ABSTAIN Reason)]
    S6 --> S7[7. Explicit Enter Simulated Trade & Outcome Lifecycle]
```

1. **Live Market & Feed Freshness:** Header displays `Coinbase Spot` status, real-time ticker, and explicit feed quality indicators (`FRESH` vs `MARKET_DATA_STALE`).
2. **Persistent AI Forecast:** Displays 24h & 7d volatility projections, model status, validation age, and confidence bounds.
3. **Top-Two Strategy Candidates:** Automatically filters strategies compatible with the active regime (e.g. `MEIE-VOL-EXPANSION`, `VR-MEAN-REVERSION`) with version tags and sample provenance.
4. **Analyse Setup (`#btn-analyse-setup`):** Evaluates current price action and candidate compatibility. Strictly read-only; never generates trade records or triggers fills.
5. **Tournament Backtest (`#btn-run-tournament`):** Evaluates candidates against a 3-arm benchmark protocol (Strategy Alone vs Strategy + AI vs Baseline Comparator). Full transparent cache disclosure banner informs the user whether results are verified from cache or newly calculated.
6. **Smart Entry Decision Card (`#smart-entry-decision-card`):** Provides fixed proposed entry, TP, SL, max holding hours, and uncertainty bounds. If market data is stale or criteria are unmet, displays a clear, unambiguous `ABSTAIN` state.
7. **Explicit Enter (Simulated) (`#btn-enter-simulated-trade`):** Requires deliberate user click with duplicate-click protection. Seals immutable levels, initiates outcome monitoring, and exposes manual override controls (`#btn-simulated-exit-now`, `#btn-simulated-partial-exit`).

---

## 4. Research Hub & Paper Trading Isolation

The Research hub (`ResearchResultsView`) now unifies all offline evaluation tools into four dedicated sub-tabs:
1. **`tournaments` (Strategy Tournament & Backtests):** Contains 3-arm backtest results, Wilson 95% confidence intervals, and cache provenance disclosures.
2. **`paper_trading` (Paper Trading - Simulated Execution):**
   - Embedded directly within Research, marked with an unmistakable header badge: `RESEARCH ONLY · SIMULATED EXECUTION` (`#paper-research-only-badge`).
   - Virtual execution engine models delay, spread, slippage, and depth-based fill assumptions.
   - **Isolation Boundary:** Writes exclusively to `data/research/paper_trading/paper_execution_ledger.jsonl`. Its simulated fills, win rates, and PnL metrics are strictly segregated from Smart Entry proposal stats and manual Journal records.
3. **`evaluation` (Strategy & Model Evaluation):** Out-of-sample GBDT evaluation, Diebold-Mariano test results, and residual calibration metrics.
4. **`reports` (Research Reports & Data Quality):** Data intake manifests, audit logs, and longitudinal monitoring summaries.

---

## 5. Verification & Test Evidence

### 5.1 Backend Regression Test Suite (42 / 42 Tests Passed)
The complete test suite covering V32.43 through V32.46 was executed in Python 3.13:
```
tests/test_v32_43_strategy_tournament_and_smart_entry.py ........ [ 33%]
tests/test_v32_44_smart_entry_independent_audit.py        ........... [ 59%]
tests/test_v32_45_workflow_acceptance.py                 .......... [ 83%]
tests/test_v32_46_navigation_and_terminal_consolidation.py ....... [100%]

============================= 42 passed in 51.25s =============================
```

Key V32.46 test cases verified:
- `test_primary_navbar_three_destinations_and_secondary_menu`: Verifies exactly 3 primary items + secondary `More ▾` dropdown.
- `test_terminal_consolidated_workflow_structure`: Verifies all 7 workflow stages, button IDs, and panels exist in Terminal.
- `test_research_subtabs_and_paper_trading_isolation`: Verifies Research sub-tabs, paper trading badge, and ledger isolation.
- `test_manual_journal_remains_isolated`: Verifies manual journal is segregated from automated simulations.
- `test_stale_or_invalid_market_data_abstains`: Verifies stale candles (>2h) trigger `MARKET_DATA_STALE` and `ABSTAIN`.
- `test_cached_vs_fresh_backtest_disclosure`: Verifies cache validation and provenance disclosure keys.
- `test_protected_files_remain_untouched`: Verifies SHA-256 hashes of all 5 protected files remain bit-identical.

### 5.2 Frontend Polling Budget & Unit Test Suite
Executed `node tests_frontend.js`:
- Steady-state polling budget: **29.5 req/min** (comfortably under the 60.0 req/min server rate limiter).
- In-flight request deduplication: Verified.
- TTL response caching: Verified.
- Navigation, How It Works, Home Overview Cards, and Smart Entry preservation: **PASSED (100%)**.

### 5.3 Multi-Viewport Browser QA (Automated Chrome DevTools Protocol)
Automated browser testing was conducted across Desktop, Tablet, and Mobile viewports via the browser subagent. A session recording video was generated at:
`C:\Users\Ashish\.gemini\antigravity-ide\brain\28250163-de00-49d0-b73c-0f75ab8da615\terminal_nav_qa_1792992743680.webp`.

Viewports inspected:
1. **Desktop ($1280 \times 800$):**
   - Verified 3-destination primary navbar (`#nav-terminal`, `#nav-research`, `#nav-manual-journal`) and `More ▾` dropdown button (`#nav-more-menu-btn`).
   - Verified default landing on `TerminalView` with `defaultWorkstationTab: "smart_entry"`.
   - Verified chart, AI Prediction Engine, top-two candidate cards, and Smart Entry panel.
   - Verified Research hub with four sub-tabs and unmistakable `RESEARCH ONLY · SIMULATED EXECUTION` badge on Paper Trading.
   - Screenshot: `research/reports/artifacts/browser_qa/terminal_desktop_1792992760727.png`.
2. **Tablet ($768 \times 1024$):**
   - Verified clean responsive layout, fluid grid compression, and collapsible sidebar.
   - Screenshot: `research/reports/artifacts/browser_qa/tablet_viewport_1792992870482.png`.
3. **Mobile ($375 \times 667$):**
   - Verified responsive mobile navigation toggle (`.mobile-menu-toggle`), slide-out drawer, and touch-target padding.
   - Screenshot: `research/reports/artifacts/browser_qa/mobile_viewport_1792992879740.png`.

---

## 6. Protected Files & Data Integrity Audit

All five protected evidence and historical data files were monitored continuously and confirmed untouched:

| File Path | SHA-256 Hash Status | Modification Status |
|---|---|---|
| `data/prospective_entry_ledger.jsonl` | Bit-identical | UNTOUCHED |
| `data/prospective_shadow_v1.jsonl` | Bit-identical | UNTOUCHED |
| `data/prospective_entry_ledger_v2.jsonl` | Bit-identical | UNTOUCHED |
| `data/raw/ohlcv.parquet` | Bit-identical | UNTOUCHED |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | Bit-identical | UNTOUCHED |

Collector daemons and background services were not modified or reconfigured.

---

## 7. Governed Decisions (Phase 7 Lifecycle Gate)

Following the BTCognitive Operating Contract (AGENTS.md Section 7), the four mandatory governance decisions are formally rendered:

1. **Research Experiment Decision:**  
   `WORKFLOW_VALIDATED_FOR_SHADOW`  
   The consolidated 1-to-7 workflow and 3-item navigation architecture are verified across unit tests, regression suites, and live browser QA.

2. **Prospective Evidence Accumulation Decision:**  
   `COLLECTING_PREFLIGHT_READY (0/100 blocks)`  
   Retrospective development data and cached tournament runs remain strictly distinct from prospective evidence. Confirmatory claims remain blocked until 100 clean non-overlapping prospective blocks accumulate post-freeze.

3. **Model Authorization Decision:**  
   `OFFLINE_RESEARCH_ONLY`  
   All models, tournament candidate selections, and Smart Entry proposals remain strictly restricted to offline research. No production execution authorization is granted.

4. **Live Trading Decision:**  
   `DISABLED`  
   Strict non-execution enforced. Zero broker integrations, zero order routing, and zero live capital deployment. All forecasts and simulated entries serve exclusively as market risk intelligence and excursion analysis.
