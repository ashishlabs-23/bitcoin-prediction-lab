# BTCognitive V32.48 — Integrated Analyse + Backtest + Smart Entry Workflow Report

**Date:** October 26, 2026  
**Status:** QA_VERIFIED / GOVERNANCE_COMPLIANT  
**Scope:** Automated 1-to-7 Analyse & Tournament Orchestration, Truthful Provenance, Locked Simulated Execution & Ongoing AI Anomaly Monitoring  
**Repository Branch:** `main` (Verified clean working tree)  

---

## 1. Executive Summary & Design Decision

BTCognitive V32.48 delivers the integrated **"Analyse Setup" + Tournament Backtest + Smart Entry Workflow** for the BTCUSD Live Terminal. 

### Core Architectural Mandate
- **Elimination of Mandatory Multi-Step Backtesting:** Backtesting is now fully integrated into the single **"Analyse Setup"** button click. The user is never forced into a separate, mandatory second user action to run a backtest.
- **Single-Click Orchestration (Stages 1 through 7):** When the user clicks **Analyse Setup** once, the system validates the market data, computes causal closed-bar indicators, classifies the market regime, evaluates candidate strategies against the 7/10 preliminary screen, executes the 3-arm tournament backtest (with sequential fallback evaluation), forms the final Smart Entry decision, and renders all cards into the Live Terminal in one continuous pass.
- **Strict Execution Boundary:** The Analyse workflow is strictly read-only (`is_read_only = True`, `attempts_created = 0`). The separate **Enter (Simulated)** button remains strictly and uniquely the *only* action that can create a simulated trade attempt.
- **Immutable Protective Geometry & AI Risk Copilot:** Once an attempt is created via Enter (Simulated), take-profit and stop-loss prices are permanently frozen. Real-time background monitoring tracks incoming AI forecasts and data quality, flagging direction reversals and risk spikes ($\ge 1.5\times$ baseline) as operator alerts without ever moving or rewriting the frozen TP/SL boundaries.

---

## 2. Seven-Stage Orchestration Lifecycle

```mermaid
graph TD
    UI[User Clicks 'Analyse Setup'] --> S1[Stage 1: Validate Market Data]
    S1 --> S2[Stage 2: Closed Candle Features & Regime Classification]
    S2 --> S3[Stage 3: Strategy Evaluation & 7/10 Screen]
    S3 --> S4[Stage 4: Candidate Ranking & Shortlisting]
    S4 --> S5[Stage 5: Automatic Tournament Backtest Execution]
    S5 --> S6[Stage 6: Final Smart Entry Decision Formulation]
    S6 --> S7[Stage 7: Render Complete Results in Live Terminal]
    S7 --> DEC{Decision Outcome}
    DEC -->|SMART_ENTRY_AVAILABLE| ENABLE_BTN[Enable 'Enter (Simulated)' Button]
    DEC -->|ABSTAIN / NO_SMART_ENTRY| DISABLE_BTN[Display Clear Rejection Reason]
    ENABLE_BTN -.->|User Explicit Action Only| ENTER[Click 'Enter (Simulated)']
    ENTER --> CREATE_ATTEMPT[Create Simulated Attempt & Freeze TP/SL]
    CREATE_ATTEMPT --> MONITOR[Ongoing AI Direction & Risk Anomaly Monitor]
```

### Stage Details

1. **Stage 1 — Validate Current Market Data:** Validates that candles belong to `BTCUSD` / `BTC-USD`, timeframe is `1h`, timestamps are strictly monotonically increasing without gaps, data age is within acceptable freshness ($< 2.0$ hours), and open/incomplete candles are strictly excluded.
2. **Stage 2 — Closed Candle Feature Computation & Regime Classification:** Computes causal technical indicators (ATR 14, EMA 20, EMA 50, Bollinger Bands 20/2.0, ADX 14) using closed bars only. Captures an immutable `candle_watermark_hash`.
3. **Stage 3 — Strategy Evaluation:** Tests candidate strategies from the `VersionedStrategyRegistry` against regime compatibility and executes the empirical 7/10 preliminary screen across the latest 10 historical closed opportunities.
4. **Stage 4 — Candidate Ranking:** Shortlists Candidate 1 (Primary) and Candidate 2 (Challenger), recording explicit qualification or disqualification reasons.
5. **Stage 5 — Automatic Tournament Backtest Execution:** Evaluates candidates across the predeclared 3-arm protocol:
   - **Arm 1:** Raw Strategy Alone (historical TP-first rate and 95% Wilson CI).
   - **Arm 2:** Strategy + AI Excursion Filter (incremental lift and Wilson CI).
   - **Arm 3:** Passive Buy & Hold 24h Baseline Comparator (48.5% benchmark hurdle).
   - *Sequential Fallback:* Evaluates Candidate 1; if Candidate 1 fails any gate, automatically evaluates Candidate 2; if Candidate 2 also fails (or no candidate available), terminates with an honest `ABSTAIN`.
