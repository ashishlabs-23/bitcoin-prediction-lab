# BTCognitive V32.26 — Evidence-First Model, Strategy & Data Provenance Audit Report

**Execution Protocol:** BTCognitive Master Multi-Agent Engineering & Research Protocol  
**Audit Date:** October 25, 2026 (05:10 UTC)  
**Target Repository:** `c:\Projects\BTCognitive\BTCognitive`  
**Operating Mode:** `OFFLINE_RESEARCH_ONLY`  
**Live Trading:** `DISABLED` (Non-execution invariant strictly enforced)  
**Primary Governance Verdict:** `SAFE FOUNDATIONS COMPLETE — CONFIRMATORY GATES BLOCKED ON DATA PROVENANCE & META-MODEL`  

---

## Executive Summary & Epistemic Verdict

This report establishes the forensic baseline, data lineage audit, mathematical contract verification, and multi-agent research plan for transitioning BTCognitive from a preliminary strategy-to-alert scaffold into an evidence-based, cost-aware research system.

### Core Governance Findings:
1. **Model Forecast vs. Market Edge Reality:**  
   Neither our internal directional models nor external foundation models currently produce a positive trading edge after costs. Our canonical `HAR-RS-DOW-v1.0` volatility model is mathematically verified for 168h realized variance under QLIKE loss, but directional GBDTs demonstrate out-of-sample AUCs between **0.504 and 0.5145** (statistically indistinguishable from a random coin flip). External models (e.g. `AMFORGE/tabicl-gold-btc-finetuned`) report high validation accuracy on retail CFD feeds, but carry severe security risks (pickle deserialization), context-encoder loss, and arbitrary 60-minute ATR barrier definitions that do not match our Coinbase Spot contract.
2. **Data Lineage Verdict (`PARTIALLY_VERIFIED`):**  
   The primary historical dataset (`data/raw/ohlcv.parquet`, 42,177 rows, SHA-256 `1e722f33...`) has perfect chronological continuity (0 gaps, 0 duplicates, 0 nulls), but its schema lacks row-level `symbol`, `venue`, and `quote_currency` identifiers. Historical repository notes indicate mixed heritage (`CCXT/Binance` historical archive merged with Coinbase backfills). While suitable for exploratory rule formulation, it is **gated and blocked for confirmatory economic authorization** until an independently signed exchange capture manifest is established.
3. **Runtime Route & Freshness Truth:**  
   The in-process FastAPI application (`TestClient`) successfully loads and executes `/api/research/smart-entry/pipeline` and `/latest`. The running background server (PID 25648 on port 8000) returns 404 because it was booted prior to route registration. Per strict operating instructions, the live daemon was left untouched. When queried with default historical data, the pipeline strictly and correctly fails closed with `STALE_DATA` (>26h age exceeds the 2h tolerance).
4. **Hard Governance Locks Maintained:**  
   `LIVE_TRADING_ENABLED = False` permanently; `META_MODEL_UNAVAILABLE` remains active; **zero positive-edge research alerts are emitted**.

---

## 1. Specialist Workstream Findings (Agents A–F)

### Agent A — Repository & Runtime Forensics
- **Evidence Level:** `VERIFIED_IN_SOURCE` & `VERIFIED_BY_TEST`.
- **Working Tree State:** All existing user-modified and untracked files are preserved intact.
- **Pipeline Implementation:** All four pipeline modules ([`engine/data_verification.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/data_verification.py), [`engine/strategy_signal_engine.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/strategy_signal_engine.py), [`engine/trade_outcome_evaluator.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/trade_outcome_evaluator.py), [`engine/smart_entry_pipeline.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/smart_entry_pipeline.py)) are implemented, typed, and pass all 19 unit tests in 1.13s.
- **Process & Network Forensics:** Process PID 25648 is active on port 8000. It was not killed or restarted. Live HTTP GET `/api/health` returns `200 OK` (`live_trading_enabled: False`). Live HTTP GET `/api/research/smart-entry/pipeline/latest` returns `404 Not Found` due to pre-boot route table binding (`ACTIVE_SERVER_ROUTE_ABSENT`). In-process `TestClient` returns `200 OK` (`WORKING_TREE_ROUTE_PRESENT`).

