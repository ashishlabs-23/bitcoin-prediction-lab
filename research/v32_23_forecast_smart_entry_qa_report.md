# BTCognitive V32.23 — End-to-End AI Forecast & Smart Entry Recovery Report

**Document ID:** `BTC-REP-V32.23-FORECAST-SMART-ENTRY-RECOVERY`  
**Execution Timestamp:** 2026-10-24T21:22:00+05:30 (UTC: 2026-10-24T15:52:00Z)  
**Authoritative Environment:** Windows x64 · PowerShell · Python 3.13 (.venv_win) · Node.js v20.14.0  
**Repository Branch / HEAD Commit:** `v32-longitudinal-monitoring-active` / `25d483f`  
**Operating Boundary:** Research Intelligence & Risk Containment · Live Execution Strictly `DISABLED`  

---

## 1. Executive Summary & Root Cause Analysis

Following the V32.22 chart desynchronization fix, this V32.23 audit and recovery task conducted an exhaustive forensic investigation into the end-to-end AI forecast pipeline and Smart Entry decision path. The objective was to make the system's authentic output visible, traceable, correctly timestamped, and scientifically honest without forcing live trades or fabricating artificial alpha.

### Root Cause Analysis of Investigated Defects

| Pipeline Component | Suspected / Documented Defect | Forensic Investigation Finding | Final Remediation / Governance Status |
| :--- | :--- | :--- | :--- |
| **Model Artifacts & Checksums** | Conflicting historical checksum prefixes reported in prior audit logs for directional GBDTs (`29589feb`, `70bd910a`, `63720157`). | Full 64-character SHA-256 digests computed directly from disk match `directional_models_freeze_metadata.json` byte-for-byte. The prior conflict was caused by truncated 8-character string representations in prose logs. | **VERIFIED (Artifact Integrity Valid)**. Directional models are verified on disk but strictly gated to `OFFLINE_RESEARCH_ONLY`. |
| **Target Identity & Prediction Output** | Plotted chart line perceived as an AI directional price prediction. | The displayed forecast line is `EMPIRICAL_CONFORMAL_PERSISTENCE_v1.0` ($S_0$ Random Walk persistence baseline), accompanied by nominal diffusion bands ($\pm 1.645 \sigma \sqrt{h}$). It is **not** a directional classifier or machine-learning price predictor. | **GOVERNED & LABELED**. Chart series and contract explicitly labeled as Non-Directional Baseline ($S_0$) + Nominal Diffusion Bands. |
| **Diffusion Band Coverage** | Plotted bands represented as 90% conformal coverage. | Diffusion bands scale parametrically with $\sqrt{h}$ under nominal Gaussian assumptions ($z=1.645$). They have not been calibrated on out-of-sample BTC empirical return distributions. | **GOVERNED & LABELED**. Formally tagged as `NOMINAL_UNCALIBRATED_GAUSSIAN` in API schema and chart overlay. |
| **Smart Entry $\mu=0.0$ Defect** | Drift score calculated and discarded when PDE solver called with $\mu=0.0$. | The heuristic score (`mom_1h`, `rs_ratio`) has no econometric calibration to physical or risk-neutral drift. Directional GBDTs have ~52.1% accuracy (Brier score 0.249), offering no statistically proven directional edge. Mapping heuristic scores or uncalibrated probabilities directly to drift $\mu$ would constitute synthetic fabrication. | **RESOLVED VIA NULL BASELINE**. Drift is explicitly held at $\mu=0.0$ (`DRIFTLESS_NULL_BASELINE`). Under $\mu=0.0$, expected net return is negative after 9.3–87 bps transaction friction. Smart Entry's `ABSTAIN` is the **correct scientific decision**, not a runtime software defect. |
| **Prospective Ledger Containment** | Concern over side-effect writes to ledgers during chart scrubbing, UI polling, or test execution. | V32.18 / V32.19 containment verified. Smart Entry `evaluate_market()` and research API endpoints default to `persist=False`, performing zero disk writes. | **VERIFIED & CONTAINED**. All 5 protected ledgers and raw parquets have 100% bit-identical SHA-256 digests before and after test execution. |

---

## 2. Model Identity, Training Provenance & Artifact Gate

### Authoritative Model Inventory & Disk Hash Audit

Each model artifact on disk was independently inspected and hashed using SHA-256:

