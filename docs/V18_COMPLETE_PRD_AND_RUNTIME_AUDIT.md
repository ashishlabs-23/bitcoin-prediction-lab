# BTCognitive V18 — Complete PRD & Runtime Reconciliation Audit

**Document Version:** 1.0.0  
**Audit Epoch:** V18.0.0 (October 2026)  
**Classification:** Research Governance, Epistemic Reconciliation & Disabled-State Verification  
**Repository State:** Local clone at `C:\Projects\BTCognitive\BTCognitive`, origin `main` at `01f87ca` with V7–V17 additions  
**Authoritative Product Mandate:**  
> **BTCognitive is a BTCUSD market-analysis, future-price forecasting and quantitative research application. It is not a trading application.**  
> Live trading, broker order submission, trade-placement controls, paper-order workflow as a product feature, synthetic market signals, and fabricated consensus are strictly disabled at the backend and frontend boundaries.

---

## 1. Executive Summary & Audit Mandate

The V18 audit conducts an exhaustive, whole-history reconciliation of BTCognitive across all requirement artifacts:
- Original Master PRD (`BTCognitive_Master_PRD.md`)
- Master PRD v2 Continuation (`BTCognitive_Master_PRD_v2_Continuation.md`)
- V12–V17 Amendments (`BTCognitive_PRD_Amendment_V12.md`, `V13.md`, `V14.md`, `V15.md`, `V17.md`)
- PRD Traceability Matrix (`BTCognitive_PRD_Traceability_Matrix.md`)
- Historical research reports, challenger bake-offs, trial census registries, and model governance records.

### Key Audit Findings

1. **Strict Analysis-Only Boundary Enforced:**
   - Previous revisions left legacy execution endpoints (`POST /api/arena/trade`, `POST /api/arena/paper-trades`, `POST /api/arena/paper-trades/close`) that accepted simulated or paper orders.
   - In V18, all trade-submission endpoints are permanently disabled at the FastAPI router boundary with HTTP 200/403 typed responses (`status: DISABLED`).
   - The frontend QuickExecutionTicket simulation button has been permanently locked to `🚫 ANALYSIS ONLY · ORDER EXECUTION DISABLED`.

2. **Elimination of Analytical Decisions & Read-Side Mutations:**
   - In `api/routes_arena.py`, `GET /api/arena/context` previously called `arena_runner.record_arena_decision_context(...)`, mutating the database on read requests. Furthermore, missing strategy data defaulted to `["SKIP", "LONG", "SKIP", "SKIP"]` and synthesized a `LONG` consensus.
   - In V18, read-side ledger mutations are purged from GET endpoints, and missing inputs yield typed unavailable states (`consensus: NO_CONSENSUS`, `actions: []`) rather than fabricated actions.

3. **Trial Census Duplication Reconciled:**
   - Investigation into `experiments/results/test_census.json` revealed that all 29 trial entries shared the identical trial hash `8478f66327374931` (repeated execution retries on the same configuration).
   - Reconciled artifact `experiments/results/test_census_reconciled.json` establishes the true count of 1 unique configuration, preventing inflated trial counts from distorting multiple-testing corrections.

4. **Historical Evidence Conflict Reconciled:**
   - Reconciled the historical contradiction between 90.32% vs 75.8% vs 69.7% path containment figures across August 2026 reports.

---

## 2. Investigation of Historical Evidence Contradictions

### 2.1 The 90.32% vs 75.8% vs 69.7% Path Containment Conflict

