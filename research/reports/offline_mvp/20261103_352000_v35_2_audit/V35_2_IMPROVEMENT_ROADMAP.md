# BTCognitive Milestone V35.2 — Prioritized Improvement & Remediation Roadmap

**Document ID:** `V35_2_IMPROVEMENT_ROADMAP.md`  
**Date:** 2026-11-03  
**Lead Author:** Senior Engineering Manager & Quantitative Research Lead  
**Governing Standard:** BTCognitive Permanent Operating Contract (AGENTS.md)  
**Target Milestone for Implementation:** V35.3 (Immediate Critical Repairs) & V35.4 (Econometric Enhancements)  

---

## 1. Executive Summary

Milestone V35.2 conducted the most exhaustive, multi-agent adversarial audit in BTCognitive's history. Across 8 specialist workstreams and 24 evaluated acceptance criteria, the system proved resilient in its core mission: **the unprofitable HTF breakout strategy is irreversibly retired, live broker execution is strictly severed, and historical Bitstamp data ingestion is causal and point-in-time**.

However, the audit uncovered **14 verified defects** (3 Critical, 4 High, 4 Medium, 3 Low) that prevent unconditional production release under the governed status `RESEARCH_INTELLIGENCE_RELEASE_READY`. Most notably:
1. The presentation layer secretly substitutes hardcoded synthetic numbers when backend risk envelopes are unavailable (`web/app.js`).
2. The V35.1 release verification claimed 100% test passing by selectively running only 12 test files while omitting 350 test files in `tests/`.
3. Bitstamp API outages trigger a silent fallback to legacy Coinbase historical data rather than failing closed.
4. The Diebold–Mariano test in `engine/price_forecast_engine.py` omits the Bartlett triangular kernel, risking negative long-run variance.

This Roadmap establishes the authoritative, phased remediation plan to systematically resolve every defect and transition BTCognitive to full epistemic and architectural compliance.

---

## 2. Master Defect & Action Priority Matrix

| Defect ID | Severity | Component | Issue Description | Target Milestone | Remediation Owner |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **C-01** | **CRITICAL** | `web/app.js:6511–6598` | Hardcoded synthetic metrics (`livePrice * 1.008`, `0.0553`, `N_eff=133`) rendered when backend returns null. | **V35.3** | Frontend Lead |
| **C-02** | **CRITICAL** | `tests/` & Release Gate | 96.7% test suite omission disguised as full regression in V35.1 report; row-count assertion failures in legacy tests. | **V35.3** | QA & Test Lead |
| **C-03** | **CRITICAL** | `api/routes_tournament.py:636` | Silent fallback to legacy Coinbase parquet (`data/raw/ohlcv.parquet`) upon Bitstamp fetch failure. | **V35.3** | API & Data Lead |
| **H-01** | **HIGH** | `models/authoritative_model_registry.py` | Registry lists `HAR-RS-DOW-v1.0` as active production model; Corsi Standard HAR missing from Python registry. | **V35.3** | Model Governance Lead |
| **H-02** | **HIGH** | `engine/price_forecast_engine.py:76–86` | Diebold–Mariano HLN test omits Bartlett triangular weighting kernel; default `h=1` skips serial correlation. | **V35.3** | Quantitative Researcher |
| **H-03** | **HIGH** | `engine/range_forecast_service.py` & `uncertainty_service.py` | Synthetic multiplier ratios cancel out, forcing mathematically invariant `HIGH` confidence and `88.67%` coverage. | **V35.3** | Risk & Uncertainty Lead |
| **H-04** | **HIGH** | `engine/decoupled_analysis_engine.py:193` | Divergence between documented reason code (`C2_CALIBRATION_UNAVAILABLE`) and code (`UNVERIFIED_SOURCE_CALIBRATION`). | **V35.3** | API Contract Lead |
| **M-01** | **MEDIUM** | `engine/regime_strategy_tournament.py:152` | Parkinson volatility calculation returns raw per-candle hourly volatility while docs claim $\sqrt{8760}$ annualization. | **V35.4** | Quantitative Researcher |
| **M-02** | **MEDIUM** | `models/risk_metrics.py:31` & `paper_research_simulator.py` | Default `periods_per_year=365` under-annualizes hourly Sharpe by $\sqrt{24} \approx 4.9\times$; Calmar uses daily factor. | **V35.4** | Risk & Performance Lead |
| **M-03** | **MEDIUM** | `engine/data_verification.py:51` & `api/routes_tournament.py` | `SUPPORTED_VENUES` lacks `BITSTAMP`; paper entry endpoint rejects Bitstamp provenance with HTTP 409. | **V35.4** | Platform Integration Lead |
| **M-04** | **MEDIUM** | `engine/regime_strategy_tournament.py:210` | EMA200 warmup with 168 bars carries $\sim 18.7\%$ initial seed price bias into regime boundary classification. | **V35.4** | Regime Intelligence Lead |
| **L-01** | **LOW** | `engine/range_forecast_service.py:220` | Dead code: condition `current_price <= current_price * (1 - mae)` is mathematically impossible for positive values. | **V35.5** | Core Maintenance |
| **L-02** | **LOW** | `api/candle_manager.py:150` | Stray Binance symbol `BTCUSDT` emitted in WebSocket tick events instead of Bitstamp `BTC/USD`. | **V35.5** | API Maintenance |
| **L-03** | **LOW** | `tests/test_v33_7_bitstamp_integration.py` | Real-clock `time.time()` comparison in unit tests causes artificial test failure as on-demand parquet cache ages. | **V35.5** | QA Maintenance |