### Agent B — Data Lineage & Market Contract
- **Evidence Level:** `VERIFIED_IN_SOURCE` & `CONFLICTING`.
- **Primary Hourly Dataset (`data/raw/ohlcv.parquet`):**
  - SHA-256: `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` (2,326,699 bytes).
  - Row Count: Exactly 42,177 contiguous hourly candles spanning `2022-01-01 00:00:00+00:00` to `2026-10-24 08:00:00+00:00`.
  - Continuity: `dt.is_monotonic_increasing == True`; duplicate timestamps = 0; gaps = 0.
  - Geometry: All prices strictly positive; high $\ge \max(\text{open}, \text{close})$; low $\le \min(\text{open}, \text{close})$.
  - Provenance Conflict: Column schema is `['timestamp', 'open', 'high', 'low', 'close', 'volume', 'available_time']`. No row-level venue/symbol metadata exists. Prior report [`application_necessity_and_accuracy_improvement_plan.md:128`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/application_necessity_and_accuracy_improvement_plan.md#L128) records `CCXT/Binance historical archive`, while [`data_audit_summary.json:5`](file:///c:/Projects/BTCognitive/BTCognitive/research/data_audit_summary.json#L5) labels it `Coinbase Spot`.
  - **Verdict:** `PARTIALLY_VERIFIED`. Source history is mixed; the dataset cannot be cryptographically proven as pure Coinbase Spot.
- **Secondary 15-Minute Dataset (`data/raw/coinbase_15m.parquet`):**
  - Verified by signed manifest [`coinbase_15m_manifest.json`](file:///c:/Projects/BTCognitive/BTCognitive/data/raw/coinbase_15m_manifest.json) (SHA-256 `016e7ac4...`, 13,200 bars, `2026-06-09` to `2026-10-24 18:15 UTC`). Authenticated Coinbase Exchange REST API. Distinct from the hourly parquet.

### Agent C — Strategy & Barrier Mathematics
- **Evidence Level:** `VERIFIED_IN_SOURCE` & `VERIFIED_BY_TEST`.
- **Primary Strategy Contract:** `TSMOM_DONCHIAN_24H_168H`.
  - Signal uses completed closed bars at $t$.
  - Trend filter: 168h EMA computed causally from closed bars.
  - Channel: 24h Donchian high/low over prior completed bars $[t-24, t-1]$ via `.shift(1)`, strictly excluding bar $t$.
  - Execution: Next-bar open ($t+1$).
  - Risk Units: $1R = |P_{\text{entry}} - P_{\text{stop}}| = 1.5 \sigma_P(24\text{h}) \cdot P_{\text{entry}}$. Target is $1.5R = 2.25 \sigma_P \cdot P_{\text{entry}}$.
  - Horizon: 24 hours (24 bars).
  - Short Restriction: Spot short-to-open candidates strictly map to `CASH` with reason code `SPOT_SHORT_INELIGIBLE`.
- **Barrier Resolution Contract ([`engine/trade_barrier_resolver.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/trade_barrier_resolver.py)):**
  - Conservative intrabar collision rule: simultaneous upper/lower touch in a single bar resolves as `SL_FIRST`.
  - Signed Timeout Return: $R_{\text{TO}} = s \cdot \frac{P_{\text{timeout}} - P_{\text{entry}}}{|P_{\text{entry}} - P_{\text{stop}}|}$.
  - Expected Net R Equation:
    $$EV_{\text{net}} = p_{\text{TP}}(k_{\text{tp}} - C_R) - p_{\text{SL}}(k_{\text{sl}} + C_R) + p_{\text{TO}}(\mathbb{E}[R_{\text{TO}} \mid \text{TIMEOUT}] - C_R)$$
    with $C_R = \frac{\text{friction\_bps} / 10000}{|P_{\text{entry}} - P_{\text{stop}}| / P_{\text{entry}}}$.

### Agent D — Model & Forecast Research
- **Evidence Level:** `VERIFIED_IN_SOURCE` & `AUTHOR_REPORTED`.
- **Directional GBDTs (`1h`, `4h`, `24h`):** LightGBM/GBDT return-sign classifiers. Expected training samples: 34,894 (`2022-01-08` to `2025-12-31`). Input features: `ret_1h, ret_4h, ret_24h, ret_168h`. Author-reported training accuracy: ~52.14%. Empirical holdout AUC: 0.504 to 0.5145. GBDT output $P(\text{UP})$ is attached as context only; strictly forbidden from being substituted for $p_{\text{TP}}$.
- **Volatility Model (`HAR-RS-DOW-v1.0`):** Realized variance risk model evaluated under QLIKE. Not a directional price or trade-outcome model.
- **`amazon/chronos-2`:** 120M encoder-only foundation model (`safetensors`, Apache-2.0). Suitable as an offline Stage 3 forecasting challenger for 24h forward quantile trajectories ($P_{10}, P_{50}, P_{90}$). Does not compute target-before-stop probabilities.
- **External Classifiers (`AMFORGE/tabicl-gold-btc-finetuned`, `maverick90024/btc-usd-consensus-1d`):** Rejected due to security (pickle deserialization), context-encoder loss (`NotFittedError` on load), GPL-3.0 licensing contagion, and horizon/asset mismatches.

### Agent E — Statistical Design & Meta-Labeling
- **Evidence Level:** `VERIFIED_IN_SOURCE`.
- **Missing Meta-Model Contract:** Must predict tri-state outcome $(p_{\text{TP}}, p_{\text{SL}}, p_{\text{TO}})$ with $p_{\text{TP}} + p_{\text{SL}} + p_{\text{TO}} = 1.0$.
- **Validation Protocol:** Purged, embargoed walk-forward cross-validation (24h purging to eliminate label overlap leakage). Separate out-of-fold calibration period (Platt scaling / isotonic).
- **Economic Acceptance Gate:** Calibrated $EV_{\text{net}} > 0$ and 95% confidence lower bound $> 0$ under 87 bps friction.

### Agent F — API, Alerting & UX
- **Evidence Level:** `VERIFIED_BY_TEST` & `VERIFIED_BY_LOCAL_API`.
- **Pipeline Endpoints:** `@router.post("/smart-entry/pipeline")` and `@router.get("/smart-entry/pipeline/latest")`.
- **Alert Semantics:** Title = `"Potential positive-edge research signal"`; Disclaimer = `"Research only — no order placed; not a guarantee of profit."`
- **Deduplication:** SHA-256 hash of `(strategy_id, instrument, side, decision_timestamp, model_version)`.
- **Current State:** 0 alerts emitted (`alert_emitted: false`).

---

## 2. Actual Implementation Map

| Path | Symbol / Component | Stage | Status | Evidence Classification |
| :--- | :--- | :--- | :--- | :--- |
| [`engine/data_verification.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/data_verification.py) | `DataContractValidator` | Stage 1 | `IMPLEMENTED` | `VERIFIED_IN_SOURCE` & `VERIFIED_BY_TEST` |
| [`engine/strategy_signal_engine.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/strategy_signal_engine.py) | `StrategySignalEngine` | Stage 2 | `IMPLEMENTED` | `VERIFIED_IN_SOURCE` & `VERIFIED_BY_TEST` |
| [`engine/directional_forecast_service.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/directional_forecast_service.py) | `compute_directional_gbdt_forecast` | Stage 3 | `IMPLEMENTED` | `VERIFIED_IN_SOURCE` & `VERIFIED_BY_TEST` |
| [`engine/trade_outcome_evaluator.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/trade_outcome_evaluator.py) | `TradeOutcomeEvaluator` | Stage 4 | `IMPLEMENTED (FAIL-CLOSED)` | `VERIFIED_IN_SOURCE` & `VERIFIED_BY_TEST` |
| [`engine/smart_entry_pipeline.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/smart_entry_pipeline.py) | `SmartEntryPipeline` | Stage 5 & 6 | `IMPLEMENTED` | `VERIFIED_IN_SOURCE` & `VERIFIED_BY_TEST` |
| [`api/routes_research.py`](file:///c:/Projects/BTCognitive/BTCognitive/api/routes_research.py) | `execute_smart_entry_pipeline` | API | `IMPLEMENTED` | `VERIFIED_BY_LOCAL_API` (TestClient) |
| Active Daemon (Port 8000) | Live HTTP Listener | Deployment | `STALE_IN_MEMORY_ROUTE` | `VERIFIED_BY_LOCAL_API` (404 on live listener) |

---

## 3. Data Lineage & Provenance Ledger

| Dataset Path | SHA-256 Hash | Size | Rows | Monotonic | Gaps | Provenance Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | 2.32 MB | 42,177 | YES | 0 | **`PARTIALLY_VERIFIED`** (Missing row-level venue metadata; mixed CCXT/Binance vs Coinbase history) |
| `data/raw/coinbase_15m.parquet` | `016e7ac4c0a4a78b4599184e3b4b1604019b6e1bbe64fd7683d95a87bfef12cf` | 678 KB | 13,200 | YES | 0 | **`AUTHENTICATED`** (Verified by signed JSON manifest from Coinbase API) |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | 2.28 MB | 40,902 | YES | 0 | **`PARTIALLY_VERIFIED`** (Pre-backfill baseline) |

### Quarantine & Eligibility Policy:
- **Exploratory Research Allowed:** `data/raw/ohlcv.parquet` may be used for testing feature extraction logic, pipeline wiring, and synthetic unit tests.
- **Confirmatory Economic Evaluation Blocked:** Model training for production authorization and live alert issuance is **strictly blocked** until an authenticated Coinbase Spot hourly dataset is captured directly with signed cryptographic timestamps.

---

## 4. Metric Discrepancy & Reconciliation Ledger

| Metric / Evaluation Report | Documented Finding | Root Cause / Reconciliation |
| :--- | :--- | :--- |
| **GBDT Training Accuracy (~52.14%)** | Reported in `directional_models_freeze_metadata.json` across 34,894 samples. | Training set accuracy on in-sample data. Slightly above 50% due to mild in-sample fitting. |
| **GBDT Holdout AUC (0.504 – 0.5145)** | Audited in `research/v32_17_empirical_remediation_and_first_passage_report.md`. | Out-of-sample evaluation on 2026 data. Proves directional predictive power is statistically indistinguishable from a random 50/50 coin flip ($p = 0.3184$). |
| **Barrier Strategy Hit Rate (18.61%)** | Audited in `v32_17` for fixed entry attempts. | Reflects unconditional probability of hitting a $2\sigma$ profit target before a $1\sigma$ stop loss under Bitcoin's negative-drift intraday regimes. |
| **Turnover Reduction Claims (60–80%)** | Found in early documentation drafts. | **Unsupported claim.** Removed from `README.md` as no reproducible backtest ledger established this figure. |

---

## 5. Protected Files Integrity Baseline

All 5 protected files were verified via SHA-256 before and after execution:

| Protected File Path | Exact SHA-256 Hash | Integrity Status |
| :--- | :--- | :--- |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **100% UNTOUCHED (BIT-IDENTICAL)** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **100% UNTOUCHED (BIT-IDENTICAL)** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **100% UNTOUCHED (BIT-IDENTICAL)** |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **100% UNTOUCHED (BIT-IDENTICAL)** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **100% UNTOUCHED (BIT-IDENTICAL)** |

---

## 6. Runtime & Test Verification Evidence

1. **Focused Test Suite:** `pytest tests/test_strategy_to_alert_pipeline.py -v`  
   **Result:** **19 passed in 1.13s** (0 errors, 0 warnings).
2. **Regression Suite:** `pytest tests/test_v32_25_directional_integration.py tests/test_entry_contracts_and_resolver.py tests/test_prospective_shadow_collector.py tests/test_shadow_feed_runner.py -v`  
   **Result:** **40 passed, 1 warning in 13.44s**.
3. **Frontend Checks:** `npm run check` and `npm run test`  
   **Result:** **100% PASSED** (steady-state polling budget verified at 29.5 req/min).
4. **FastAPI TestClient Execution:**  
   `POST /api/research/smart-entry/pipeline` returned `200 OK`, `final_action: ABSTAIN`, `primary_reason: STALE_DATA`.
5. **Live Process PID 25648:**  
   `GET http://127.0.0.1:8000/api/health` returned `200 OK`. `GET http://127.0.0.1:8000/api/research/smart-entry/pipeline/latest` returned `404` (stale in-memory route table from pre-boot state). Service was preserved without restart.

---

## 7. Residual Blockers & Next Separately Authorized Phase

| Blocker ID | Description | Governing Action Required |
| :--- | :--- | :--- |
| **BLK-PROV-01** | `data/raw/ohlcv.parquet` lacks row-level venue metadata. | Acquire authenticated Coinbase Spot hourly dataset with cryptographic source manifest. |
| **BLK-META-01** | Missing trained, calibrated triple-barrier meta-model. | Execute Phase 4 training using `TradeBarrierResolver` ground-truth labels. |
| **BLK-SVC-01** | Running daemon PID 25648 runs older route table. | Execute user-controlled restart (`Stop-Process -Id 25648 -Force ; uvicorn api.server:app`). |

---

## 8. Independent Adversarial (Red-Team) Review

- **Reviewer:** Independent Skeptical Quant Auditor.
- **Adversarial Checks:**
  1. *Did any modified file violate protected datasets?* **NO.** All SHA-256 hashes matched.
  2. *Was any live trading enabled or order submitted?* **NO.** `LIVE_TRADING_ENABLED = False` confirmed in health endpoint and code.
  3. *Were any third-party pickle models loaded?* **NO.** `tabicl_finetuned.pkl` was inspected via text card only; never unpickled.
  4. *Did the pipeline emit any positive-edge alerts?* **NO.** Strictly 0 alerts emitted; all setups fail closed with `META_MODEL_UNAVAILABLE` or `STALE_DATA`.
  5. *Were 24h and 72h horizons mixed?* **NO.** Primary strategy strictly locked to 24h; 72h exploratory candidate triggers `HORIZON_MISMATCH`.
  6. *Is any old holdout mislabeled as untouched confirmatory evidence?* **NO.** 2026 data is explicitly acknowledged as previously viewed development data; true confirmatory validation requires prospective accumulation.
- **Red-Team Verdict:** **PASS (ACCEPTED WITHOUT MODIFICATION)**.
