# 🏛️ Architecture Decision Record (ADR) — BTCognitive Probabilistic Forecasting & Market Intelligence

**Status:** APPROVED (Internal Scientific & Engineering Review)  
**Date:** 2026-10-14  
**Scope:** Live Market Ingestion, Feature Pipeline, Forecasting Ladder, Uncertainty Calibration, and Shadow Decision Engine  
**Preregistration ID:** `ADR-2026-BTCOGNITIVE-SOTA-01`

---

## 1. Context & Problem Statement

BTCognitive began as an exploratory research platform. Historical empirical studies established that:
1. **Directional Price Prediction on 24h Daily OHLCV is a 50.0% Coin Flip (AUC = 0.504)** as documented in `research/reports/metric_reconciliation_report.md`.
2. **Taker Execution Destroys Gross Statistical Edge (`COST_ERASED`)** as documented in `research/entry_tp_sl/PROMOTION_DECISION.md`.
3. **Volatility Risk-Envelopes (HAR-RS-DOW + C2 Conformal Calibration) Are Predictable (91.18% empirical coverage)** as documented in `experiments/results/uncertainty_04_final_report.md`.
4. **Production Model Inference Must Remain Fail-Closed (`BLOCKED_PROVENANCE_UNVERIFIED`)** until cryptographic input/context hashes and longitudinal clean evaluation blocks pass.

The objective is to evolve BTCognitive into a research-grade market-intelligence application that combines live market observations, research evidence, multi-horizon probabilistic forecasts, uncertainty calibration, and a research-only shadow decision engine without fabricating data or lowering governance gates.

---

## 2. Evaluation of Quantitative & ML Approaches

| Approach / Methodology | Evaluated Role | Data Frequency | Empirical Findings / Literature | Decision | Explicit Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Microstructure: Order Flow Imbalance (OFI) & Spread** | Feature Pipeline | Tick / 1-sec / 1-min | Cont et al. (2014), Cartea et al. (2018). Multi-level OFI explains contemporaneous and short-horizon price impact. | **ACCEPTED** | Proven physical order book dynamics. Directly available via Coinbase BTC-USD L2 feeds. |
| **Volume-Synchronized Probability of Toxicity (VPIN)** | Risk / Regime Feature | Volume-bucketed | Easley, López de Prado, O'Hara (2012). Quantifies adverse selection risk and liquidity withdrawal prior to cascades. | **ACCEPTED** | Effective volatility-expansion trigger; protects execution from adverse selection. |
| **Hawkes Point Processes** | Volatility Clustering | Event-level | Hawkes (1971), Bacry et al. (2015). Captures self-exciting jump arrivals in order book events. | **ACCEPTED (Challenger)** | Highly suitable for regime detection; already has foundational code in repo. |
| **HAR-RS-DOW Volatility Model** | Volatility Baseline | Hourly / Daily RV | Corsi (2009). Standard benchmark for realized volatility with Day-of-Week effects. | **ACCEPTED (Baseline B)** | Frozen artifact (`har_rs_dow_v1.joblib`) already validated in repo. Serves as reference standard. |
| **Naive Historical Benchmark** | Reference Baseline | 1h, 4h, 24h | Zero-return drift, 30-day rolling historical volatility. | **ACCEPTED (Baseline A)** | Mandatory reference standard; every model must beat Baseline A out-of-sample. |
| **Quantile Tree / Ridge Models (LightGBM/Ridge Quantile)** | Multi-Horizon Quantile | 1h, 4h, 24h | Koenker & Bassett (1978), Ke et al. (2017). Direct pinball loss minimization for P10, P50, P90. | **ACCEPTED (Challenger C)** | Low compute overhead, robust tabular handling, interpretable feature splits, no deep learning bloat. |
| **Temporal Fusion Transformer (TFT)** | Sequence Challenger | Multi-horizon hourly | Lim et al. (2021). Self-attention with variable selection networks across static, observed, and known inputs. | **ACCEPTED (Challenger D)** | Evaluated strictly against identical partitions as Challenger C. Kept modular. |
| **Pretrained Foundation Models (Chronos, Mamba-Time)** | Experimental Sequence | Hourly / Daily | Ansari et al. (2024), Gu & Dao (2023). Zero-shot time-series forecasting. | **REJECTED (Production)** | High dependency footprint, non-causal pretraining data leakage risks, unproven net-of-fee edge on BTC. |
| **Conformalized Quantile Regression (CQR)** | Uncertainty Calibration | Causally separated | Romano et al. (2019), Angelopoulos & Bates (2021). Finite-sample coverage guarantees under exchangeability. | **ACCEPTED** | Provides honest uncertainty bounds with empirical coverage and interval width tracking. |
| **Triple-Barrier Meta-Labeling** | Trade Sizing & Abstention | Event-driven | Marcos López de Prado (2018). Separates structural setup from binary bet-sizing decision. | **ACCEPTED** | Essential to prevent `COST_ERASED` outcomes; filters out trades where edge < fees. |