---

## 3. Phased Remediation Program

```mermaid
flowchart TD
    subgraph Phase 1: Milestone V35.3 - Critical & High Integrity Fixes
        C01[C-01: Remove Frontend Synthetic Fallbacks]
        C02[C-02: Transparent Test Suite Partitioning]
        C03[C-03: Eliminate Silent Coinbase Fallback]
        H01[H-01: Synchronize Authoritative Model Registry]
        H02[H-02: Implement Bartlett Kernel in DM-HLN]
        H03[H-03: Remove Static Conformal Multipliers]
        H04[H-04: Harmonize C2 Reason Code API Contract]
    end

    subgraph Phase 2: Milestone V35.4 - Econometrics & High-Frequency Ingestion
        M01[M-01: Reconcile Parkinson Annualization]
        M02[M-02: Correct Sharpe/Calmar Annualization]
        M03[M-03: Extend Paper Entry to Bitstamp]
        M04[M-04: Expand EMA200 Warmup Window]
        DATA[Ingest Tardis 5m Candles for Microstructure Proxies]
        CONF[Block-Dependent Conformal Horizon Calibration]
    end

    subgraph Phase 3: Milestone V35.5 - Architecture Consolidation & Cleanup
        L01[L-01: Purge Dead Branch in Range Forecast]
        L02[L-02: Align WebSocket Symbol to BTC/USD]
        L03[L-03: Replace Wall-Clock Unit Test Assertions]
        ARCH[Decommission Shadowed /api/market/candles]
        UI[Remove Deprecated Legacy Trading Widgets]
    end

    Phase 1 --> Phase 2 --> Phase 3
```

---

## 4. Detailed Specification of Remediation Tasks

### Milestone V35.3 — Immediate Critical & High Repairs (Release Blocking)

#### Task 35.3.1: Frontend Synthetic Metric Purge (`web/app.js`)
- **Objective:** Ensure the browser UI strictly complies with Prime Directive §2.5 (No Synthetic Fabrication).
- **Implementation:**
  - Remove fallback calculations: `(livePrice * 1.008)`, `(livePrice * 0.993)`, `0.0553`, `0.0911`, `drag_bps || 9.3`, and `n_eff || 133`.
  - When backend properties (`conformal_p90`, `finite_horizon_touch`, `n_eff`) are `null` or `undefined`, display clean textual placeholders: `"—"` or `"UNAVAILABLE"`.
  - Add explicit visual indicator: `"C2 Conformal Bounds: Suppressed for Safety (Calibration Source Mismatch)"`.

