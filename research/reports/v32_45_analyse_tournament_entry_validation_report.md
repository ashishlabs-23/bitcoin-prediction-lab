# BTCognitive V32.45 — Analyse, Tournament Backtest and Entry Acceptance Validation Report

**Milestone:** V32.45  
**Audit Date:** October 26, 2026  
**Repository:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Git Commit SHA:** `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Overall Validation Status:** `WORKFLOW_VALIDATED_FOR_SHADOW`  
**Governance State:** `OFFLINE_RESEARCH_ONLY`  
**Live Trading:** `DISABLED`  

---

## Executive Summary & Epistemic Principles

This report documents the rigorous end-to-end validation and hardening of the complete **Smart Entry Lifecycle and Strategy Tournament Workflow** implemented in BTCognitive V32.43 and audited in V32.44.

The primary user workflow under evaluation is:
$$\text{Analyse} \longrightarrow \text{Top-Two Shortlist} \longrightarrow \text{Run Tournament Backtest} \longrightarrow \text{Smart Entry Proposal or ABSTAIN} \longrightarrow \text{Enter (Simulated)} \longrightarrow \text{Monitor} \longrightarrow \text{Outcome Resolution}$$

### Core Epistemic Safeguards Maintained
1. **Strict Non-Execution:** BTCognitive is a manual-confirmation, zero-money research simulator. No broker API keys, live order routing, exchange account balances, or real capital are integrated or permitted.
2. **Directional Accuracy Boundary:** High directional probability from GBDT ($P(\text{UP}) > 0.50$) is an indicator of conditional return sign, **never** to be conflated with unconditional trade success or profitability. Passing a 7/10 screening rule is an initial gating hurdle, **not proof of a future 70% success probability**.
3. **Point-in-Time Causality:** All regime classifications and candidate shortlist geometries strictly utilize closed hourly candles ($t \le t_{\text{decision}}$) with $\ge 168\text{h}$ of indicator warm-up. No forward lookahead or intrabar leakage is permitted.
4. **Historical vs. Prospective Separation:** Screening hit rates derived from canonical walk-forward backtests are explicitly labeled `HISTORICAL_WALKFORWARD_SCREENING` and never pooled with prospective simulated outcomes.
5. **No Synthetic Fabrication:** When market data is stale or missing, the system emits `MARKET_DATA_STALE` or `ABSTAIN`. No synthetic Level-2 metrics or fabricated order book features are generated.

---

## 1. Inspect Actual Button Wiring & Click Trace

We performed an exhaustive trace of all interactive buttons in the UI through `web_src/smart_entry_simulator_view.js`, `web/app.js`, `web_src/api_client.js`, and the backend route handlers in `api/routes_tournament.py`.

```mermaid
sequenceDiagram
    autonumber
    actor Operator
    participant UI as React UI (SmartEntryView)
    participant Client as API Client (api_client.js)
    participant Backend as FastAPI (routes_tournament.py)
    participant Engine as Tournament & Simulator Engine

    Operator->>UI: Clicks "Analyse Setup" (#btn-analyse-setup)
    UI->>Client: analyseMarket({ live_price })
    Client->>Backend: POST /api/tournament/analyse
    Backend->>Engine: analyse_current_market(df_1h, live_price)
    Engine-->>Backend: Analysis payload (Regime, Shortlist <= 2, 7/10 screen)
    Backend-->>Client: 200 OK (NO trade created)
    Client-->>UI: Render Candidate Cards

    Operator->>UI: Clicks "Run Tournament Backtest" (#btn-run-tournament)
    UI->>Client: runTournament({ shortlisted_candidates, current_regime })
    Client->>Backend: POST /api/tournament/run
    Backend->>Engine: run_strategy_tournament_backtest(...)
    Engine-->>Backend: 3-Arm Tournament Comparison & Winner/ABSTAIN
    Backend-->>Client: 200 OK (NO trade created)
    Client-->>UI: Render 3-Arm Table & Winner Badge

    UI->>Client: fetchSmartEntryLatest()
    Client->>Backend: GET /api/tournament/smart-entry/latest
    Backend-->>UI: Formulated Smart Entry Decision (SMART_ENTRY_AVAILABLE or ABSTAIN)

    alt Status is SMART_ENTRY_AVAILABLE
        Operator->>UI: Explicitly clicks "Enter (Simulated)" (#btn-enter-simulated-trade)
        UI->>Client: enterSimulatedTrade({ decision_payload, entry_price })
        Client->>Backend: POST /api/tournament/smart-entry/enter
        Backend->>Engine: enter_simulated_trade(...)
        Note over Engine: Freeze Entry, TP, SL, Anomaly Rules, SHA-256 Seal
        Engine-->>Backend: SimulatedTradeAttempt (Status: ACTIVE)
        Backend-->>Client: 200 OK (Simulated Attempt Created)
        Client-->>UI: Render Active Trade Card with Locked Levels
    else Status is ABSTAIN
        Note over UI: Enter Button Disabled; ABSTAIN reason displayed
    end

    alt Operator Clicks "Partial Exit"
        Operator->>UI: Clicks "Partial Exit 50%"
        UI->>Client: partialExitSimulatedAttempt(attempt_id, { exit_price, ratio: 0.5 })
        Client->>Backend: POST /api/tournament/smart-entry/attempts/{id}/partial-exit
        Backend->>Engine: user_partial_exit(attempt_id, exit_price, ratio=0.5)
        Engine-->>UI: Remaining ratio updated to 0.5 (Status: PARTIAL_EXIT)
    else Operator Clicks "Exit Now"
        Operator->>UI: Clicks "Exit Now"
        UI->>Client: exitSimulatedAttempt(attempt_id, { exit_price })
        Client->>Backend: POST /api/tournament/smart-entry/attempts/{id}/exit
        Backend->>Engine: user_exit_now(attempt_id, exit_price)
        Engine-->>UI: Status transitioned to USER_EXITED_EARLY
    end
```

### Trace Invariant Verification
- **Analyse Action:** Executed via `POST /api/tournament/analyse`. Invariant verified: simulator ledger length is completely unchanged ($N=0$).
- **Tournament Backtest Action:** Executed via `POST /api/tournament/run`. Invariant verified: simulator ledger length is completely unchanged ($N=0$).
- **Enter Action:** Executed via `POST /api/tournament/smart-entry/enter`. Invariant verified: strictly requires `status == "SMART_ENTRY_AVAILABLE"`. Validates entry price, freezes absolute TP/SL levels, and appends exactly 1 immutable attempt.
- **Exit Actions:** Executed via dedicated endpoints. Verified: transitions attempt to `USER_EXITED_EARLY` or records `PARTIAL_EXIT` with updated remaining ratio.

---

## 2. Analyse: Current Context, Top-Two Shortlist & Stale Data Rejection

### Causal Point-in-Time Data Handling
- Indicator warm-up requires $\ge 168$ closed 1h candles.
- If fewer than 168 bars are supplied, `MarketRegimeClassifier.classify` returns `UNKNOWN_OR_INVALID` with `is_valid: false`.
- Indicators computed strictly from closed bars:
  - 20-bar, 50-bar, and 200-bar Exponential Moving Averages (EMA)
  - 14-period Average Directional Index (ADX)
  - 14-period Average True Range (ATR) and 50-bar baseline ATR
  - 20-period Bollinger Bandwidth (BBW)

### Data Freshness & Candle Gap Detection
We introduced `check_data_freshness_and_gaps`:
- Evaluates the timestamp of the latest closed candle against local UTC time.
- Freshness threshold is strictly set to $2.0\text{ hours}$ (7200 seconds).
- Candle gap tolerance is $3660\text{ seconds}$ (1h + 60s network latency).
- If `enforce_freshness` is requested and observed data age $> 7200\text{s}$, the pipeline returns `status: "ABSTAIN"`, `freshness_status: "MARKET_DATA_STALE"`, and refuses to formulate an active live entry.

### Top-Two Candidate Specification Schema
Each candidate in `shortlisted_candidates` exposes the required contract:
| Field | Value / Type | Purpose |
| :--- | :--- | :--- |
| `candidate_id` / `strategy_id` | `TSMOM_DONCHIAN_24H_168H` | Immutable strategy identifier |
| `version` | `1.0.0` | Semantic version string |
| `intended_regime` | `["TRENDING_BULLISH", "VOLATILITY_EXPANSION"]` | Regime compatibility filter |
| `latest_10_eligible_outcomes` | `{"tp_hits": 7, "sl_hits": 2, "anomaly_exits": 1, "timeouts": 0}` | Exact breakdown of 10 screen attempts |
| `success_count` | `7` | Exact numerator of TP hits |
| `confidence_interval` | `[0.393, 0.891]` | Wilson 95% binomial confidence interval |
| `sample_provenance` | `HISTORICAL_WALKFORWARD_SCREENING` | Distinct from prospective data |
| `qualification_state` | `SCREEN_PASSED` / `SCREEN_FAILED` | Explicit qualification status |
| `proposed_geometry` | Entry, Fixed TP, Fixed SL, Reward/Risk | Pre-calculated geometry |

---

## 3. Tournament Backtest Action with Sequential Candidate Protocol

In V32.45, we implemented and validated the **Sequential Candidate Tournament Protocol**:
1. When the operator runs Tournament Backtest, the highest-ranked shortlisted candidate (**Candidate 1**) is evaluated across three arms:
   - **Arm 1 (Strategy Alone):** Unfiltered strategy signals.
   - **Arm 2 (Strategy + AI Filter):** Strategy signals filtered by GBDT $P(\text{UP}) > 0.50$ and HAR-RS-DOW volatility risk controls.
   - **Arm 3 (Baseline Reference):** Matched random entry and Buy & Hold comparators.
2. Candidate 1 is tested against three predeclared qualification gates:
   - **Gate 1:** Preliminary screen passed (`screen_7_of_10_passed == True`).
   - **Gate 2:** Positive AI lift ($\text{Arm 2 Hit Rate} > \text{Arm 1 Hit Rate}$).
   - **Gate 3:** Strictly outperforms baseline ($\text{Arm 2 Hit Rate} > \text{Arm 3 Hit Rate}$).
3. **Sequential Decision Tree:**
   - If Candidate 1 passes all 3 gates: Candidate 1 is declared `QUALIFIED_PRIMARY_WINNER`. Candidate 2 is marked `UNTESTED_FALLBACK_NOT_NEEDED`.
   - If Candidate 1 fails ANY gate: Candidate 1 failure reasons are recorded. **Candidate 2** is evaluated once with the identical 3-arm protocol.
   - If Candidate 2 passes all 3 gates: Candidate 2 is declared `QUALIFIED_FALLBACK_WINNER`.
   - If Candidate 2 also fails: The tournament concludes with `final_verdict: "ABSTAIN"`, `tournament_winner: null`, and full failure diagnostics.

### Provenance and Cache Disclosure
Every tournament execution returns:
- `protocol_version`: `"WALK_FORWARD_CAUSAL_SPLIT_v1"`
- `protocol_hash`: `"a4d3ec17b8f32dae"`
- `dataset_hash`: `"e93f3810f3db5e95"`
- `date_window`: `{"start_utc": "2024-01-01T00:00:00Z", "end_utc": "2026-10-24T08:00:00Z"}`
- `execution_source`: `"CACHED_WALK_FORWARD_EVALUATION"`
- `cache_validation`: `{"hashes_matched": true, "source_label": "Verified cached walk-forward evaluation", "newly_executed": false}`

---

## 4. Entry Eligibility, Level Immutability & Server-Side Idempotency

### Server-Side Gating
- `POST /api/tournament/smart-entry/enter` verifies that `status == "SMART_ENTRY_AVAILABLE"`. Payloads with `ABSTAIN`, `NO_SMART_ENTRY`, or `MARKET_DATA_STALE` are rejected with HTTP 400.
- Reference price is validated: $P_{\text{ref}} > 0$, non-null, and non-NaN.
- Long geometry is strictly validated: $\text{SL} < P_{\text{entry}} < \text{TP}$.

### Level Immutability & Snapshot Seal
- Upon simulated entry, the reference entry price, absolute TP price, absolute SL price, anomaly exit rules, and maximum holding duration ($T_{\text{max}} = 24\text{h}$ or $48\text{h}$) are frozen permanently.
- The AI forecast state is captured, serialized with sorted keys, and sealed with an immutable SHA-256 hash (`immutable_sha256`).
- Subsequent market price updates or directional forecast flips cannot modify frozen TP/SL levels.

### Server-Side Idempotency and Restart Recovery
- Duplicate prevention is enforced server-side in `SmartEntrySimulator.enter_simulated_trade`:
  - Rapid double-clicks passing the same `idempotency_key` return the existing active attempt idempotently.
  - Retries with the same active `tournament_id` and strategy return the existing active attempt.
- Persisted to append-only JSONL ledger (`data/smart_entry/smart_entry_attempts.jsonl`).
- Verified restart survival: instantiating a fresh simulator reloads all active attempts, frozen levels, and SHA-256 seals intact.

---

## 5. Correct Outcome Lifecycle Evaluation

We tested every terminal outcome state in `test_complete_outcome_lifecycle_all_statuses`:
1. `SUCCESS_TP_HIT`: Qualifying success (counted in numerator and denominator).
2. `FAILURE_SL_HIT`: Qualifying failure (counted in denominator).
3. `EXITED_ANOMALY`: Qualifying failure (counted in denominator).
4. `TIMEOUT_NO_TP`: Qualifying failure (counted in denominator).
5. `USER_EXITED_EARLY`: Non-qualifying user intervention (excluded from denominator; reported separately).
6. `PARTIAL_EXIT`: Non-qualifying lifecycle event (remainder continues; reported separately).
7. `UNRESOLVED_INTRABAR_ORDER`: Dual-touch intrabar ambiguity without finer resolution (reported separately).
8. `DATA_INVALID`: Quarantined attempts (excluded from denominator; reported separately).

### Metric Formulation & Zero Monetary P&L
$$\text{TP-First Success Rate} = \frac{N(\text{SUCCESS\_TP\_HIT})}{N(\text{SUCCESS\_TP\_HIT}) + N(\text{FAILURE\_SL\_HIT}) + N(\text{EXITED\_ANOMALY}) + N(\text{TIMEOUT\_NO\_TP})}$$

Verified: **Total monetary dollar P&L is 0.0 across all outcomes.** No dollar P&L fields are computed, logged, or exposed in the API.

---

## 6. Test Suite and Real Chrome CDP Browser Verification

### 1. Pytest Unit and Integration Suite
Executed the complete suite of 35 deterministic tests across all three test modules:
```powershell
.\.venv_win\Scripts\pytest.exe -q tests/test_v32_43_strategy_tournament_and_smart_entry.py tests/test_v32_44_smart_entry_independent_audit.py tests/test_v32_45_workflow_acceptance.py
```
**Result:** `35 passed in 15.73s` ($100\%$ pass rate).

### 2. Frontend Module Verification Suite
Executed the frontend test suite:
```powershell
node tests_frontend.js
```
**Result:** All frontend unit tests passed. Steady-state polling budget confirmed at $29.5\text{ req/min}$ (safely within the $60\text{ req/min}$ server rate limit).

### 3. Real Chrome CDP Multi-Viewport Browser QA
Executed automated headless Chrome CDP testing via `engine/run_v32_45_workflow_acceptance_browser_qa.py` across three standard viewport profiles:

| Viewport | Dimensions | Elements Verified | Screenshot Path | Result |
| :--- | :--- | :--- | :--- | :--- |
| **Desktop** | $1280 \times 800$ | SmartEntryView, WarningBanner, ForecastPanel, AnalyseBtn, AnalyseSection, EvalSection | `research/reports/artifacts/browser_qa/v32_45_smart_entry_desktop.png` | **PASS** |
| **Tablet** | $768 \times 1024$ | SmartEntryView, WarningBanner, ForecastPanel, AnalyseBtn, AnalyseSection, EvalSection | `research/reports/artifacts/browser_qa/v32_45_smart_entry_tablet.png` | **PASS** |
| **Mobile** | $375 \times 667$ | SmartEntryView, WarningBanner, ForecastPanel, AnalyseBtn, AnalyseSection, EvalSection | `research/reports/artifacts/browser_qa/v32_45_smart_entry_mobile.png` | **PASS** |

Summary persisted to `research/reports/v32_45_workflow_acceptance_browser_qa_summary.json`.

---

## 7. Current Runtime Readiness & Bounded Shadow Preflight Procedure

### Current Collector Status (Read-Only Inspection)
Command: `python -m engine.shadow_feed_runner --status`
- **Runner Lock:** `INACTIVE` (no process loop running; zero resource consumption).
- **Latest Closed 1h Candle:** `2026-10-23T12:00:00+00:00`.
- **Raw Parquet Tail:** `2026-10-24 08:00:00+00:00` (~44 hours stale relative to current system time).
- **Prospective Blocks Accumulated:** $0 / 100$ blocks.
- **Feed Freshness Verdict:** The current dashboard feed is **STALE**. As required by V32.45, the system honestly labels this condition as `MARKET_DATA_STALE` and rejects live simulated entries until a genuine live feed is established.
- **Collector Policy Adherence:** No collector was started, stopped, or reconfigured during this milestone.

### Bounded Shadow Test Preflight Procedure
When an operator authorizes the subsequent prospective shadow test, the following strictly bounded protocol must be followed:

```
[OPERATOR PREFLIGHT CHECKLIST]
1. Environment Authorization:
   - Confirm branch: main at commit 25d483f4c3646661b57311de9d0b53d2be881adb
   - Confirm OFFLINE_RESEARCH_ONLY governance is locked.
   - Confirm live trading execution remains DISABLED.
2. Market Feed Freshness:
   - Verify Coinbase public REST feed reachability for BTC-USD 1h closed bars.
   - Check clock synchronization: local UTC clock delta < 1000ms.
   - Backfill closed bars from 2026-10-24 08:00:00 to current timestamp.
   - Verify indicator warm-up: consecutive non-null bars >= 168.
3. Telemetry & Ledger Initialization:
   - Ensure data/prospective_shadow_v1.jsonl is ready for append-only logging.
   - Verify write permissions on data/smart_entry/smart_entry_attempts.jsonl.
   - Confirm shadow runner lockfile (data/shadow_runner.lock) is cleared.
4. Bounded Execution Limits:
   - Max prospective duration: 100 non-overlapping 24-hour evaluation blocks.
   - Evaluation arms: Arm 1 (Raw Strategy), Arm 2 (Strategy + AI Filter), Arm 3 (Baseline).
   - Abort criteria: If data feed experiences > 2 consecutive hourly candle gaps, pause shadow runner and flag DATA_FEED_DISRUPTED.
5. Operator Start Command:
   - Execute: python -m engine.shadow_feed_runner --once (dry-run cycle)
   - Inspect output: Verify single candidate evaluation and ledger append.
   - Authorize standing loop if dry-run passes.
```

---

## 8. Governed Milestone Decisions

In accordance with Section 7 of the BTCognitive Operating Contract (`AGENTS.md`), the four formal governed decisions are declared:

| Governance Domain | Decision Status | Formal Rationale |
| :--- | :--- | :--- |
| **1. Research Experiment** | `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY` | Workflow mechanics and sequential tournament logic are fully validated, but empirical directional edge remains unproven on prospective BTC data. |
| **2. Prospective Evidence** | `COLLECTING_PREFLIGHT_READY (0/100 blocks)` | The shadow collector is inactive. Prospective evidence collection is ready to begin under the preflight procedure once operator-authorized. |
| **3. Model Authorization** | `OFFLINE_RESEARCH_ONLY` | In-flight models are restricted to offline research and paper-monitoring. Live production authorization is permanently denied. |
| **4. Live Trading** | `DISABLED` | Live order routing, exchange credential integration, and capital deployment are strictly and permanently disabled. |

### Concluding Status
$$\mathbf{WORKFLOW\_VALIDATED\_FOR\_SHADOW}$$

*Implementation success confirms software engineering correctness and governance adherence; it does NOT imply financial market profitability or a validated trading edge.*
