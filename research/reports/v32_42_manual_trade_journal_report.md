# BTCognitive V32.42 — Manual Trade Journal and AI Forecast Evaluation Report

**Document ID:** `BTC-REP-V32.42-MANUAL-JOURNAL-EVAL`  
**Execution Date:** October 25, 2026  
**Governance Posture:** `OFFLINE_RESEARCH_ONLY`  
**Economic Posture:** `NO_GO_NO_VALIDATED_EDGE`  
**Live Execution Authorization:** `PERMANENTLY_DISABLED`  
**Author:** BTCognitive Quantitative Research & Engineering Team  

---

## 1. Executive Summary & Epistemic Boundaries

### Purpose
The objective of BTCognitive V32.42 is to implement an observational manual trade journal and AI forecast evaluation system. The purpose is to empirically measure whether BTCognitive's existing AI forecasts (directional GBDT ensemble, HAR-RS-DOW volatility model, market regime classifier, and quantitative strategy signals) provide practical information to traders who execute their own positions on external exchanges.

### Strict Non-Execution Invariants
1. **Zero Broker Execution:** No exchange credentials, broker API keys, FIX sessions, order placement, or automated execution are implemented.
2. **Observational Manual Entry:** Users execute trades on external exchanges (e.g., Coinbase, Kraken, Binance) and manually record entry and exit parameters in BTCognitive.
3. **Zero Automated Position Closure:** The system never infers an exit from live market feeds or closes an external position automatically.
4. **Target & Scope Separation:** Volatility and directional predictions serve as observational market risk intelligence; they never authorize capital deployment.

---

## 2. System Architecture & Workflows

### A. Manual Trade Entry Workflow ("I Entered a Trade")
When an operator executes a trade on an external venue, they click the **"I Entered a Trade"** action button available on:
- Primary Navigation (`nav-manual-journal`)
- Home Overview Card 6 (`home-btn-trade-journal`)
- Hero Section CTA (`btn-hero-entered-trade`)
- Trade Journal Header (`btn-i-entered-trade`)

The entry form captures:
- **Instrument:** Defaults to `BTC-USD`.
- **Direction:** `LONG` or `SHORT`.
- **Entry Price:** Validated positive, finite float.
- **Entry Timestamp:** ISO UTC timestamp.
- **Quantity:** Optional BTC size (if omitted, recorded as `PRICE_DIRECTION_ONLY`).
- **Entry Fee:** Optional USD fee (if omitted, labeled `GROSS_PNL_ONLY` / `NET_PNL_INCOMPLETE`).
- **Market Type:** `SPOT`, `PERPETUAL`, or `FUTURES`.
- **Leverage & Contract Multiplier:** For derivatives risk evaluation.
- **Notes:** Optional thesis or entry rationale.

#### Immutable Entry Forecast Snapshot
Upon confirmation, the engine synchronously captures and seals the latest point-in-time state of the BTCognitive AI model:
- `snapshot_timestamp_utc`: Exact moment of registration.
- `model_id`: Directional GBDT ensemble (`directional-gbm-ensemble-v1.0`).
- `forecast_status`: `VALID`, `STALE`, or `UNAVAILABLE`.
- `predicted_direction`: `UP`, `DOWN`, or `UNAVAILABLE`.
- `horizons`: Directional probabilities $P(\text{UP})$ and $P(\text{DOWN})$ across 1h, 4h, and 24h horizons.
- `regime_classification`: Active market regime.
- `strategy_signal`: Deterministic strategy candidate state.
- `immutable_sha256`: Canonical SHA-256 digest computed across the normalized snapshot dictionary. The snapshot cannot be retroactively modified or backfilled with subsequent observations.

### B. Manual Trade Exit Workflow ("I Exited")
For each open manual record in the **Open Records** section, an **"I Exited"** action button allows recording full or partial exits:
- **Exit Price:** Validated positive, finite float.
- **Exit Timestamp:** ISO UTC timestamp.
- **Quantity Closed:** Partial exit deduction or full closure.
- **Exit Fee:** Optional USD fee.
- **Notes:** Exit rationale or post-trade notes.

When the full quantity has been closed, the trade status transitions to `CLOSED`, final volume-weighted average exit price (VWAP) is determined, and final P&L status is resolved.

### C. Auditable Corrections
Historical trade records are never silently altered. If an operator needs to correct an entry fee, notes, leverage, or multiplier, an **Auditable Adjustment** is recorded:
- Records `adjustment_id`, `timestamp_utc`, `field_name`, `old_value`, `new_value`, and `reason`.
- Appended directly to the persistent ledger.

---

## 3. Profit and Loss Calculation Standards

Calculations strictly follow point-in-time financial mathematics:

