# BTCognitive V21 — Regression & Gate Verification Report

**Date:** October 19, 2026  
**Status:** 100% GREEN (52 / 52 Automated Tests Passing)  
**Product Mode:** `ANALYSIS_ONLY`  
**Live Execution:** `DISABLED`  
**Web Formatter & Budget:** PASSED (0 Errors)  

---

## 1. Executive Summary

This report documents the independent verification of BTCognitive V21 hotfixes and the restored research-condition alert lifecycle. Verification includes:
1. Complete execution of the new V21 regression and gate verification test suite (`tests/test_v21_hotfix_and_alerts.py` — 13/13 passed).
2. Complete execution of existing notifications and release gate suites (`tests/test_notifications.py` and `tests/test_v20_release_and_gates.py` — 39/39 passed).
3. Complete web asset validation via `npm run check` and `npm test` (0 errors, 100% budget passed).
4. Multi-viewport visual verification on live running server (`127.0.0.1:8000`) across Desktop (1440x900) and Mobile (390x844).

---

## 2. Test Execution Summary

### 2.1 Backend Pytest Suites

```
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.0.0, pluggy-1.6.0
rootdir: C:\Projects\BTCognitive\BTCognitive
configfile: pytest.ini
plugins: anyio-4.12.1, asyncio-0.23.6, cov-5.0.0, mock-3.14.0

tests/test_v21_hotfix_and_alerts.py::test_analysis_only_authoritative_health_contract PASSED [  7%]
tests/test_v21_hotfix_and_alerts.py::test_active_paper_position_execution_disabled_contract PASSED [ 15%]
tests/test_v21_hotfix_and_alerts.py::test_trading_mutation_endpoints_rejected_or_nonexistent PASSED [ 23%]
tests/test_v21_hotfix_and_alerts.py::test_trade_markers_api_excludes_non_trades PASSED [ 30%]
tests/test_v21_hotfix_and_alerts.py::test_market_memory_non_directional_was_correct_is_null PASSED [ 38%]
tests/test_v21_hotfix_and_alerts.py::test_future_price_forecast_separation PASSED [ 46%]
tests/test_v21_hotfix_and_alerts.py::test_forecast_multi_horizon_truthfulness PASSED [ 53%]
tests/test_v21_hotfix_and_alerts.py::test_research_conditions_metadata_endpoint PASSED [ 61%]
tests/test_v21_hotfix_and_alerts.py::test_research_alert_trigger_on_fresh_condition PASSED [ 69%]
tests/test_v21_hotfix_and_alerts.py::test_research_alert_cooldown_and_deduplication PASSED [ 76%]
tests/test_v21_hotfix_and_alerts.py::test_stale_market_data_rejects_positive_alert PASSED [ 84%]
tests/test_v21_hotfix_and_alerts.py::test_channel_delivery_reporting_accuracy PASSED [ 92%]
tests/test_v21_hotfix_and_alerts.py::test_read_only_dashboard_no_decision_records_side_effect PASSED [100%]

============================= 13 passed in 61.24s =============================
```

```
tests/test_notifications.py (24 passed)
tests/test_v20_release_and_gates.py (15 passed)
============================= 39 passed in 23.82s =============================
```

**Total Combined Pytest Results:** **52 passed, 0 failed (100% pass rate)**.

### 2.2 Frontend Checks & Budget Tests

```bash
> btcognitive-web@1.0.0 check
> node --check app.js && node --check sw.js
Exit code: 0

> btcognitive-web@1.0.0 test
> node test_size_budget.js
Testing size budgets...
✓ app.js: 12513 lines <= 14000
✓ styles.css: 6516 lines <= 7500
✓ index.html: 846 lines <= 1000
Exit code: 0
```

---

## 3. Detailed Verification Matrix by Defect Area

