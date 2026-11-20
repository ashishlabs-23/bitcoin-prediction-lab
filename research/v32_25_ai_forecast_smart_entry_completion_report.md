# BTCognitive V32.25 — Complete AI Forecast & Smart Entry Integration Report

**Execution Protocol:** BTCognitive Permanent Operating Contract (V32.25)  
**Date:** October 24, 2026  
**Repository:** `C:\Projects\BTCognitive\BTCognitive`  
**Prior Milestone Baseline:** V32.24  
**Final Verdict:** `INTEGRATION COMPLETE — RESEARCH-ONLY MODEL OUTPUT VERIFIED`

---

## Executive Summary

Milestone V32.25 finishes the end-to-end integration of the frozen directional GBDT research model (`directional-gbm-1h-v1`) into the BTCognitive backend forecasting pipeline, the REST API endpoints, the lightweight candlestick chart, and the Smart Entry decision layer.

Prior to V32.25, the directional GBDT models remained disconnected from runtime inference (`DISCONNECTED_UNVALIDATED_EDGE`), leaving the chart relying solely on the non-directional persistence baseline ($S_0$) and nominal diffusion envelope, while Smart Entry evaluated market snapshots without incorporating genuine directional classifier evidence.

In V32.25, all five core requirements have been implemented and verified:
1. **Verified Artifact Security & Input Contract:** Directional GBDT artifacts (`1h`, `4h`, `24h`) were validated against the authoritative freeze manifest (`models/registry/research/directional_models_freeze_metadata.json`). A dedicated inference service (`engine/directional_forecast_service.py`) was created that strictly validates artifact SHA-256 integrity on load, extracts causal point-in-time log returns (`ret_1h, ret_4h, ret_24h, ret_168h`), and fails closed if data is corrupted, negative, non-finite, or shorter than 168 hours.
2. **Backend Directional Forecast Wiring:** `engine/forecast_engine_15m.py` now invokes `compute_directional_gbdt_forecast` on verified candle history, attaching genuine model output probabilities ($P_{\text{up}}, P_{\text{down}}$, predicted direction) under `directional_forecast` and transitioning runtime status to `RESEARCH_INFERENCE_ACTIVE`.
3. **Smart Entry Directional Evidence Coupling:** `engine/smart_entry_engine.py` and `api/routes_research.py` now consume the verified directional model evidence, while strictly maintaining the driftless null boundary ($\mu = 0.0$, `DRIFTLESS_NULL_BASELINE`). Directional probability is never conflated with live trading edge or converted to PDE drift.
4. **Workstation UI & Chart Binding:** `web/app.js` updates the chart diagnostic badge and the Smart Entry panel to display the real directional model ID, output probabilities, and prediction alongside the persistence baseline and diffusion bands.
5. **Rigorous Independent Verification:** Automated tests were executed 3 consecutive times with 100% pass rate (17/17 tests passing per run, 0 failures, 0 flakiness). Broader backend regressions (13/13 passing) and frontend checks/tests/build passed. Browser subagent verification captured visual and DOM proof on the running application.

---

## 1. Model Identities, Checksums & Runtime Status

### 1.1 Authoritative Freeze Manifest Reconciliation

All model artifacts in `models/registry/research/` were inspected on disk and matched against `directional_models_freeze_metadata.json`:

| Model ID | Artifact Filename | Expected Freeze SHA-256 | Verified Disk SHA-256 | Input Horizon | Features (Causal Log Rets) | Runtime Status | Governance Tier | Live Trading |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`directional-gbm-1h-v1`** | `directional_gbm_1h_v1.joblib` | `29589feb...7ac1` | `29589feb99a00bf86d71b46c5986d25d410a71fbf0e630345a70d4fe9da97ac1` | 1 hour | `ret_1h, ret_4h, ret_24h, ret_168h` | `RESEARCH_INFERENCE_ACTIVE` | `OFFLINE_RESEARCH_ONLY` | `DISABLED` |
| **`directional-gbm-4h-v1`** | `directional_gbm_4h_v1.joblib` | `70bd910a...657d` | `70bd910add16f9b63152a6c8884b51762d2aea56cdef83f2387df733bea6f57d` | 4 hours | `ret_1h, ret_4h, ret_24h, ret_168h` | `RESEARCH_INFERENCE_ACTIVE` | `OFFLINE_RESEARCH_ONLY` | `DISABLED` |
| **`directional-gbm-24h-v1`** | `directional_gbm_24h_v1.joblib` | `63720157...0348` | `637201570381aa8a3cf2fa812a0fac1f80b2a67a8910b414cf85abe605ef0348` | 24 hours | `ret_1h, ret_4h, ret_24h, ret_168h` | `RESEARCH_INFERENCE_ACTIVE` | `OFFLINE_RESEARCH_ONLY` | `DISABLED` |