### Spot Formulations
$$\text{Gross P\&L}_{\text{Long}} = (P_{\text{exit}} - P_{\text{entry}}) \times Q$$
$$\text{Gross P\&L}_{\text{Short}} = (P_{\text{entry}} - P_{\text{exit}}) \times Q$$
$$\text{Net P\&L} = \text{Gross P\&L} - \text{Fee}_{\text{entry}} - \text{Fee}_{\text{exit}} - \text{Explicit Costs}$$

### Derivative Formulations
For contracts with multiplier $M$:
$$\text{Gross P\&L} = (P_{\text{exit}} - P_{\text{entry}}) \times Q \times M \quad (\text{Long})$$
$$\text{Gross P\&L} = (P_{\text{entry}} - P_{\text{exit}}) \times Q \times M \quad (\text{Short})$$
If contract parameters are missing or invalid (e.g. $M \le 0$), the engine does not default to spot; it explicitly marks the calculation `CALCULATION_INCOMPLETE_MISSING_CONTRACT_SPECS`.

### Fee Transparency
- If fees are unknown or omitted, fees are never assumed to be zero.
- `net_pnl_usd` is set to `None`, and `pnl_status` is explicitly set to `GROSS_PNL_ONLY` or `NET_PNL_INCOMPLETE`.
- `NET_PNL_COMPLETE` is granted only when all relevant fees are explicitly recorded.

---

## 4. Bifurcated AI Performance Evaluation

The evaluation engine bifurcates results into two distinct dimensions:

### A. User Trade Performance
Measures how the user's executed trades performed financially:
- Total Completed Trades ($N$).
- Winning, Losing, and Breakeven counts.
- Win Rate ($W / N$).
- Total Gross P&L and Total Net P&L.
- Average Win ($), Average Loss ($), Average Net ($).
- Maximum Observed Cumulative Drawdown ($).
- Disaggregation by Direction (`LONG` vs `SHORT`), Market Regime, and Strategy tag.

### B. AI Forecast Performance
Measures whether the AI's predictions were objectively accurate, completely independent of whether the user made money:
- **Snapshot Validity:** Number of trades with valid vs stale/unavailable AI snapshots.
- **Directional Agreement:** Fraction of trades where user trade direction matched the model's predicted direction.
- **Model Accuracy Rate:** On eligible trades with valid forecasts, what fraction saw price move in the model's predicted direction.
- **Contingency Matrix (User Outcome vs Model Correctness):**
  - **User WIN · Model CORRECT:** User followed AI recommendation and profited.
  - **User WIN · Model INCORRECT:** User traded against the AI or model missed the market turn, yet user profited.
  - **User LOSS · Model CORRECT:** User traded *against* the AI's forecast and suffered an adverse move.
  - **User LOSS · Model INCORRECT:** Both user and model were wrong.
- **Calibration Metric:** Brier score evaluated when eligible sample size $N \ge 10$.

### Sample Size Caveat & Disclaimer
The UI renders a permanent prominent warning banner:
> **`⚠ INSUFFICIENT EVIDENCE · USER-SELECTED SAMPLE WARNING`**  
> *This evaluation is based on manually recorded trades. A small or non-random sample of trades cannot establish statistical significance, predictive edge, or trading profitability across changing market conditions.*

---

## 5. Automated Verification & Test Evidence

### A. Python Pytest Unit & Integration Suite
File: [`tests/test_v32_42_manual_trade_journal_and_eval.py`](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_v32_42_manual_trade_journal_and_eval.py)

| Test Case | Objective | Result |
| :--- | :--- | :--- |
| `test_safety_non_execution_and_journal_status` | Verify non-execution boundaries and status contract | `PASSED` |
| `test_long_and_short_pnl_with_fees` | Spot Long/Short gross and net P&L with explicit fees | `PASSED` |
| `test_gross_only_label_when_fees_unknown` | Enforce `GROSS_PNL_ONLY` when fees are omitted | `PASSED` |
| `test_derivative_calculations_and_missing_contract_specs` | Contract multiplier and missing spec rejection | `PASSED` |
| `test_partial_and_full_exits_reconciliation` | Partial exit deductions and volume-weighted close | `PASSED` |
| `test_durable_persistence_and_recovery` | Replay across restarts from append-only ledger | `PASSED` |
| `test_forecast_snapshot_immutability` | SHA-256 seal verification on entry forecast | `PASSED` |
| `test_forecast_direction_vs_user_selected_trade_direction` | Trade against AI evaluated in contingency matrix | `PASSED` |
| `test_api_endpoints_manual_journal_lifecycle` | FastAPI endpoints lifecycle (/enter, /exit, /eval) | `PASSED` |
| `test_protected_files_isolation_assertion` | Bit-identical check on 5 protected repository files | `PASSED` |