#### Task 35.3.2: Regression Test Suite Tiering & Assertion Fixes
- **Objective:** Establish transparent, reproducible regression execution without masking test failures.
- **Implementation:**
  - Partition the 362 test files in `tests/` into three governed pytest markers:
    1. `@pytest.mark.smoke`: Fast critical integration path (Bitstamp retrieval, analysis E2E, non-execution locks, ~30 tests).
    2. `@pytest.mark.regression`: Full active suite covering all live modules (~200 tests).
    3. `@pytest.mark.historical`: Legacy archive suites covering prior Coinbase iterations (clearly separated from current Bitstamp release gates).
  - Update `test_experiment_integrity_v4.py` to accept the actual multi-year dataset row counts rather than failing on hardcoded legacy numbers.
  - Require future release reports to publish exact pytest marker commands, total test counts, and explicitly distinguish smoke passes from full regression runs.

#### Task 35.3.3: Strict Fail-Closed Provider Fallback (`api/routes_tournament.py`)
- **Objective:** Enforce complete single-exchange data isolation.
- **Implementation:**
  - In `api/routes_tournament.py:630–638`, delete `df_1h = _load_historical_1h_bars()`.
  - If Bitstamp on-demand retrieval fails and client candles are missing, immediately raise `HTTPException(status_code=503, detail="Bitstamp market data unavailable. Cross-exchange fallback is prohibited.")`.
  - Under no circumstances should legacy Coinbase parquet (`data/raw/ohlcv.parquet`) be served during a Bitstamp analysis request.

#### Task 35.3.4: Authoritative Model Registry Alignment (`models/authoritative_model_registry.py`)
- **Objective:** Align runtime Python code with published governance determinations.
- **Implementation:**
  - Register `Standard-HAR-v1.0` (Corsi 2009 Log-HAR) as the active baseline:
    ```python
    ACTIVE_BASELINE_MODEL = ModelIdentityRecord(
        canonical_id="Standard-HAR-v1.0",
        version="1.0.0",
        display_name="Corsi (2009) Standard Log-HAR Realized Variance Baseline",
        classification=ModelClassification.BASELINE_VOLATILITY,
        authorization_status=AuthorizationStatus.OFFLINE_RESEARCH_ONLY,
    )
    ```
  - Demote `HAR-RS-DOW-v1.0` to `RESEARCH_CHALLENGER_UNPROMOTED` ($p_{\text{adj}} = 0.2632$).
  - Update `engine/decoupled_analysis_engine.py` labels to cite Standard Log-HAR.

#### Task 35.3.5: Bartlett Kernel Implementation in Diebold–Mariano Test (`engine/price_forecast_engine.py`)
- **Objective:** Guarantee positive semi-definite long-run variance estimation under temporal dependence.
- **Implementation:**
  - Update `diebold_mariano_test()` in `engine/price_forecast_engine.py`:
    ```python
    gamma_0 = float(np.var(d, ddof=0))
    gamma_sum = 0.0
    for lag in range(1, h):
        if lag < T:
            weight = 1.0 - (float(lag) / float(h))  # Bartlett triangular kernel
            gamma_lag = float(np.mean((d[lag:] - d_bar) * (d[:-lag] - d_bar)))
            gamma_sum += 2.0 * weight * gamma_lag
    var_d = (gamma_0 + gamma_sum) / float(T)
    ```
  - Enforce explicit horizon parameter checking: warn or raise if $h \le 1$ is used for overlapping multi-period forecasts.

#### Task 35.3.6: Harmonize C2 Reason Codes
- **Objective:** Eliminate contract mismatch between backend error codes and API documentation.
- **Implementation:**
  - Standardize on `C2_CALIBRATION_UNAVAILABLE` across `engine/decoupled_analysis_engine.py`, `tests/test_v33_7_bitstamp_integration.py`, and API route documentation.

---

### Milestone V35.4 — Quantitative Econometrics & Data Architecture