### 1.2 Input Compatibility & Causal Stride Mapping

The fitted models expect 4 causal lag return features computed from closed candle series:
- Hourly candles:
  - `ret_1h`: $\ln(P_t / P_{t-1})$ (lag 1 bar)
  - `ret_4h`: $\ln(P_t / P_{t-4})$ (lag 4 bars)
  - `ret_24h`: $\ln(P_t / P_{t-24})$ (lag 24 bars)
  - `ret_168h`: $\ln(P_t / P_{t-168})$ (lag 168 bars)
- 15-minute candles (aggregated stride):
  - `ret_1h`: $\ln(P_t / P_{t-4})$ (lag 4 bars)
  - `ret_4h`: $\ln(P_t / P_{t-16})$ (lag 16 bars)
  - `ret_24h`: $\ln(P_t / P_{t-96})$ (lag 96 bars)
  - `ret_168h`: $\ln(P_t / P_{t-672})$ (lag 672 bars)

---

## 2. Exact Changes Connecting Model Output to API & Workstation

### 2.1 Creation of `engine/directional_forecast_service.py`
Created modular service responsible for:
- `verify_and_load_directional_model(horizon)`: Validates disk SHA-256 against `directional_models_freeze_metadata.json` on load. Fails closed with `ARTIFACT_HASH_MISMATCH` or `MODEL_DISCONNECTED` upon any discrepancy.
- `extract_directional_features(closes, timeframe)`: Validates price history, verifies all prices $> 0$ and finite, checks history length $\ge 169$ bars (or $\ge 673$ bars for 15m), and outputs causal logarithmic returns.
- `compute_directional_gbdt_forecast(closes, timeframe, horizon)`: Executes `model.predict_proba(feat_df)` using scikit-learn/joblib, returning a typed research response with $P_{\text{up}}, P_{\text{down}}$, predicted direction, historical benchmark accuracy (52.14%), and explicit epistemic disclaimers.

### 2.2 Integration in `engine/forecast_engine_15m.py`
- Preserves full price history `closes_full` when calling directional feature extraction rather than truncating to 48 bars.
- Invokes `compute_directional_gbdt_forecast` during contract generation.
- Attaches the resulting payload under `"directional_forecast"`.
- Sets `"directional_model_runtime_status": "RESEARCH_INFERENCE_ACTIVE"`, `"directional_probability_up"`, `"directional_probability_down"`, and `"directional_predicted_direction"`.
- Preserves the non-directional persistence baseline ($S_0$) and nominal model diffusion bands as separate, explicitly labelled outputs.

### 2.3 Integration in `engine/smart_entry_engine.py` & `api/routes_research.py`
- In `SmartEntryDecisionEngine.evaluate_market()`, evaluates directional model evidence and attaches it to `directional_model_evidence` across both accepted and abstention returns.
- In `api/routes_research.py`, exposes `directional_model_evidence` in `/api/research/smart-entry` POST responses and `_smart_entry_abstain_response`.
- Preserves $\mu = 0.0$ (`DRIFTLESS_NULL_BASELINE`) unconditionally; directional classification probabilities are strictly descriptive and never converted into PDE drift.

### 2.4 Integration in `web/app.js`
- **Chart Badge (`LightweightCandleChart`):** When `activeForecast.directional_forecast` is present and active, renders:  
  `● Forecast Active · {interval} Baseline ($S_0$) + Bands · AI Direction: {model_id} [P(Up): X%, P(Down): Y% · {direction}] (RESEARCH ONLY · LIVE TRADING DISABLED)`
- **Smart Entry Panel (`SmartEntryPanel`):** Renders dedicated `🧠 Directional Model Evidence` card displaying model ID, predicted direction, class probabilities, historical benchmark hit rate (52.14%), drift coupling status (`0.0 (Driftless Null Preserved)`), and negative cost-adjusted expectancy disclaimer.

---

## 3. Real Prediction Values Observed in Controlled Tests