**Summary:** 10 passed in 50.07s.

### B. Frontend Verification Suite
Script: `node tests_frontend.js`
- Polling budget: 29.5 req/min (server limit: 60 req/min).
- API client methods verified (`fetchJournalStatus`, `fetchJournalTrades`, `fetchJournalEvaluation`, `recordEnterTrade`, `recordExitTrade`, `recordAdjustTrade`).
- UI markers verified (`nav-manual-journal`, `home-btn-trade-journal`, `btn-hero-entered-trade`, `ManualTradeJournalView`, `journal-warning-banner`, `journal-open-records`, `journal-closed-records`, `journal-ai-evaluation`, `journal-sample-disclaimer`).
- **Result:** `All Frontend Unit Tests Passed Successfully!`

### C. Real Chrome DevTools Protocol (CDP) Multi-Viewport QA
Script: [`engine/run_v32_42_journal_browser_qa.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/run_v32_42_journal_browser_qa.py)  
Execution: Connected to Chrome on port 9222, dynamic test server on loopback.

| Viewport | Dimensions | Elements & Actions Verified | Screenshot Artifact | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Desktop** | 1280x800 | Navbar, Warning Banner, Open/Closed Records, AI Eval, Disclaimer | [`v32_42_manual_journal_desktop.png`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_42_manual_journal_desktop.png) | `PASSED` |
| **Tablet** | 768x1024 | 2-column cards, modal triggers, responsive table | [`v32_42_manual_journal_tablet.png`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_42_manual_journal_tablet.png) | `PASSED` |
| **Mobile** | 375x667 | Single-column cards, responsive table wrapping, touch buttons | [`v32_42_manual_journal_mobile.png`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_42_manual_journal_mobile.png) | `PASSED` |

---

## 6. Repository Integrity & Protected Files Audit

All 5 protected files were verified via SHA-256 checksums to remain 100% bit-identical:

| Protected File Path | Verified SHA-256 Checksum | Integrity Status |
| :--- | :--- | :--- |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | Bit-Identical |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | Bit-Identical |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | Bit-Identical |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | Bit-Identical |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | Bit-Identical |

---

## 7. Changed Files Inventory

1. [`engine/manual_trade_journal.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/manual_trade_journal.py) — Core data structures, P&L mathematics, immutable forecast snapshot capture with SHA-256 seal, append-only JSONL event store, and bifurcated evaluation engine.
2. [`api/routes_manual_journal.py`](file:///c:/Projects/BTCognitive/BTCognitive/api/routes_manual_journal.py) — REST API endpoints for `/api/journal/trades`, `/enter`, `/{id}/exit`, `/{id}/adjust`, `/evaluation`, and `/status`.
3. [`api/server.py`](file:///c:/Projects/BTCognitive/BTCognitive/api/server.py) — Integrated and mounted `manual_journal_router`.
4. [`web_src/api_client.js`](file:///c:/Projects/BTCognitive/BTCognitive/web_src/api_client.js) — Added manual trade journal API client methods with error handling.
5. [`web_src/manual_trade_journal_view.js`](file:///c:/Projects/BTCognitive/BTCognitive/web_src/manual_trade_journal_view.js) — Standalone React component source.
6. [`web/app.js`](file:///c:/Projects/BTCognitive/BTCognitive/web/app.js) — Added navigation link in Navbar, CTA in HeroSection, Card 6 link in HomeOverview, route handler in App router, and complete `ManualTradeJournalView` component.
7. [`tests/test_v32_42_manual_trade_journal_and_eval.py`](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_v32_42_manual_trade_journal_and_eval.py) — Comprehensive pytest test suite (10 test cases, 100% passing).
8. [`tests_frontend.js`](file:///c:/Projects/BTCognitive/BTCognitive/tests_frontend.js) — Added frontend module verification assertions.
9. [`engine/run_v32_42_journal_browser_qa.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/run_v32_42_journal_browser_qa.py) — Chrome CDP automated browser QA runner.
10. [`research/reports/v32_42_manual_journal_browser_qa_summary.json`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/v32_42_manual_journal_browser_qa_summary.json) — Machine-readable browser QA results.
11. [`research/reports/artifacts/browser_qa/v32_42_manual_journal_desktop.png`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_42_manual_journal_desktop.png) — Desktop viewport screenshot.
12. [`research/reports/artifacts/browser_qa/v32_42_manual_journal_tablet.png`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_42_manual_journal_tablet.png) — Tablet viewport screenshot.
13. [`research/reports/artifacts/browser_qa/v32_42_manual_journal_mobile.png`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/browser_qa/v32_42_manual_journal_mobile.png) — Mobile viewport screenshot.