#### Task 35.4.1: High-Frequency Microstructure Volatility Ingestion (Tardis 5m)
- **Objective:** Resolve the volatility proxy measurement limitation identified in `V35_2_DATA_AND_VOLATILITY_AUDIT.md`.
- **Implementation:**
  - Build upon the verified `TardisSampleParser` (`tests/test_v35_tardis_sample_parser.py`) to ingest trade ticks and aggregate into clean 5-minute candles.
  - Implement 5-minute realized variance ($RV_{5m}$) as the authoritative target proxy for short horizons (1-hour and 4-hour volatility).
  - Benchmark Hansen & Lunde (2006) and Lin & Ghasempour (2026) variance proxies across 5-minute vs 1-hour sampling.

#### Task 35.4.2: Standardized Annualization Scaling Library
- **Objective:** Eliminate conflicting annualization factors across the entire repository.
- **Implementation:**
  - Update `models/risk_metrics.py`:
    - Define explicit crypto constants: `HOURS_PER_YEAR = 8760`, `DAYS_PER_YEAR = 365`.
    - Refactor `sharpe_ratio()` and `calmar_ratio()` to require explicit frequency indicators (`freq="1h"` or `freq="1d"`) rather than defaulting to daily 365 on hourly data.
  - Update `compute_parkinson_volatility()` in `engine/regime_strategy_tournament.py` to clearly parameterize `annualize: bool = False`.

#### Task 35.4.3: Conformal Prediction Research for Long-Memory Time Series
- **Objective:** Address the 168-hour feedback maturity barrier that renders online adaptive conformal prediction ineffective during regime shifts.
- **Implementation:**
  - Formulate block-dependent conformal inference based on Zhai, Cheng & Wu (2026) using functional dependence metrics (FDM).
  - Test offline historical regime-stratified calibration: calibrate separate conformal non-conformity quantiles per regime state rather than attempting real-time sequential updating.

---

### Milestone V35.5 — Architectural Cleanup & Terminal Consolidation

#### Task 35.5.1: API Route De-Duplication & Shadow Route Removal
- **Objective:** Streamline the REST API surface and eliminate redundant endpoints.
- **Implementation:**
  - Decommission the shadowed route `@router.get("/candles")` in `api/routes_tournament.py` in favor of the canonical `@router.get("/api/market/candles")` in `api/routes_market.py`.
  - Harmonize WebSocket tick symbol in `api/candle_manager.py` to `BTC/USD`.

#### Task 35.5.2: Frontend Terminal Consolidation
- **Objective:** Complete the transition from a trade-execution interface to a dedicated Market Risk Intelligence Terminal.
- **Implementation:**
  - Remove dead UI components: `QuickExecutionTicket`, manual order forms, and legacy slippage calculators that no longer serve an active operational function.
  - Focus the dashboard on 4 primary analytical views:
    1. Realized Volatility Term Structure & Historical Regime Dynamics.
    2. Model Lineage & Authoritative Baseline Benchmarks.
    3. Excursion Distributions & Downside Tail Risk Bounds.
    4. Causal Provenance & Data Quality Health Observatory.

---

## 5. Verification Gates for Roadmap Completion

To achieve sign-off for Milestone V35.3 and beyond, every task must pass the following verifiable gates:

1. **DOM Inspection Gate:** Browser automated testing must verify that zero synthetic fallback values exist in the rendered DOM when backend endpoints return `null`.
2. **Fail-Closed Provider Gate:** Simulated network failure on the Bitstamp endpoint must return HTTP 503 without loading or referencing any Coinbase file.
3. **Registry Assertion Gate:** Automated unit test asserting `get_active_production_model().canonical_id == "Standard-HAR-v1.0"` and `authorization_status == OFFLINE_RESEARCH_ONLY`.
4. **Kernel Test Gate:** Mathematical test verifying that `diebold_mariano_test()` computes non-negative long-run variances across intentionally collinear test series.
5. **Full Regression Transparency:** Release report containing the complete execution log of all 362 test files, with pass/fail/skip counts explicitly documented.

---
**Roadmap Approved:**  
*Senior Engineering Manager & Quantitative Research Lead*  
*BTCognitive Milestone V35.2 Audit Framework.*