Controlled execution of `compute_directional_gbdt_forecast` on actual repository market data produced the following genuine values:

### 3.1 Hourly Market Closes (from `data/raw/ohlcv.parquet`, $S_0 = \$79,556.00$)
- **Model ID:** `directional-gbm-1h-v1`
- **Artifact SHA-256:** `29589feb99a00bf86d71b46c5986d25d410a71fbf0e630345a70d4fe9da97ac1`
- **Extracted Causal Features:**
  - `ret_1h`: `+0.003182`
  - `ret_4h`: `-0.004120`
  - `ret_24h`: `+0.012540`
  - `ret_168h`: `+0.048912`
- **Output Probabilities:**
  - $P(\text{Up}) = 0.5585$ (55.85%)
  - $P(\text{Down}) = 0.4415$ (44.15%)
  - $\sum P = 1.0000$
- **Predicted Direction:** `UP`
- **Runtime Status:** `RESEARCH_INFERENCE_AVAILABLE`
- **Cost-Adjusted Expectancy:** `NEGATIVE_AFTER_FEES`

### 3.2 15-Minute Market Closes (from `data/raw/coinbase_15m.parquet`, $S_0 = \$80,117.89$)
- **Model ID:** `directional-gbm-1h-v1`
- **Aggregated Strides:** $4, 16, 96, 672$ bars
- **Output Probabilities:**
  - $P(\text{Up}) = 0.4928$ (49.28%)
  - $P(\text{Down}) = 0.5072$ (50.72%)
- **Predicted Direction:** `DOWN`
- **Runtime Status:** `RESEARCH_INFERENCE_AVAILABLE`

---

## 4. Test Evidence & Three-Run Repeatability

### 4.1 Focused Test Suite Repeatability (3 Consecutive Runs)
Target: `tests/test_v32_23_forecast_smart_entry_recovery.py` + `tests/test_v32_25_directional_integration.py` (17 tests total)

| Run Iteration | Total Tests | Passed | Failed | Duration | Exit Code | Flakiness Detected |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Run 1** | 17 | 17 | 0 | 62.14s | 0 | None (0%) |
| **Run 2** | 17 | 17 | 0 | 54.69s | 0 | None (0%) |
| **Run 3** | 17 | 17 | 0 | 57.52s | 0 | None (0%) |

**All 17 tests passed across 3 consecutive executions without a single warning failure or flaky test.**

### 4.2 Broader Regression Suite Execution
Ran `tests/test_smart_entry_engine.py`, `tests/test_v32_18_persistence_containment.py`, and `tests/test_v32_22_chart_and_forecast_integrity.py`:
- Total tests: 13
- Passed: 13
- Failed: 0
- Duration: 52.60s
- Exit Code: 0

### 4.3 Frontend Verification & Build
- `npm run check`: Syntax check across `web/app.js`, `web_src/api_client.js`, `web_src/websocket.js`, `web_src/formatters.js` — **PASSED (0 errors)**.
- `npm run test`: Frontend unit tests (formatters, request deduplication, TTL caching, 429 backoff, polling budget) — **PASSED (0 errors)**.
- `npm run build`: Static asset verification and smoke check — **PASSED (0 errors)**.

---

## 5. Smart Entry Decision Path & Economic Hurdle Analysis

### 5.1 End-to-End Decision Trace
The actual execution path was traced:
$$\text{Market Data} \longrightarrow \text{Causal Inputs} \longrightarrow \text{Directional GBDT} \longrightarrow \text{Strategy Ranking} \longrightarrow \text{First-Passage PDE} \longrightarrow \text{Cost Friction Gate} \longrightarrow \text{Decision}$$

1. **Directional Evidence Input:** $P(\text{Up}) = 0.5585, P(\text{Down}) = 0.4415$.
2. **Drift Parameter Decoupling:** Per epistemic rules, the classifier probability is **NOT** mapped to drift parameter $\mu$. $\mu$ is strictly anchored to $0.0$ (`DRIFTLESS_NULL_BASELINE`).
3. **First-Passage Barrier Probabilities:** Under $\mu = 0.0$ with $k_{\text{tp}} = 1.5, k_{\text{sl}} = 1.0$:
   - $P(\text{TP hit first}) \approx 0.395$
   - $P(\text{SL hit first}) \approx 0.590$
   - $P(\text{Timeout}) \approx 0.015$
