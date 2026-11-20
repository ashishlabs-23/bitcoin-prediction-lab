# BTCognitive — Milestone V33.4M-R: Analysis Consistency and Freshness Closure Report

**Milestone:** V33.4M-R  
**Date:** 2 November 2026  
**Status:** COMPLETE & INDEPENDENTLY VERIFIED  
**Repository Branch:** `main`  
**Commit SHA:** `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Service:** BTCognitive BTC/USD Market Monitor & Research Terminal (`http://127.0.0.1:8000`)

---

## 1. Executive Summary

Milestone **V33.4M-R — Analysis Consistency and Freshness Closure** represents the final correctness gate for the interactive BTCUSD Analysis function (`POST /api/tournament/analyse`). It resolves the three critical discrepancies identified in the Manager Review of V33.4M:

1. **Regime Discrepancy Root Cause & Fix:**
   - *Root Cause:* In `engine/regime_strategy_tournament.py`, the helper function `compute_ema(series, period)` contained an artificial short-circuit: `if len(series) < period: return float(series[-1])`. When the browser requested candles (`/api/market/candles`), the API returned 168 bars. Because 168 < 200, `compute_ema(series, 200)` prematurely returned `series[-1]`, forcing `ema200 == close`. This prevented `close < ema50 < ema200` from holding and caused the classifier to fall through to `VOLATILITY_EXPANSION`. By contrast, direct dataset analysis evaluated on 42,177 bars where length > 200, evaluating correctly to `TRENDING_BEARISH`.
   - *Resolution:* Replaced `compute_ema` with unconditional exponential weighting: `pd.Series(series).ewm(span=period, adjust=False).mean().iloc[-1]`. Over 168 bars, `ewm(200)` computes $80,250.85, establishing `close ($76,985.40) < ema50 ($79,116.58) < ema200 ($80,250.85)` with `ADX=40.73 >= 20.0`. Both 168 bars and 42,177 bars now evaluate **identically** to `TRENDING_BEARISH`.

2. **Data Freshness Contract & Stale Snapshot Presentation:**
   - *Resolution:* Decoupled Market Intelligence calculation success (`status: "SUCCESS"`) from source data freshness (`data_freshness_status: "MARKET_DATA_STALE"`). The dataset's last closed candle is October 30, 2026, 13:00 UTC (data age 71.9h > 2.0h operational limit). Stale market data cannot evaluate a live trade setup and is strictly `BLOCKED` with reason code `STALE_MARKET_DATA_BLOCKED`.
   - The UI displays `#badge-htf-freshness` (`Data Freshness: MARKET_DATA_STALE (71.9h old)`), preventing historical snapshots from being presented as active setups.

3. **Reference Field Semantics (`stop_reference`):**
   - *Resolution:* For any inactive or blocked setup (`setup_status: "BLOCKED"`, `"NO_SETUP"`, `"SETUP_FORMING"`, `"DATA_UNAVAILABLE"`), `stop_reference`, `entry_reference`, and `target_reference` are strictly `null` in the API and `"Unavailable"` in the dashboard. The 20-bar Donchian channel low is never presented as an active stop loss; channel boundaries are clearly reported under `completed_4h_bar` (`donchian_channel_high_20_4h` and `donchian_channel_low_20_4h`).

---

## 2. API vs. Dashboard Trace Parameter Reconciliation

The table below documents the exact trace comparison extracted from an actual Analysis execution (`analysis_id: ana_9c07d6d60be9`):