| Document / Artifact | Dataset / Window | Sample Size | Reported Metric | Underlying Ground Truth | Audit Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `results/production_lock.json` | Aug 1 – Aug 31, 2026 (Retrospective) | 31 blocks (24h) | 90.32% (28/31) Joint Path Containment | Exact empirical count: 28/31 = 90.3225% | **CONFIRMED FOR 31-BLOCK RETROSPECTIVE WINDOW** |
| `research/challenger_bakeoff_report.md` | Aug 1 – Sep 3, 2026 (Walk-forward) | 33 blocks (24h) | 90.32% Joint Containment, 0.4120% QLIKE | Copy-paste error from 31-block table over 33-block table | **IDENTIFIED DEFECT: INCORRECT TABLE TRANSCRIPTION** |
| `research/baseline_challenge_report.md` | Aug 1 – Sep 3, 2026 (Walk-forward) | 33 blocks (24h) | 69.7% Joint (23/33), 75.8% MFE P90 (25/33) | Exact empirical count: 23/33 = 69.697%, 25/33 = 75.757% | **CONFIRMED FOR 33-BLOCK WALK-FORWARD WINDOW** |
| Target Claim: "Target 78.87% (Achieved)" | N/A | N/A | Claimed 69.7% achieved target of 78.87% | Numerical contradiction: 69.7% < 78.87% | **IDENTIFIED DEFECT: FALSE CLAIM OF TARGET ACHIEVEMENT** |

#### Root Cause Analysis:
1. In `baseline_challenge_report.md` line 13: The report claimed `"Target 78.87% (Achieved)"` while reporting actual joint containment of `69.70% (23/33 blocks)`. An achievement claim when actual (69.7%) is below hurdle (78.87%) is mathematically invalid.
2. In `challenger_bakeoff_report.md` Section 2: The author copied the 31-block retrospective metric table (90.32% containment, 0.4120% QLIKE) into the 33-block comparison section, creating an irreconcilable conflict with the 33-block empirical test logs.
3. **Resolution:** The canonical ground truth is frozen:
   - 31-block retrospective window: 90.32% joint containment.
   - 33-block walk-forward test: 69.70% joint containment, 75.76% MFE P90 coverage.
   - Target 78.87% was **NOT** achieved in the 33-block walk-forward challenge. The model correctly failed the promotion gate and was retained under `OFFLINE_RESEARCH_ONLY`.

### 2.2 Trial Census Hash Duplication (`test_census.json`)

- **Observation:** `experiments/results/test_census.json` contained 29 entries, all reporting identical trial hash `8478f66327374931`.
- **Investigation:** Each entry ran identical hyperparameters (`learning_rate: 0.01`, `batch_size: 32`, `lookback: 168`) with varying execution timestamps between August 28 and August 30, 2026.
- **Correction:** A census of 29 trials would imply a Bonferroni or Holm-Bonferroni correction factor of 29, artificially penalizing significance testing. The reconciled registry (`test_census_reconciled.json`) records `unique_parameter_sets: 1`, `execution_instances: 29`, with `authoritative_trial_count: 1`.

---

## 3. End-to-End Requirement Census & Verification Status

### Phase 1 — Market Data & Causal Ingestion (PRD-DATA)
- `PRD-DATA-01`: Causal Point-in-Time Data Boundaries ($t_{\text{feature}} \le t_{\text{issue}} < t_{\text{maturity}}$). **STATUS: IMPLEMENTED & VERIFIED**. Enforced in `data/feature_cache.py` and `engine/price_forecast_engine.py`.
- `PRD-DATA-02`: Primary Coinbase Spot BTC-USD Feed. **STATUS: IMPLEMENTED & VERIFIED**. Validated via WebSocket and REST adapters.
- `PRD-DATA-03`: Synthetic Data Prohibition. **STATUS: IMPLEMENTED & VERIFIED**. When inputs fail or are missing, typed `DATA_UNAVAILABLE` states are returned without synthetic imputation.

### Phase 2 — Volatility & Risk Modeling (PRD-VOL)
- `PRD-VOL-01`: HAR-RS-DOW 168h Variance Target (`rv7d_var_ann`). **STATUS: IMPLEMENTED & VERIFIED**. Confirmed in `models/har_rs_dow_v1.joblib` and `models/authoritative_model_registry.py`.
- `PRD-VOL-02`: Epistemic Target Separation. **STATUS: IMPLEMENTED & VERIFIED**. Volatility models are strictly separated from price forecasting. HAR-RS-DOW is classified as a volatility risk model, not a directional predictor.
- `PRD-VOL-03`: Realized Variance 24h Proxy (`rv24h_var_ann`). **STATUS: IMPLEMENTED & VERIFIED**. Evaluated as a separate hourly-sampled risk target.

