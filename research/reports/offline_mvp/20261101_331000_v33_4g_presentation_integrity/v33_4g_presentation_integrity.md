# BTCognitive V33.4G — Forecast & Market-Data Presentation Integrity Report (F04 & F05)

**Milestone Identifier:** V33.4G  
**Execution Timestamp:** 2026-11-01 22:52:00 UTC+05:30  
**Scope:** Remediation and independent verification of F04 (Forecast Presentation Integrity) and F05 (Market-Price & Data-Source Disclosures).  
**Repository Branch:** `main` (commit SHA `25d483f4c3646661b57311de9d0b53d2be881adb`)  
**Operating Boundary:** Offline Research Only (`OFFLINE_RESEARCH_ONLY`), zero capital risk, Live Trading strictly `DISABLED`.

---

## 1. Executive Summary & Root Cause Analysis

During previous milestone audits (V33.4A–V33.4E), two presentation defects were registered:
- **F04 (Forecast Presentation Integrity):** Hardcoded demonstration fallback values existed in frontend components (`PredictionPanel`, `AiForecastRiskOutlookView`, `MarketStateSection`, and `ExplainableAIPanel`). When the backend API truthfully returned `status: "BLOCKED_PROVENANCE_UNVERIFIED"` with `direction_state: "NOT_ESTIMATED"`, the UI defaulted to displaying `direction: "SHORT"`, `probability: 47.1%`, `model: "LightGBM Meta-Model (B4)"`, and `setup: "A1 (Liquidity Sweep / Reclaim)"`. Furthermore, statistical volatility risk estimates (such as the continuous 168-hour variance proxy `HAR-RS-DOW-v1.0` / C2 risk envelope) were conflated with directional return forecasting.
- **F05 (Market-Price & Data-Source Integrity):** Unconditional labels such as `"Live price"` and `"Spot Market Price: Coinbase BTC/USD Feed"` were displayed in the Hero section, Ticker bar, and Smart Entry view even though the underlying data feed was operating from a local historical snapshot (`LOCAL_HISTORICAL_SNAPSHOT` from 30 October 2026, 13:00 UTC). This created a risk of presenting historical, stale snapshot prices as current executable entry references.

---

## 2. Engineering Remediation Details

### 2.1 Backend Status Contract Repair (`engine/status_contract.py`)
- **Datetime Inspection Robustness:** Corrected timestamp extraction in `evaluate_system_status()`. In addition to `isinstance(df_cache.index, pd.DatetimeIndex)`, the evaluator now explicitly inspects `df_cache["timestamp"]` when using a `RangeIndex` with a timestamp column, extracting the true last closed candle (`2026-10-30 13:00:00+00:00`).
- **Truthful Snapshot Disclosure:** When operating in `LOCAL_HISTORICAL_SNAPSHOT` or `offline_research` data mode, the system authoritatively sets:
  - `market_data_status = "STALE"`
  - `source = "LOCAL_HISTORICAL_SNAPSHOT"`
  - `is_historical_snapshot = True`
  - `snapshot_label = "Last observed close — 30 October 2026, 13:00 UTC (STALE — NOT A CURRENT ENTRY REFERENCE)"`

### 2.2 Purging Demonstration Fallbacks (`web/app.js` & `web_src/smart_entry_simulator_view.js`)
- **`PredictionPanel`:**
  - Removed all hardcoded fallbacks (`SHORT`, `47.1%`, `LightGBM Meta-Model (B4)`, `A1 (Liquidity Sweep / Reclaim)`).
  - Separated into two distinct, un-conflated sections:
    1. **C2 Risk Forecast (`HAR-RS-DOW-v1.0` continuous variance proxy):** Displays dispersion range independently with an explicit notice:
       > *"Volatility risk envelope indicates dispersion range (continuous variance proxy); does NOT imply directional trade probability or win rate. Directional predictions remain strictly offline."*
    2. **Directional Return Forecast:** Requires an authenticated directional recommendation flag (`is_directional_recommendation_enabled === true`). Otherwise renders `DIRECTIONAL FORECAST UNAVAILABLE`, win probability `—`, and setup `No setup detected`.
  - Removed dummy fallback scores in `uncertainty_breakdown` (0.8, 1.0, 0.75, 0.84, 0.88), session context (`NEW_YORK_OVERLAP`), and funding drag (10.0 bps).
- **`AiForecastRiskOutlookView`:**
  - Removed hardcoded probabilities `0.5585` and `0.4415`, and unconditional `"FRESH"` badge.
  - Renders `ABSTAIN (SIGNAL DISABLED)`, `P(UP): —`, `P(DOWN): —`, and `Status: STALE (Historical Snapshot Close — Not Current Entry Reference)`.
- **`MarketStateSection` & `ExplainableAIPanel`:**
  - Purged fake percentage (`82%`), dummy regimes, and mock SHAP weights (`Momentum: 0.18`, etc.).
  - Replaced with honest `"Unavailable"` and `"Explanation data unavailable — no active model explanation payload."` disclaimers.