6. **Stage 6 — Form Final Smart Entry Decision:** Formulates either `SMART_ENTRY_AVAILABLE` with locked TP/SL geometry and Wilson confidence intervals, or `ABSTAIN` / `NO_SMART_ENTRY` with specific actionable feedback.
7. **Stage 7 — Render in Live Terminal:** Updates the Live Terminal DOM in one continuous pass, displaying Candidate details, 3-arm tournament results, truthful provenance disclosures, and enabling the Enter (Simulated) button.

---

## 3. Truthful Provenance & Anti-Duplicate Protection

### Backtest Provenance Disclosure
To prevent conflation between fresh simulated executions and cached analytical metrics, the tournament payload discloses:
- `execution_source`: `"FRESH_BOUNDED_WALK_FORWARD_EXECUTION"` when `force_fresh=True` or newly generated; `"CACHED_WALK_FORWARD_EVALUATION"` when serving verified walk-forward manifests.
- `cache_validation`: `{"cached": True/False, "newly_executed": True/False, "cache_timestamp_utc": "..."}`.
- `methodology_disclosure`: `"Tournament arm performance metrics are loaded from canonical walk-forward backtest manifests."`

### Anti-Duplicate Debouncing Guard
To protect against rapid duplicate clicks on both the backend API and frontend:
- **Frontend Debouncing:** `#btn-analyse-setup` and `#btn-run-tournament` disable immediately upon click, setting opacity to 0.7, changing cursor to `wait`, and showing "Analysing & Backtesting...".
- **Backend Debouncing:** `POST /api/tournament/run` hashes `request_payload + candle_watermark_hash` within a 2.5-second time window. Duplicate requests within this window return the identical cached result with `duplicate_blocked` incremented, preventing redundant compute.

---

## 4. Simulated Execution & AI Anomaly Monitoring

- **Zero-Trade Invariant:** Clicking Analyse executed 1 tournament, made 1 API call, and created **0** simulated trade attempts (`attempts_created: 0`).
- **Explicit Enter Action:** Clicking `Enter (Simulated)` created exactly 1 simulated attempt with locked levels:
  - Reference Entry: `$80,314.23`
  - Frozen Take-Profit: `$82,976.37`
  - Frozen Stop-Loss: `$78,983.16`
- **Direction Reversal Detection:** When an AI forecast flip was injected ($P(\text{DOWN}) = 65\%$), `direction_change_alert` was flagged on the attempt, while TP and SL remained strictly identical to their initial values.
- **Risk Spike Detection ($\ge 1.5\times$ Baseline):** When an annualized forecast risk spike of $85.0\%$ was injected (exceeding $35.0\% \times 1.5 = 52.5\%$), `risk_spike_alert` was flagged immediately, requiring operator review while preserving frozen TP/SL.
- **Degraded Data Quality States:** The simulator rejects silent normalization of malformed feeds, transitioning actively into `DEGRADED_MALFORMED_FORECAST`, `DEGRADED_STALE_PRICE_FEED`, or `DEGRADED_CANDLE_GAPS`.
- **Restart Survival:** Page reload verified that active attempt state and UI action buttons (`#btn-simulated-exit-now`) survive full client restarts without loss of state.

---

## 5. Verification & Test Evidence