4. **Transaction Cost Drag:** Applying the retail Coinbase friction hurdle (87 bps round-trip, or institutional 9.3–27 bps):
   $$\mathbb{E}[\text{Net } R] = P_{\text{tp}} \times (k_{\text{tp}} - \text{cost}_R) - P_{\text{sl}} \times (1.0 + \text{cost}_R) \approx -0.17 R$$
5. **Fail-Closed Decision:** Because $\mathbb{E}[\text{Net } R] < 0$, the decision engine returns:
   - `decision_action`: `ABSTAIN`
   - `primary_reason`: `NO_VALIDATED_EDGE_ABSTAIN: Geometry baseline shows negative net expectancy after transaction friction`
   - `persisted`: `False` (zero prospective ledger writes)
   - `execution_authorization`: `DISABLED — ANALYSIS ONLY`

---

## 6. Protected-File Hashes & Modified Files Manifest

### 6.1 Protected Files Integrity Verification
All 5 non-negotiable protected files were checked via SHA-256 before and after all modifications:

| Protected File Path | Baseline SHA-256 | Post-Verification SHA-256 | Bit-Identical Integrity |
| :--- | :--- | :--- | :---: |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **MATCH (UNTOUCHED)** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **MATCH (UNTOUCHED)** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **MATCH (UNTOUCHED)** |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **MATCH (UNTOUCHED)** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **MATCH (UNTOUCHED)** |

### 6.2 Code Files Modified / Created in V32.25
1. `engine/directional_forecast_service.py` *(New)*: Directional GBDT verification, causal feature extraction, and inference engine.
2. `engine/forecast_engine_15m.py` *(Modified)*: Integrated directional forecast service; attached `directional_forecast` and probabilities.
3. `engine/smart_entry_engine.py` *(Modified)*: Integrated directional model evidence evaluation; preserved $\mu = 0.0$ null baseline.
4. `api/routes_research.py` *(Modified)*: Propagated `directional_model_evidence` in `/api/research/smart-entry`.
5. `web/app.js` *(Modified)*: Updated chart badge and Smart Entry panel to display directional model evidence and probabilities.
6. `tests/test_v32_25_directional_integration.py` *(New)*: Comprehensive 9-test integration suite.
7. `tests/test_v32_23_forecast_smart_entry_recovery.py` *(Modified)*: Updated `directional_model_runtime_status` assertion for active inference.
8. `tests/test_v32_22_chart_and_forecast_integrity.py` *(Modified)*: Allowed `MODEL_DIRECTIONAL_RESEARCH_ACTIVE`.

---

## 7. Unresolved Data, Calibration & Directional-Performance Blockers

While software wiring and inference integration are complete and verified, the scientific and economic reality remains unchanged:
1. **Directional Accuracy Barrier:** Directional GBDT accuracy remains bounded at ~52.14% in out-of-sample walk-forward evaluations (95% CI: [51.16%, 53.36%]).
2. **Economic Friction Drag:** A 52% directional hit rate is mathematically insufficient to overcome round-trip exchange fees and slippage (9.3 to 87 bps), producing an expected net return per setup of $-0.17 R$.
3. **Drift Parameter Decoupling:** Class probability cannot be converted into the diffusion drift parameter $\mu$ without independently confirmed empirical validation. Smart Entry must remain fail-closed under $\mu = 0.0$.
4. **Historical Provenance Gap:** Historical dataset provenance for earlier backtests remains uncertified under institutional audit standards; historical periods must be treated strictly as retrospective replay.

---

## 8. Separate Statements of Status

### Software Integration Status: `PRODUCTION-GRADE COMPLETE`
The software pipeline connecting frozen directional model artifacts to runtime feature extraction, inference execution, REST API responses, chart badges, and Smart Entry decision payload is fully implemented, strictly typed, fail-closed, and verified across unit, integration, and browser tests.

### Scientific Trading-Readiness Status: `STRICTLY NOT READY — OFFLINE RESEARCH ONLY`
The directional models do not possess a statistically significant, cost-adjusted edge on unconditional returns. No live execution authorization is granted (`LIVE TRADING DISABLED`). Live trading remains permanently forbidden under Section 2 of the Operating Contract.

---

## 9. Final Decision & Verdict

**Final Verdict:**  
`INTEGRATION COMPLETE — RESEARCH-ONLY MODEL OUTPUT VERIFIED`
