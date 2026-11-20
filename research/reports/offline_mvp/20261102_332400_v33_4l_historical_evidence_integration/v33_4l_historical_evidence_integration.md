# BTCognitive — Milestone V33.4L: Read-Only Historical Evidence Integration Report

**Date:** 2026-11-02  
**Milestone:** V33.4L  
**Classification:** `RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY`  
**Git Branch:** `main` | **Base SHA:** `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Operating Mode:** STRICT OFFLINE RESEARCH ONLY (`LIVE_TRADING = DISABLED`)  

---

## 1. Executive Summary

Milestone **V33.4L** successfully resolves the presentation gap identified in forensic audits F02, F06, and the V33.4J-R handover by safely integrating and presenting the validated retrospective research evidence for the **High-Timeframe (HTF) Range Expansion Breakout** candidate in the BTCognitive live dashboard without:
1. Conflating historical replay with prospective confirmation.
2. Triggering automated strategy authorization or buy/sell recommendations.
3. Invoking expensive runtime backtests inside interactive user loops.
4. Conflating retrospective replay datasets with untouched prospective evidence.

The verified historical evidence (194 trades, +9.57 bps Net EV across all trades; +59.25 bps Net EV across the 110 retained trades under Binance VIP0 26.0 bps friction) is now loaded via a tamper-evident, read-only evidence loader, exposed via a dedicated REST endpoint, and displayed prominently in the Smart Entry Simulator panel with clear epistemic classification and provenance disclosures.

---

## 2. Evidence Provenance & Cryptographic Lineage

### 2.1 Authoritative Disk Artifacts
The loader validates the integrity of the following immutable research ledgers using SHA-256 digests:
- **Trade Event Ledger:** `research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/v33_3a_194_trade_event_ledger.csv`  
  *SHA-256:* `0b1e1cd089f32798d6c011acf2900c42e1c94e0b97b3349b356c0b25189d8b00`
- **Exclusion Classification Ledger:** `research/reports/offline_mvp/20261031_330320_v33_03b_htf_closure/v33_3b_excluded_trade_classification.csv`  
  *SHA-256:* `59f89b90706e0d60e9feecea1dc6c09e3aa31265b3de77b834b18d78890eda67`

### 2.2 Dataset Lineage Qualification
In accordance with Management Directive V33.4J-R, the provenance status is formally disclosed as **`PARTIALLY_RESOLVED`**:
- **Original Research Manifest (V13 Lineage):** Recorded 41,273 bars ending `2026-09-16 16:00:00 UTC` (SHA-256: `b1900a7f450543c5643e0b713f738931c4361a4fb62f1110f34edc004844be18`).
- **Full 194-Trade Window:** Requires 41,397 hourly bars ending `2026-09-21 20:00:00 UTC` (SHA-256: `855f157d1fa28477908759adeb50bb1e26d0bd36a98f898808f83100138909b4`) to include the completed exit of Trade 194. Trade 194 was the final trade prior to the late-2026 research freeze.
- **Offline Reproduction Dataset:** `ohlcv_backfilled.parquet` (42,177 bars, SHA-256: `8936ed31ac2ec339f5add90bed350a1d378df573d15e292ed9a6cea9dbe4e069`).
- **Runtime Serving Dataset:** `ohlcv.parquet` (42,326 bars, SHA-256: `bbe0fc8c436526456899c4a8aa5abef929e85f3d1970551ec053051d5cf3f70c`).

---

## 3. Reconciled Statistical & Econometric Results

All calculations reflect the standard Binance VIP0 institutional cost structure (20.0 bps taker fee round-trip, 2.0 bps spread, 2.0 bps entry slippage, 2.0 bps exit volatility penalty = **26.0 bps total modeled drag**):

| Population Cohort | Trade Count | Win Rate (%) | Mean Gross Return | Mean Net Expectancy (VIP0) | Cumulative Net VIP0 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **All Historical Trades** | 194 | 43.81% (85/194) | +35.57 bps | **+9.57 bps** | +1,856.8 bps |
| **Retained Subgroup** | 110 | 48.18% (53/110) | +85.25 bps | **+59.25 bps** | **+6,518.0 bps** |
| — Trending Bull | 105 | 48.57% (51/105) | +89.15 bps | +63.15 bps | +6,631.2 bps |
| — Vol Compression Range | 3 | 33.33% (1/3) | +45.84 bps | +19.84 bps | +59.5 bps |
| — Trending Bear | 2 | 50.00% (1/2) | -60.34 bps | -86.34 bps | -172.7 bps |
| **Excluded Subgroup** | 84 | 38.10% (32/84) | -29.49 bps | **-55.49 bps** | **-4,661.2 bps** |
| — Consolidation Range | 75 | 40.00% (30/75) | -15.16 bps | -41.16 bps | -3,087.1 bps |
| — Transition / Unsupported | 9 | 22.22% (2/9) | -148.90 bps | -174.90 bps | -1,574.1 bps |

### Weighted Expectancy Parity Re-Verification:
$$\text{Retained Weighted Net EV} = \frac{105(+63.15) + 3(+19.84) + 2(-86.34)}{110} = \mathbf{+59.2546\text{ bps}}$$
$$\text{Excluded Weighted Net EV} = \frac{75(-41.16) + 9(-174.90)}{84} = \mathbf{-55.4902\text{ bps}}$$
$$\text{Total Population Net EV} = \frac{110(+59.2546) + 84(-55.4902)}{194} = \mathbf{+9.5712\text{ bps}}$$

---

## 4. Architectural & Implementation Deliverables

### 4.1 Historical Evidence Loader (`engine/historical_evidence_loader.py`)
- Singleton loader reading disk CSVs directly.
- Validates SHA-256 hashes against known constants.
- Validates that trade IDs are unique and strictly range from 1 to 194.
- Validates that the 110/84 partition is mutually exclusive and collectively exhaustive.
- Validates that every trade record includes 26.0 bps cost schedule.
- Emits structured dictionary with governance locks (`is_confirmatory = False`, `is_prospective = False`, `is_live_authorized = False`, `satisfies_prospective_gate = False`, `demo_fixtures_excluded = True`).

### 4.2 Dedicated REST API Endpoint (`GET /api/tournament/historical-evidence`)
- Route registered in `api/routes_tournament.py`.
- Non-blocking, cached, read-only endpoint returning HTTP 200 with full metrics and provenance.
- Never mutates runtime tournament state or creates trading proposals.

### 4.3 Dashboard Evidence Panel (`web/app.js` and `web_src/api_client.js`)
- Integrated into `SmartEntrySimulatorView`.
- Renders:
  - Header: Strategy name with `RETROSPECTIVE RESEARCH ONLY — NON-CONFIRMATORY` and `Provenance: PARTIALLY_RESOLVED` badges.
  - Four key metric cards: 194 Trades, 43.81% Win Rate, +9.57 bps Net EV, 110 / 84 Retained/Excluded (+59.25 bps on 110 retained).
  - Subgroup summaries detailing net contribution vs. drag eliminated.
  - Separate Current Setup Assessment banner informing the user that historical results do not determine current market entry readiness.
  - Prospective Validation banner clearly marking prospective status as `NOT VALIDATED` (0 events accumulated).
  - Explicit non-execution legal disclaimer (`Real trading remains strictly DISABLED`).

---

## 5. Verification Results

### 5.1 Unit Tests (`tests/test_v33_4l_historical_evidence.py`)
- **10/10 Passed** (18.15s):
  1. `test_valid_artifact_loading`: Verifies SHA-256, 194 trades, and exact arithmetic.
  2. `test_110_84_partition_integrity`: Verifies mutual exclusivity and collective exhaustiveness.
  3. `test_dataset_provenance_qualification`: Verifies fingerprint separation and PARTIALLY_RESOLVED status.
  4. `test_missing_artifact_handling`: Verifies fail-closed behavior on missing CSV.
  5. `test_artifact_hash_mismatch`: Verifies fail-closed behavior on altered CSV content.
  6. `test_corrupted_duplicate_trade_ids`: Verifies detection of non-unique trade IDs.
  7. `test_incorrect_cost_assumption`: Verifies detection of modified cost models.
  8. `test_demo_fixture_and_prospective_isolation`: Verifies that mock registry attempts (N=4) and prospective shadow ledger remain untouched and isolated.
  9. `test_api_historical_evidence_endpoint`: Integration test for `GET /api/tournament/historical-evidence`.
  10. `test_historical_evidence_non_interference_with_stale_market_data`: Verifies decoupling from stale market feeds.

### 5.2 Regression Suite
- **60/60 Passed** (30.82s across `test_v33_4h_backtest_isolation.py`, `test_v33_4f_decision_stability.py`, `test_v33_4g_presentation_integrity.py`, `test_v32_49_scenario_qa.py`).
- Total suite: **70/70 tests passing (100%)**.

### 5.3 Browser CDP End-to-End Verification (`scripts/qa/v33_4l_browser_verification.py`)
- Executed against live running backend server (`http://127.0.0.1:8000`).
- Headless Chrome connected via Chrome DevTools Protocol.
- Verified DOM elements:
  - `#historical-research-evidence-panel`: Present and populated.
  - `#badge-historical-classification`: `RETROSPECTIVE RESEARCH ONLY — NON-CONFIRMATORY`.
  - `#badge-provenance-status`: `Provenance: PARTIALLY_RESOLVED`.
  - `#metric-historical-trades`: `194`.
  - `#metric-historical-winrate`: `43.81%`.
  - `#metric-historical-expectancy`: `+9.57 bps`.
  - `#metric-historical-retained`: `110 / 84` and `+59.25 bps on 110 retained`.
  - `#banner-current-setup-assessment`: Present and explicit.
  - `#banner-prospective-validation`: Present and indicates `NOT VALIDATED`.
  - `#disclaimer-historical-evidence`: Contains `Real trading remains strictly DISABLED`.