---

## 3. Data Ingestion Architecture & Contracts

1. **Spot Market:** Coinbase Exchange BTC-USD (Trades + Level 2 Order Book) with Bitstamp/Kraken failover.
   - Sequence checks on book updates; immediate cache invalidation and snapshot resynchronization on gap detection.
2. **Derivatives:** Binance Futures BTCUSDT Funding Rate and Open Interest isolated as distinct derivative series.
   - **Critical Rule:** Never mix derivative settlement indices with spot prices.
3. **Data Quality Contract:**
   - Every observation includes: `source`, `instrument`, `event_timestamp`, `receipt_timestamp`, `units`, `freshness_status`, `error_state`.
   - Never substitute missing feeds with fabricated numbers (e.g., hardcoded price fallbacks).

---

## 4. Phase-by-Phase Traceability Matrix

| Phase / Requirement | Current Implementation | Repository Evidence | Identified Defect | Planned Engineering Fix | Automated Regression Test |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase 0: Baseline & State** | Uvicorn running with routes | `junit_report.xml` (853 tests pass) | Background server was stale when running without reload | Verified baseline, backed up sqlite DBs, auto-reload configured | `tests/test_system_contracts.py` |
| **Phase 2: Research Results** | `api/routes_research.py` & `web/app.js` | 11 allowlisted reports with SHA256 | Prediction panel previously hid historical reports | Decoupled research catalog endpoint, 3-pillar banner | `tests/test_research_results_api.py` |
| **Phase 3: Evidence Reconciliation** | Contradictions banner in UI & API | `metric_reconciliation_report.md` | Legacy health report asserted HEALTHY despite blocked runtime | Flagged with `CONFLICT_REQUIRES_RECONCILIATION` and `COST_ERASED` | `tests/test_research_results_api.py` |
| **Phase 4: Market Ingestion** | `engine/data_engine.py` | Line 112 has fallback 68000.0 | Synthetic fallback violates data contract | Remove synthetic numbers; implement fail-closed Coinbase L2 & Binance funding/OI contracts | `tests/test_data_contracts.py` |
| **Phase 5: PIT Feature Pipeline** | `engine/feature_pipeline.py` | 32 features computed | Lack of temporal perturbation test proving zero lookahead | Implement causal train-fold scaling and time-lag assertion tests | `tests/test_point_in_time_features.py` |
| **Phase 6: Forecasting Ladder** | `engine/range_forecast_service.py` | MFE/MAE quantiles generated | Naive Baseline A and Quantile Tree Challenger C not formally pitted | Build structured ladder: Baseline A (Naive), B (HAR-RS), C (Quantile Regressor), D (TFT) | `tests/test_forecasting_ladder.py` |
| **Phase 7: Calibration** | `engine/uncertainty_service.py` | P10, P50, P90 range boundaries | Coverage not reported alongside interval width | Compute empirical coverage, Winkler score, and horizon-specific calibration | `tests/test_uncertainty_calibration.py` |
| **Phase 8 & 9: Shadow Engine** | `engine/observatory.py` | SQLite WAL persistence | Shadow forecasts not filtered by net-of-fee economic hurdle | Record immutable t0 forecasts with fee hurdle check and explicit abstention states | `tests/test_shadow_mode_decision.py` |
| **Phase 10: Unified UI** | `web/app.js` | React SPA with navigation | Live vs Archived vs Experimental vs Production needs clear tabs | Add Forecast Lab & Data Health views while preserving blocked production gate | `tests/test_frontend_contracts.py` |