| Canonical Model ID | Disk Artifact Path | Actual Disk SHA-256 Digest | Authoritative Manifest / Registry Hash | Classification Status |
| :--- | :--- | :--- | :--- | :--- |
| **`HAR-RS-DOW-v1.0`** | `experiments/results/freeze/har_rs_dow_v1.joblib` | `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b` | `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b` | **VERIFIED** (`AUTHORIZED_FOR_PRODUCTION` — Volatility Risk Intelligence Only) |
| **`directional-gbm-1h-v1`** | `models/registry/research/directional_gbm_1h_v1.joblib` | `29589feb99a00bf86d71b46c5986d25d410a71fbf0e630345a70d4fe9da97ac1` | `29589feb99a00bf86d71b46c5986d25d410a71fbf0e630345a70d4fe9da97ac1` | **PARTIALLY VERIFIED** (`OFFLINE_RESEARCH_ONLY` — Disconnected from live runtime) |
| **`directional-gbm-4h-v1`** | `models/registry/research/directional_gbm_4h_v1.joblib` | `70bd910add16f9b63152a6c8884b51762d2aea56cdef83f2387df733bea6f57d` | `70bd910add16f9b63152a6c8884b51762d2aea56cdef83f2387df733bea6f57d` | **PARTIALLY VERIFIED** (`OFFLINE_RESEARCH_ONLY` — Disconnected from live runtime) |
| **`directional-gbm-24h-v1`** | `models/registry/research/directional_gbm_24h_v1.joblib` | `637201570381aa8a3cf2fa812a0fac1f80b2a67a8910b414cf85abe605ef0348` | `637201570381aa8a3cf2fa812a0fac1f80b2a67a8910b414cf85abe605ef0348` | **PARTIALLY VERIFIED** (`OFFLINE_RESEARCH_ONLY` — Disconnected from live runtime) |
| **`EMPIRICAL_CONFORMAL_PERSISTENCE_v1.0`** | N/A (Algorithmic Martingale Baseline) | N/A (Causal code baseline) | `models/authoritative_model_registry.py` | **VERIFIED** (`OFFLINE_RESEARCH_ONLY` — Plotted as baseline on chart) |

### Detailed Training Contract & Horizon Audit

1. **`HAR-RS-DOW-v1.0`**:
   - **Target**: Annualized 7-Day Realized Variance (`rv7d_var_ann`).
   - **Sampling**: Hourly OHLCV from `data/raw/ohlcv.parquet`.
   - **Features (10)**: `log_rv_down_1d`, `log_rv_up_1d`, `log_rv7d_var_ann_lag`, `log_rv30d_var_ann`, `dow_1`...`dow_6`.
   - **Target Separation Invariant**: Does **not** predict price direction or future closing price. Authorized exclusively for volatility regime quantification and C2 conformal risk containment.
2. **Directional GBDTs (`1h`, `4h`, `24h`)**:
   - **Target**: Sign of forward log return ($\ln(C_{t+h} / C_t) > 0$).
   - **Features (4)**: Causal lagged log returns (`ret_1h`, `ret_4h`, `ret_24h`, `ret_168h`).
   - **Training Window**: 2022-01-08T00:00:00Z to 2025-12-31T22:00:00Z ($N \approx 34,894$).
   - **Blocker Preventing Live Connection**: Out-of-sample directional hit rate is $52.14\%$ for 1h, $52.00\%$ for 4h, and $48.65\%$ for 24h. Diebold-Mariano paired tests against the zero-drift null yield $p > 0.15$. After deducting realistic transaction friction (9.3 to 87 bps round-trip), net expectancy is strictly negative ($-0.17R$ to $-0.87R$). Connecting these models to live trade generation would violate the BTCognitive Epistemic Prime Directive.

---

## 3. AI Forecast Backend, Response Schema & Baselines

### Separation of Real Forecasts from Baselines

The backend implementation across `engine/forecast_engine_15m.py` and `api/market_monitor_routes.py` enforces a rigorous schema separation:
- **Model ID**: `EMPIRICAL_CONFORMAL_PERSISTENCE_v1.0`
- **Forecast Type**: `NON_DIRECTIONAL_RESEARCH_BASELINE`
- **Target Definition**: `{horizon} Non-Directional Persistence Baseline & Nominal Model Diffusion Envelope`
- **Diffusion Calibration**: `NOMINAL_UNCALIBRATED_GAUSSIAN`
- **Directional Classifier Status**: `DISCONNECTED_UNVALIDATED_EDGE` (`OFFLINE_RESEARCH_ONLY`)
- **Directional Recommendation**: `ABSTAIN`
- **Live Trading**: `DISABLED`

### Timestamp Monotonicity & Closed-Candle Integrity