### A. Unit & Integration Test Matrix (`tests/test_v32_48_integrated_analyse_and_tournament.py`)
| Test Matrix | Target Capability | Result |
| :--- | :--- | :--- |
| **Matrix A** | Single-click integrated orchestration: Stages 1-7 in one call, 0 attempts created | **PASSED** |
| **Matrix B** | Data integrity: rejects incomplete/open bars, handles stale feeds and gaps with ABSTAIN | **PASSED** |
| **Matrix C** | Sequential qualification: Candidate 1 -> Candidate 2 -> ABSTAIN if both fail | **PASSED** |
| **Matrix D** | Truthful provenance: fresh vs cached distinction, 2.5s anti-duplicate debouncing | **PASSED** |
| **Matrix E** | Simulated entry: immutable TP/SL freeze, direction flip, risk spike $>1.5\times$, first-touch | **PASSED** |
| **Matrix F** | Protected files SHA-256 isolation: zero writes across entire test run | **PASSED** |

### B. Full Pytest Regression Suite
- **Executed:** `pytest tests/test_v32_48* tests/test_v32_47* tests/test_v32_46* tests/test_v32_45* tests/test_v32_44* tests/test_v32_43* -v`
- **Result:** **72 passed in 20.52s (100% pass rate)**.

### C. Automated CDP Real Backend Browser QA Runner (`engine/run_v32_48_real_backend_qa.py`)
Tested against live FastAPI backend on port 8094:
- **Test A (One-Click Integrated Workflow):** Passed. 1 click triggered 1 POST `/api/tournament/analyse` (`auto_tournament: true`), returning DecisionCard, TournamentSection, Candidates, and EnterBtn. Server-side `attempts_created: 0`.
- **Test B (Chart Data Integrity):** Passed. Stale feed injection triggered honest `ABSTAIN` / `NO_SMART_ENTRY`.
- **Test C & D (Tournament & Provenance):** Passed. 3-arm comparison rendered with truthful walk-forward provenance.
- **Test E (Explicit Enter & AI Monitoring):** Passed. Clicked Enter, created attempt `att_db7b32f61fbb`. Injected direction flip & risk spike; TP/SL remained strictly immutable. Exit Now resolved lifecycle.
- **Test F (Responsive Viewports):** Passed across Desktop (1280x800), Tablet (768x1024), and Mobile (375x667).

### D. Captured Browser Artifacts
All screenshots saved in `research/reports/artifacts/browser_qa/v32_48_real_backend/`:
1. `v32_48_test_a_one_click_integrated_workflow.png`
2. `v32_48_test_b_chart_data_integrity.png`
3. `v32_48_test_c_d_tournament_provenance.png`
4. `v32_48_test_e_entry_and_ai_monitoring.png`
5. `v32_48_test_f_desktop_1280.png`
6. `v32_48_test_f_tablet_768.png`
7. `v32_48_test_f_mobile_375.png`

---

## 6. Protected Files Cryptographic Verification

All 5 protected files were cryptographically asserted before and after all QA test runs. Zero bytes were modified:

| Protected File Path | Expected SHA-256 Hash | Post-Test Verified Hash | Status |
| :--- | :--- | :--- | :--- |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **INTACT** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **INTACT** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **INTACT** |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **INTACT** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **INTACT** |

---

## 7. Four Governed Decisions

In accordance with BTCognitive Operating Principles and Governance Protocols:

1. **Research Experiment Decision:** **`PASS`**  
   The integrated 1-to-7 workflow, 3-arm walk-forward backtest, sequential qualification gates, truthful provenance disclosure, and ongoing AI anomaly monitoring meet all engineering and epistemic acceptance criteria.

2. **Prospective Evidence Decision:** **`NOT_STARTED`**  
   All backtest metrics originate from historical walk-forward replay datasets. Zero prospective out-of-sample blocks have been gathered for live validation. Confirmatory claims remain strictly locked until $\ge 100$ clean prospective blocks accumulate.

3. **Model Authorization Decision:** **`OFFLINE_RESEARCH_ONLY`**  
   Directional and volatility forecasting models remain classified strictly for market risk intelligence and excursion analysis. No production promotion is authorized.

4. **Live Trading Decision:** **`DISABLED`**  
   Live execution, broker connectivity, automated order placement, and capital deployment remain permanently disabled. All trading features are restricted to simulated execution and research study.