### Phase 3 — Genuine Future-Price Forecasting (PRD-PRICE)
- `PRD-PRICE-01`: Point Forecasts at 1h, 4h, 24h. **STATUS: IMPLEMENTED & VERIFIED**. Implemented in `engine/price_forecast_engine.py` and served via `/api/prediction/price/forecast`.
- `PRD-PRICE-02`: Persistence / Random Walk Benchmark. **STATUS: IMPLEMENTED & VERIFIED**. Point prediction $\hat{P}_{t+h} = P_t$ serves as the mandatory, unbeaten reference benchmark.
- `PRD-PRICE-03`: Regularized L2 Linear Model (Ridge). **STATUS: IMPLEMENTED & VERIFIED**. CPU-feasible regressor on lagged causal returns ($r_{1h}, r_{4h}, r_{24h}, r_{168h}$).
- `PRD-PRICE-04`: Empirical Uncertainty Quantiles (P10, P50, P90). **STATUS: IMPLEMENTED & VERIFIED**. Evaluated across 30-day rolling empirical distributions.
- `PRD-PRICE-05`: Diebold-Mariano with Harvey-Leybourne-Newbold (1997) Correction. **STATUS: IMPLEMENTED & VERIFIED**. Evaluated on non-overlapping forecast origins against Student's $t_{T-1}$.

### Phase 4 — Strategy Research Tournament (PRD-STRAT)
- `PRD-STRAT-01`: Offline Hypothetical Backtest Simulations Only. **STATUS: IMPLEMENTED & VERIFIED**. Evaluated across 5 strategy families and 3 cost regimes in `research/run_v18_price_and_strategy_tournament.py`.
- `PRD-STRAT-02`: Realistic Fee Friction Drag. **STATUS: IMPLEMENTED & VERIFIED**. Confirmed that at 87 bps round-trip friction, all active strategies generate net negative returns (-2,779 to -36,159 bps).
- `PRD-STRAT-03`: Zero Trade Placement Side Effects. **STATUS: IMPLEMENTED & VERIFIED**. Strategy simulations do not alter market state or emit orders.

### Phase 5 — Analysis-Only Boundary & Disabled Gates (PRD-GATE)
- `PRD-GATE-01`: Live Trading Elimination. **STATUS: IMPLEMENTED & VERIFIED**. No broker order placement, credentials, or execution streams.
- `PRD-GATE-02`: Paper Order Workflow Elimination as Product Feature. **STATUS: IMPLEMENTED & VERIFIED**. `/api/arena/trade` and `/api/arena/paper-trades` disabled with typed status.
- `PRD-GATE-03`: Elimination of Fabricated Defaults. **STATUS: IMPLEMENTED & VERIFIED**. No default `LONG` or hardcoded indicator fallbacks.
- `PRD-GATE-04`: Elimination of Read-Side Ledger Mutations. **STATUS: IMPLEMENTED & VERIFIED**. `GET /api/arena/context` causes zero database writes.

---

## 4. Governed Release Verdict

| Governance Gate | Status | Evidence / Artifact |
| :--- | :--- | :--- |
| **Research Experiment** | `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY` | Persistence baseline unbroken; Ridge challenger fails HLN significance at 1h/24h. |
| **Prospective Evidence** | `COLLECTING` | 6,042 prospective observations in ledger; awaiting 100 clean non-overlapping blocks. |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` | Production promotion blocked. Volatility model authorized for risk intelligence only. |
| **Live Trading** | `DISABLED` | Non-execution invariant verified across all API routes, HTTP methods, and UI components. |
| **Overall Release State** | **`V18_ANALYSIS_ONLY_AND_FORECAST_RESEARCH_VERIFIED_WITHIN_SCOPE`** | All audit reconciliation, engine hardening, and UI verification requirements fulfilled. |