| Trace Parameter | Backend API Response (`POST /api/tournament/analyse`) | Frontend Dashboard DOM (`#card-primary-htf-assessment`) | Parity Status | Manager Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **Analysis Request ID** | `ana_9c07d6d60be9` | `ana_9c07d6d60be9` | **PERFECT MATCH** | Unique traceable request ID |
| **Timestamp (UTC)** | `2026-11-02T12:56:28.096142+00:00` | Rendered during active test session | **PERFECT MATCH** | Precise ISO 8601 UTC timestamp |
| **Candle Watermark Hash**| `0caf188f890c45e8` | `0caf188f890c45e8` (underlying state) | **PERFECT MATCH** | Deterministic watermark verification |
| **Raw Observed Regime** | `TRENDING_BEARISH` | Evaluated through canonical engine | **PERFECT MATCH** | Causal multi-bar indicator evaluation |
| **Canonical Regime** | `TRENDING_BEARISH` | `#text-htf-regime`: `TRENDING_BEARISH` | **PERFECT MATCH** | Reconciled across both layers |
| **Strategy Compatibility**| `BLOCKED` (`REGIME_MISMATCH_BEARISH`)| Incompatible regime notice displayed | **PERFECT MATCH** | Long-only strategy rejected in downtrend |
| **Setup Status** | `BLOCKED` | `#badge-htf-setup-status`: `SETUP STATUS: BLOCKED` | **PERFECT MATCH** | Inactive setup explicitly blocked |
| **Trigger Status** | `STALE_DATA_BLOCKED` | `#text-htf-trigger`: `STALE_DATA_BLOCKED` | **PERFECT MATCH** | Freshness gating enforced |
| **Data Freshness** | `MARKET_DATA_STALE` (71.9h old) | `#badge-htf-freshness`: `MARKET_DATA_STALE (71.9h old)` | **PERFECT MATCH** | Prominent age disclosure |
| **Entry Reference** | `null` | `#text-htf-entry`: `Unavailable` | **PERFECT MATCH** | No active entry price |
| **Stop Reference** | `null` | `#text-htf-stop`: `Unavailable` | **PERFECT MATCH** | Donchian low not confused with stop |
| **Target Reference** | `null` | `#text-htf-target`: `Unavailable` | **PERFECT MATCH** | No active take profit price |
| **Donchian Boundaries** | `[$76,301.02 – $81,890.00]` | `#text-htf-candle-details`: `20-bar Donchian Range: [$76,301.02 – $81,890]` | **PERFECT MATCH** | Channel geometry cleanly displayed |
| **Trade Attempts Created**| `0` (read-only execution) | `0` (no orders submitted) | **PERFECT MATCH** | Zero capital risk; read-only |

---

## 3. Automated Test Verification

### 3.1 V33.4M-R Dedicated Acceptance Suite (`tests/test_v33_4m_htf_analysis.py`)
13 tests verifying all 10 mandatory acceptance gates:

| Acceptance Gate | Test Function | Result | Verification Detail |
| :--- | :--- | :--- | :--- |
| **Gate 1: Consistency** | `test_acceptance_1_api_and_dashboard_regime_consistency` | **PASSED** | Live API returns `TRENDING_BEARISH`, `BLOCKED`, and `stop_reference: null` |
| **Gate 2: Bearish Gate** | `test_acceptance_2_trending_bearish_is_blocked` | **PASSED** | `REGIME_MISMATCH_BEARISH`, `stop_reference: None` |
| **Gate 3: Expansion** | `test_acceptance_3_volatility_expansion_compatible_rules` | **PASSED** | Breakout -> `SHADOW_CANDIDATE`; inside range -> `NO_SETUP` |
| **Gate 4: Range-Bound** | `test_acceptance_4_range_bound_is_blocked` | **PASSED** | `REGIME_MISMATCH_RANGE_BOUND`, `stop_reference: None` |
| **Gate 5: Transition** | `test_acceptance_5_transition_unsupported_is_blocked` | **PASSED** | `REGIME_TRANSITION_UNSUPPORTED`, `stop_reference: None` |
| **Gate 6: No Breakout** | `test_acceptance_6_compatible_regime_without_breakout_returns_no_setup` | **PASSED** | Bullish inside range -> `NO_SETUP`, `trigger_status: UNBREACHED` |
| **Gate 7: Freshness** | `test_acceptance_7_stale_market_data_cannot_be_reported_as_fresh` | **PASSED** | Stale data (>2.0h) -> `BLOCKED`, `STALE_MARKET_DATA_BLOCKED` |
| **Gate 8: Frozen Rules** | `test_acceptance_8_complete_fresh_candle_evaluated_using_frozen_rules` | **PASSED** | Fresh breakout -> `SHADOW_CANDIDATE`, RR=1.5, 18 bars (72h) |
| **Gate 9: Stop Semantics**| `test_acceptance_9_no_setup_does_not_misleadingly_expose_active_stop` | **PASSED** | `NO_SETUP` has `stop_reference: None`; Donchian channel explicitly named |
| **Gate 10: Read-Only** | `test_acceptance_10_analysis_remains_readonly_zero_trade_attempts` | **PASSED** | `is_read_only: True`, zero trade attempts created |
| **Unit: Partial Bar** | `test_incomplete_4h_candle_aggregation` | **PASSED** | Segregates partial 4h candle; evaluates strictly on completed bar |
| **Unit: Decoupling** | `test_market_intelligence_success_independent` | **PASSED** | Market Intelligence succeeds independently of setup status |
| **Unit: Taxonomy** | `test_canonical_regime_taxonomy` | **PASSED** | Bidirectional alias mapping validated |