1. **Anchor Synchronization**: The forecast origin ($t_0$) anchors strictly to the latest completed closed candle from Coinbase REST (`coinbase_15m_adapter.py`) or hourly cache (`feature_cache`).
2. **Strictly Forward Projection**: Projections extend into the future at step increments:
   - 15m Horizon: $t_0 + 900\text{s}, t_0 + 1800\text{s}, t_0 + 2700\text{s}, t_0 + 3600\text{s}$.
   - 1h Horizon: $t_0 + 3600\text{s}, t_0 + 7200\text{s}, t_0 + 10800\text{s}, t_0 + 14400\text{s}$.
3. **No Synthetic Replacement**: If market data is stale ($> 1800\text{s}$) or contains $< 32$ candles, the endpoint fails closed and returns `status: DATA_UNAVAILABLE` rather than fabricating synthetic points.

---

## 4. Smart Entry Decision Path & $\mu=0.0$ Resolution

### Investigation of Heuristic Drift vs. Martingale Null

In `engine/probabilistic_entry_engine.py`, `evaluate_decision_gate()` calls:
```python
probs = self.predict_barrier_probabilities(features=feats, k_tp=k_tp, k_sl=k_sl, mu=0.0)
```
The audit confirmed:
1. **Heuristic Score Discarded**: The heuristic momentum and range position scores (`mom_1h`, `range_pos`) were computed but not mapped to $\mu$.
2. **Why Mapping to Drift is Blocked**:
   - In continuous-time diffusion ($dS_t = \mu S_t dt + \sigma S_t dW_t$), drift $\mu$ represents the instantaneous annualized expected return.
   - An ad-hoc technical score bounded in $[-1, 1]$ has no econometric units, no physical scale, and no empirical calibration to forward returns.
   - Setting $\mu = \text{score}$ would artificially inflate $P(\text{TP})$ and generate fictitious positive expectancy.
3. **Econometric Null Baseline**:
   - Under driftless Brownian motion ($\mu = 0.0$), the First-Passage PDE solution with empirical fat-tail calibration $c_\sigma = 1.0518$ yields $P(\text{TP}) \approx 0.18$, $P(\text{SL}) \approx 0.32$, and $P(\text{timeout}) \approx 0.50$ for barriers $k_{\text{TP}}=1.5, k_{\text{SL}}=1.0$.
   - For any transaction cost tier (12 bps to 187 bps), net expectancy is negative:
     $$\mathbb{E}[\text{Net } R] = (0.18 \times 1.5) - (0.32 \times 1.0) + (0.50 \times (-0.05)) - \text{friction}_R < 0$$
   - Since $P(\text{TP}) = 0.18 < 0.60$ (the selective hurdle) and $\mathbb{E}[\text{Net } R] < 0$, the decision engine must return `ABSTAIN`.
4. **Governed Decision**:
   - We updated `engine/probabilistic_entry_engine.py`, `engine/smart_entry_engine.py`, and `api/routes_research.py` to explicitly expose `"drift_parameter_mu": 0.0` and `"drift_status": "DRIFTLESS_NULL_BASELINE"`.
   - `ABSTAIN` is documented in all API responses as the **correct, scientifically validated outcome**, not a runtime software error.

---

## 5. Chart Semantics & Frontend Visibility

The frontend in `web/app.js` and `web/index.html` was audited and verified:
1. **Visual Separation**:
   - The forecast line is explicitly titled: `Forecast Baseline ($S_0$ Persistence)`.
   - Uncertainty bands are explicitly titled: `Nominal Upper Band (90%)` and `Nominal Lower Band (90%)`.
   - The chart badge displays: `● Forecast Active · 15m Non-Directional Baseline ($S_0$) + Diffusion Bands (RESEARCH ONLY · LIVE TRADING DISABLED)`.
2. **Historical Accuracy vs. Live Probability**:
   - The UI displays: `HIST. BENCHMARK: ~52.1% (NEGATIVE EXPECTANCY AFTER COSTS)`.
   - It is visually separated from current market telemetry and marked as a retrospective walk-forward benchmark.
3. **No Marker Wiping**:
   - The V32.22 fix ensuring `showResearchMarkers` does not wipe live decision markers is preserved.
   - Decision markers display `AI: ABSTAIN (Tier 2 Gated)` with grey circle markers rather than misleading green buy arrows.
4. **Smart Entry Panel**:
   - Renders live snapshot evaluation with status `ABSTAIN` and data source badge `COINBASE BTC-USD SPOT (LIVE TELEMETRY)`.
   - Explicitly displays the primary reason: `NO_VALIDATED_EDGE_ABSTAIN: Geometry baseline shows negative net expectancy after transaction friction`.