| Verification Area | Requirement / Gate | Test Method | Result | Evidence Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **Status Reconciliation** | `DIRECTIONAL RECOMMENDATION: DISABLED (ANALYSIS ONLY)` cleanly separated from price forecast and HAR volatility | `/health`, `/api/health`, `/api/readiness`, `/api/forecast/latest`, `/prediction/latest` | **PASS** | `test_analysis_only_authoritative_health_contract`, `test_future_price_forecast_separation` |
| **Execution Label** | `Execution disabled — analysis only` / `DISABLED (ANALYSIS ONLY)`; no trading ticket or actionable entry/TP/SL | `/api/arena/active-paper-position`, DOM audit of `AiPredictionEnginePanel` | **PASS** | `test_active_paper_position_execution_disabled_contract`, `ai_prediction_section_1792409336288.png` |
| **Chart Artifact: NONE · LOSS** | Non-directional scans (`NONE`, `HOLD`, `SKIP`, `NEUTRAL`) must be NA (never losses); render as `ABSTAIN · Routine` | SQLite DB audit (`market_memory.db`), CSV audit, `load_market_memory()`, `LightweightCandleChart` | **PASS** | `test_market_memory_non_directional_was_correct_is_null`, `test_trade_markers_api_excludes_non_trades` |
| **Chart Artifact: AI NOT ESTIMATED (75%)** | When estimate is unvalidated or missing, zero directional arrows rendered; meter shows "No validated directional estimate available" | `LightweightCandleChart` guard audit, `AiPredictionEnginePanel` conviction meter | **PASS** | `dashboard_overview_1792409309175.png`, `ai_prediction_section_1792409336288.png` |
| **Future-Price Forecasting** | 1h, 4h, 24h horizons verified; persistence baseline, experimental candidates, empirical quantiles, and HAR volatility separated | `/api/forecast/latest?horizon=1h|4h|24h`, `/api/terminal/live` | **PASS** | `test_forecast_multi_horizon_truthfulness`, `test_future_price_forecast_separation` |
| **Research Alerts: Condition Evaluation** | Evaluates fresh completed data for volatility compression, strategy triggers, and confirmed regimes | `evaluate_research_conditions` with fresh candles | **PASS** | `test_research_alert_trigger_on_fresh_condition`, `test_research_conditions_metadata_endpoint` |
| **Research Alerts: Cooldown & Dedup** | 15-minute cooldown and hourly price bucket deduplication | `evaluate_research_conditions` sequential evaluation | **PASS** | `test_research_alert_cooldown_and_deduplication` |
| **Research Alerts: Stale Data Rejection** | Candles > 2h old emit typed `NO_ALERT` (`STALE_MARKET_DATA`) | Stale candle fixture (5h age) | **PASS** | `test_stale_market_data_rejects_positive_alert` |
| **Research Alerts: Multi-Channel Dispatch** | Browser, sound, webhook, email, telegram reporting with truthful delivery statuses | `dispatch_alert` with mock channels | **PASS** | `test_channel_delivery_reporting_accuracy` |
| **Dashboard Idempotency** | Read-only dashboard queries do NOT append decision records to market memory | Count rows in `predictions` table before and after querying dashboard endpoints | **PASS** | `test_read_only_dashboard_no_decision_records_side_effect` |

---

## 4. Visual & Multi-Viewport Browser Evidence

Visual inspection was performed by autonomous browser subagent on `127.0.0.1:8000` with full DOM audit:

### 4.1 Desktop (1440x900 Viewport)
1. **Live Header & Status:** Authoritative status displayed: `● Live data available · 24 closed 1h bars · Status: Verified · Mode: Analysis Only · Live Trading: Disabled`.
2. **Chart Overlays:**
   - Evaluated all markers on `LightweightCandleChart`.
   - Confirmed: **Zero instances of `NONE · LOSS`**.
   - Confirmed: **Zero instances of `AI NOT ESTIMATED (75%)`** and zero red downward arrows.
   - Non-directional events render with neutral gray circles as `ABSTAIN · Routine`.
3. **AI Prediction Engine Panel:**
   - Conviction Meter: Displays `No validated directional estimate available` with `0%` bar width.
   - Status: Displays `STATUS: ANALYSIS ONLY` and `EXECUTION: Execution disabled — analysis only`.
   - Analytical Scenario Bounds: Clean read-only analytical reference coordinates:
     - Reference Spot: `$82,536`
     - Upper Scenario Bound: `+$743 (+0.90%)`
     - Lower Scenario Bound: `-$743 (-0.90%)`
     - Excursion Spread: `$1,486`
     - Evaluation Horizon: `60m`
   - Actionable trading ticket (`Entry / TP / SL / R:R / Est. Cost`) is completely absent.
4. **Replay & Counterfactual Lab:**
   - Status badge displays `DIRECTIONAL RECOMMENDATION: DISABLED (ANALYSIS ONLY)`.
   - Trading controls disabled with explanation: `Interactive strategy replay is available for historical exploration. Model authorization is OFFLINE_RESEARCH_ONLY; live execution is disabled.`

### 4.2 Mobile (390x844 Viewport)
1. Single-column responsive layout adapts cleanly with horizontal overflow hidden.
2. All badges, analytical scenario bounds, and status pills wrap gracefully without overlapping.
3. Chart is fully visible and touch-pan enabled with zero misplaced markers.

### 4.3 Captured Artifacts
- Video Session: `v21_live_audit_1792409244342.webp`
- Desktop Overview: `dashboard_overview_1792409309175.png`
- AI Prediction Engine Section: `ai_prediction_section_1792409336288.png`
- Arena View: `arena_view_1792409324218.png`
- Replay Lab Section: `replay_lab_section_1792409347722.png`
- Mobile Responsive View: `mobile_responsive_view_1792409372052.png`
- Mobile Top View: `mobile_top_view_1792409384665.png`

---

## 5. Governed Verification Sign-Off

- **Lead Orchestrator:** Antigravity Research Orchestrator (Multi-Agent Protocol)
- **Governed Verdict:** `V21_HOTFIX_AND_ALERTS_VERIFIED_FAIL_CLOSED`
- **Product Classification:** `ANALYSIS_ONLY`
- **Live Trading Invariant:** `DISABLED`