- Screenshot captured: `artifacts/v33_4l_historical_evidence_dashboard.png`.

---

## 6. Governed Four-Point Decision

1. **Research Experiment:** `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`  
   The HTF Range Expansion Breakout strategy is retained as the primary research candidate with documented retrospective profitability (+59.25 bps on 110 retained trades). It remains an unproven hypothesis for prospective trading.
2. **Prospective Evidence:** `FROZEN_PENDING_ACTIVATION`  
   No prospective observations have been accumulated. The shadow ledger remains at $N=0$ events. Historical replay data cannot satisfy the prospective hurdle ($N \ge 100$).
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`  
   Runtime models and strategy rules are strictly locked to offline research. No production execution authorization is granted.
4. **Live Trading:** `DISABLED`  
   Zero orders, zero broker connectivity, zero capital deployment.

---

## 7. Open Issues & Next Steps

- **F07 (Open for Milestone V33.4M):** Canonical regime mapping alignment. The strategy registry currently lists only `['VOLATILITY_EXPANSION']` for `HTF_RANGE_EXPANSION_BREAKOUT` (omitting `TRENDING_BULLISH` where 105 of the 110 profitable trades occurred). In V33.4M, the strategy contract and regime alignment will be addressed to enable setup evaluation in current bullish regimes without altering frozen code.
- **F08 (Open for Milestone V33.4N):** Server startup, runtime health, and end-to-end Analysis reliability verification.