---

## 6. Comprehensive QA Test Log & Regression Evidence

### Automated Pytest Suite Summary

| Test Module | Total Tests | Passed | Failed | Skipped | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`tests/test_v32_23_forecast_smart_entry_recovery.py`** | 8 | 8 | 0 | 0 | 48.78s |
| **`tests/test_v32_22_chart_and_forecast_integrity.py`** | 3 | 3 | 0 | 0 | (included) |
| **`tests/test_v10_market_data_and_forecast_chart.py`** | 9 | 9 | 0 | 0 | (included) |
| **`tests/test_smart_entry_engine.py`** | 2 | 2 | 0 | 0 | (included) |
| **`tests/test_smart_entry_api.py`** | 7 | 7 | 0 | 0 | (included) |
| **`tests/test_v32_18_persistence_containment.py`** | 8 | 8 | 0 | 0 | (included) |
| **Combined Full Regression Suite** | **37** | **37** | **0** | **0** | **54.57s** |

### Frontend Build & Unit Test Verification

- `npm run check`: **PASSED** (Syntax check across `web/app.js`, `web_src/api_client.js`, `web_src/websocket.js`, `web_src/formatters.js`).
- `npm run build`: **PASSED** (Asset verification for `index.html` (1.7 KB), `styles.css` (103.0 KB), `app.js` (679.4 KB)).
- `node tests_frontend.js`: **PASSED** (Deduplication, caching, 429 backoff, 29.5 req/min steady-state polling budget within 60 req/min server limit).

---

## 7. Protected File Integrity & Ledgers

All 5 protected data files were verified via SHA-256 before and after all testing and code edits:

| File Path | SHA-256 Digest | Status |
| :--- | :--- | :--- |
| `data/prospective_entry_ledger.jsonl` | `91C3AED984002F611A59C78A2EB4C342C0970BAEBBD2E3D6DF7973BE7ACF1DD7` | **UNMODIFIED** |
| `data/prospective_shadow_v1.jsonl` | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` | **UNMODIFIED** |
| `data/prospective_entry_ledger_v2.jsonl` | `E6E33E3C7BEB4C255467E967FC819B85481B0AFB1052C3EA7BD248C53F87B604` | **UNMODIFIED** |
| `data/raw/ohlcv.parquet` | `1E722F33734A89E74764C02FDE0552752CC1EA2EFF62CA9046C9D6EDF2347D5C` | **UNMODIFIED** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `C4949E5B5695FFA172677681B15AF2EA6167E73317C3496546F2286A6730B1C8` | **UNMODIFIED** |

---

## 8. Remaining Blockers & Next Research Steps

1. **Directional Return Edge**: Retrospective directional classifiers achieve ~52.1% accuracy, indistinguishable from random walk ($p > 0.15$). No directional trade execution can be authorized without prospective walk-forward evidence exceeding transaction friction.
2. **Diffusion Band Empirical Coverage**: The nominal bands on chart assume Gaussian diffusion ($\pm 1.645 \sigma \sqrt{h}$). Establishing formal 90% conformal coverage requires future conformal calibration on 15m BTC empirical return distributions.
3. **Execution Friction Hurdle**: With exchange fees between 9.3 bps and 87 bps round-trip, any strategy with $< 58\%$ win rate at 1.5:1 reward-to-risk ratio will yield negative net expectancy.

---

## 9. Final Governed Verdict

```
PARTIAL — CHART WORKS, DIRECTIONAL MODEL OR SMART ENTRY STILL BLOCKED
```

### Verdict Justification
1. **Chart Works**: The chart accurately renders validated Coinbase 15m and 1h spot candles, visualizes the non-directional persistence baseline ($S_0$), and plots nominal diffusion bands with correct UTC timestamps and zero marker wiping.
2. **Directional Model Blocked**: The directional GBDT models are verified on disk but strictly gated to `OFFLINE_RESEARCH_ONLY` due to ~52.1% retrospective hit rates and negative net expectancy after transaction costs. They are not connected to live price prediction.
3. **Smart Entry Blocked (Governed Abstain)**: Smart Entry evaluates live market snapshots under the driftless martingale null ($\mu=0.0$) and correctly fail-closes to `ABSTAIN` because geometry win probability ($18\%$) fails the selective hurdle ($60\%$) and net expectancy after transaction friction is negative.
4. **Live Trading**: Live order routing and execution remain strictly `DISABLED`. Zero writes are made to prospective ledgers.