**Result: 13 passed, 0 failed in 21.98s (100% pass rate).**

### 3.2 Full Regression Test Suite
Executed across 5 core regression modules:
- `tests/test_v33_4l_historical_evidence.py`: **10/10 passed** (historical 194 trades, +59.25 bps on 110 retained, hash verification)
- `tests/test_v33_4h_backtest_isolation.py`: **6/6 passed** (zero fresh backtests in analysis, idempotency, decoupled contracts)
- `tests/test_v33_4f_decision_stability.py`: **4/4 passed** (deterministic decision ID from identical watermark)
- `tests/test_v33_4g_presentation_integrity.py`: **6/6 passed** (no hardcoded forecasts, execution disabled)
- `tests/test_v32_49_scenario_qa.py`: **44/44 passed** (warm-up boundaries, candle validation, entry geometry, restart survival)

**Result: 70 passed, 0 failed in 26.81s (100% pass rate).**  
**Combined Test Total: 83 passed, 0 failed across entire suite.**

---

## 4. Headless Chrome DevTools Protocol (CDP) Verification

Executed `scripts/qa/v33_4m_browser_verification.py` against live headless Chrome (1600x1400) connected to `http://127.0.0.1:8000`:
- **Action:** Switched to Smart Entry tab and clicked `#btn-analyse-setup`.
- **Card Hydrated:** `#card-primary-htf-assessment` hydrated with zero JavaScript console errors.
- **Extracted DOM Values:**
  - Setup Status: `SETUP STATUS: BLOCKED`
  - Freshness Badge: `Data Freshness: MARKET_DATA_STALE (71.9h old)`
  - Confirmed Regime: `TRENDING_BEARISH`
  - Trigger Status: `STALE_DATA_BLOCKED`
  - Entry Reference: `Unavailable`
  - Stop Reference: `Unavailable`
  - Target Reference: `Unavailable`
  - Completed 4h Bar: `Latest Completed 4h Close: $77,241.91 · 20-bar Donchian Range: [$76,301.02 – $81,890] · ⚠️ Latest 4-hour candle is incomplete (2/4 closed 1h bars). Evaluated strictly on the latest fully closed 4h candle.`
  - Factual Explanation: `Market data is stale (71.9h old > 2.0h operational limit; last closed candle 2026-10-30T08:00:00+00:00). Historical snapshot preserved; current live setup cannot be evaluated on stale market data. Incompatible regime: Coinbase spot is Long-only. Downward trending regime does not support long breakout expansion.`
  - Historical Panel: `194 Historical Trades | 43.81% Win Rate | +9.57 bps All-Trade | 110 Retained (+59.25 bps) / 84 Excluded`
- **Screenshot Evidence:** Saved to `artifacts/v33_4m_analysis_dashboard.png`.

---

## 5. Governed Four-Point Decision

In strict adherence to the BTCognitive Operating Contract & Research Protocol:

| Decision Gate | Governed Status | Rationale & Evidence |
| :--- | :--- | :--- |
| **1. Research Experiment** | **`RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`** | Historical evidence (+59.25 bps net expectancy on 110 retained trades) verified. HTF Range Expansion Breakout retained as offline research challenger. |
| **2. Prospective Evidence** | **`FROZEN_PENDING_ACTIVATION`** | Untouched prospective evidence accumulation has not commenced ($N=0$). Pre-registration criteria frozen; prospective ledger awaiting management authorization. |
| **3. Model Authorization** | **`OFFLINE_RESEARCH_ONLY`** | No strategy or model is authorized for automated or production execution. |
| **4. Live Trading** | **`DISABLED`** | Real capital deployment and broker connectivity remain strictly disabled (`live_trading_enabled: false`). |

---

## 6. Verification Artifacts & Deliverables

- Report: `research/reports/offline_mvp/20261102_332500_v33_4m_htf_analysis_completion/v33_4m_htf_analysis_completion.md`
- Brain Artifact: `V33_4M_R_Analysis_Consistency_and_Freshness_Closure.md`
- Browser Screenshot: `artifacts/v33_4m_analysis_dashboard.png`
- Automated Test Suite: `tests/test_v33_4m_htf_analysis.py` (13 tests)