### 2.3 Stale Snapshot Disclosure Enforcement across Views
- **`HeroSection`:** Displays `"Historical Bar Close (October 30, 2026, 13:00 UTC)"` instead of `"Coinbase BTC/USD Feed"`, with amber badge `● HISTORICAL SNAPSHOT (STALE — NOT CURRENT ENTRY REFERENCE)`.
- **`SystemAtAGlanceCard`:** Renders `"1. Market Data (Historical Snapshot)"`, `$76,985.40` in amber, and subtext `"Last observed close — 30 October 2026, 13:00 UTC (STALE — NOT A CURRENT ENTRY REFERENCE)"`.
- **`InstitutionalTickerBar`:** Displays `"BTC/USD · Historical Snapshot (30 Oct 2026)"` with badge `"STALE — NOT A CURRENT ENTRY REFERENCE"`.
- **`ChartTopBar`:** Displays `"BTC / USD · Historical Bar Close (30 Oct 2026, 13:00 UTC · Stale Snapshot)"` with `"STALE SNAPSHOT"` badge.
- **`SmartEntrySimulatorView`:**
  - Replaced `"Live price: $76,985.4"` with `"Snapshot close: $76,985.40 (Last observed close — 30 October 2026, 13:00 UTC — STALE — NOT A CURRENT ENTRY REFERENCE)"`.
  - Replaced `"CURRENT SPOT PRICE"` with `"HISTORICAL SNAPSHOT CLOSE (STALE)"` and added amber subtext `"STALE — NOT A CURRENT ENTRY REFERENCE"`.

---

## 3. Independent Verification & Test Execution

### 3.1 Unit & Contract Verification (`tests/test_v33_4g_presentation_integrity.py`)
All 6 dedicated presentation integrity tests passed:
- `test_status_contract_stale_snapshot_disclosure`: PASSED
- `test_execution_status_strictly_disabled`: PASSED
- `test_prediction_api_returns_unverified_provenance`: PASSED
- `test_frontend_purged_of_hardcoded_forecast_fallbacks`: PASSED
- `test_frontend_market_price_integrity_disclosures`: PASSED
- `test_smart_entry_simulator_view_integrity`: PASSED

### 3.2 CDP Headless Chrome Verification (`scripts/qa/v33_4g_browser_verification.py`)
Executed live Chrome DevTools Protocol verification against real headless Chrome:
- **Test 1 (Desktop Viewport 1600x1000):**
  - `hasStaleNotice`: `True`
  - `hasHistoricalBarClose`: `True`
  - `hasCoinbaseFeedUnconditional`: `False` (zero instances)
  - `hasSnapshotClose`: `True`
  - `hasHardcodedShort`: `False` (zero instances)
- **Test 1B (Research Tab / PredictionPanel):**
  - `hasDirectionalUnavailable`: `True`
  - `hasRiskEnvelopeWarning`: `True`
  - `hasHardcodedShortFallback`: `False`
  - `hasRiskForecastAvailable`: `True` (`HAR-RS-DOW-v1.0` continuous variance proxy displayed with notice)
- **Test 1C (Forecast Tab / AiForecastRiskOutlookView):**
  - `hasAbstainSignalDisabled`: `True`
  - `hasHardcodedProb`: `False` (zero instances of 55.85% or 0.5585)
  - `hasStaleStatus`: `True`
- **Test 2 (Smart Entry Simulator View):**
  - `hasSnapshotCloseStale`: `True`
  - `hasStaleDisclaimer`: `True`
  - `hasOldSpotPrice`: `False` (`CURRENT SPOT PRICE` replaced)
- **Test 3 (Terminal View):**
  - `hasStaleNotice`: `True`
- **Test 4 (Mobile Viewport 375x812):**
  - `clientWidth`: 375 px (responsive, no viewport overflow)
  - `hasStaleNotice`: `True`

### 3.3 Full Regression Suite Execution
Executed command:
```powershell
.venv_win\Scripts\pytest.exe tests/test_v33_4g_presentation_integrity.py tests/test_v33_4f_decision_stability.py tests/test_v33_4_htf_prospective_protocol.py tests/test_v32_49_scenario_qa.py -v
```
**Result:** **61 passed in 32.89s (100% pass rate)**. Zero regressions detected.

---

## 4. Governed Four-Point Decision

1. **Research Experiment:** `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY` (`HTF_RANGE_EXPANSION_BREAKOUT` + `MarketRegimeClassifier` retained strictly as primary research candidate; not promoted to live).
2. **Prospective Evidence:** `FROZEN_PENDING_ACTIVATION` (Conformal ledger frozen at 7 blocks SHA-256 `ee58b37c...`; HTF shadow ledger inactive at 0 blocks).
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY` (no production serving authorization granted).
4. **Live Trading:** `DISABLED` (zero capital risk, pure market intelligence terminal).

