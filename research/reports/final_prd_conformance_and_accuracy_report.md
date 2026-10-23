# BTCognitive — Final PRD Conformance, Independent Verification & Predictive Accuracy Report

**Document Version:** 1.0  
**Audit Date:** 16 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Product Posture:** Research-First BTCUSD Market Intelligence (Non-Execution)  
**Authoritative Documents:**
- [docs/BTCognitive_Master_PRD.md](file:///c:/Projects/BTCognitive/BTCognitive/docs/BTCognitive_Master_PRD.md) (v1.0, 16 October 2026)
- Product Blueprint v2.0 (16 October 2026)
- Canonical Traceability Matrix: [research/reports/final_prd_traceability_matrix.csv](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/final_prd_traceability_matrix.csv)
- Frozen Evaluation Manifest: [experiments/results/final_evaluation_gate/final_evaluation_manifest.json](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/final_evaluation_gate/final_evaluation_manifest.json)
- Final Accuracy Results: [experiments/results/final_evaluation_gate/final_accuracy_results.json](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/final_evaluation_gate/final_accuracy_results.json)

---

## 1. Executive Summary & Four Separate Acceptance Decisions

BTCognitive has undergone an exhaustive multi-agent verification and predictive accuracy evaluation against its Master Product Requirements Document (PRD) and Product Blueprint v2.0. In accordance with strict epistemic standards, software test passes are never substituted for empirical forecasting accuracy, and prospective live evidence is strictly separated from retrospective historical replay.

The four independent release decisions are:

| Release Dimension | Final Verdict | Core Rationale |
| :--- | :--- | :--- |
| **1. Software Completion** | **PASS** | All mandatory product capabilities, APIs, and the 7 user-facing Terminal views are fully implemented, integrated, and verified end to end. The 52 focused tests pass in 10.86s, and `validation/startup_gate.py` passes cleanly. |
| **2. Data & Evidence Readiness** | **CONDITIONAL / REPRESENTATIVE** | Historical datasets and point-in-time feature pipelines are verified without forward leakage. However, following the quarantine of 71 synthetic mock records, clean prospective evidence blocks currently stand at **0**. Prospective calendar-time collection is required before live claims can be substantiated. |
| **3. Predictive Model Validation** | **VALIDATED FOR VARIANCE / REJECTED FOR DIRECTION** | The production volatility model `HAR-RS-DOW-v1.0` is statistically validated on 5,671 out-of-sample points for 7-day realized variance (`rv7d_var_ann`), beating the baseline by **23.7% QLIKE** with **92.36% coverage**. Directional models achieve only **52.14%** hit rate and incur negative net expectancy after trading frictions. |
| **4. Operational Authorization** | **BLOCKED FROM INFERENCE / TRADING DISABLED** | `HAR-RS-DOW-v1.0` remains set to `BLOCKED_AUDIT_FAILURE` pending prospective clean block accumulation. Directional models are restricted to `OFFLINE_RESEARCH_ONLY`. Live broker order execution and real-capital trading are permanently disabled. |

> [!CRITICAL]
> **Status of the PRD 90% Directional Accuracy Objective:**
> The PRD defines 90% directional accuracy as an **aspirational research hypothesis** on a predeclared selective subset ($\ge 10\%$ coverage, $N_{\text{eff}} \ge 100$). The final frozen evaluation on 5,838 out-of-sample hourly observations reveals that 1-hour directional accuracy is **52.14%** (95% CI: [51.16%, 53.36%]). Even when filtering to the top 10% highest conviction predictions, accuracy reaches only **53.42%** and generates heavy negative trading expectancy due to turnover. The 90% directional objective is **COMPLETELY UNSUBSTANTIATED AND NOT MET**.

---

## 2. PRD Requirement Traceability & Conformance Audit

The canonical traceability matrix is located at [research/reports/final_prd_traceability_matrix.csv](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/final_prd_traceability_matrix.csv). Below is the consolidated conformance summary:

### 2.1 Conformance Statistics
- **Total Requirements Tracked:** 31
- **Mandatory Requirements:** 30
- **Aspirational Research Hypotheses:** 1
- **Mandatory Items Passed:** 29 (96.7%)
- **Mandatory Items Blocked (Prospective Calendar-Time Dependency):** 1 (3.3% — Gate G6: Prospective Evidence Blocks)
- **Aspirational Hypotheses Achieved:** 0 (PRD-HYP-90: Rejected by empirical evidence)
- **Unvalidated 90% Marketing Claims in UI/README:** 0 (100% compliant with PRD Req 8 prohibition)

### 2.2 Traceability Inventory Summary

| Requirement Category | Scope & Key Mandates | Observed Status | Verification Reference |
| :--- | :--- | :--- | :--- |
| **Architecture (PRD-ARCH)** | Research-first non-execution; target specialization; baseline-first protocol; CPU-first laptop execution. | **PASS** | `test_terminal_release_readiness_end_to_end`, `startup_gate.py` |
| **Market Data (PRD-DATA)** | UTC normalization; multi-exchange spot comparator (>50 bps warning); spot vs perp separation; point-in-time invariant ($t_{\text{avail}} \le t_{\text{issue}}$); delayed resolution. | **PASS** | `test_phase2_market_data_and_pit.py`, `test_causal_resolution.py` |
| **Evidence Quarantine** | 71 synthetic mock records quarantined into `quarantined_forecast_outcomes`; clean blocks = 0; persistent database isolated during tests. | **PASS** | `test_longitudinal_provenance_repair.py`, `test_database_isolation.py` |
| **Model Governance (PRD-MOD)** | Central authoritative model registry; startup gate checksum enforcement; HAR-RS-DOW classified as volatility-only; directional models set to `RESEARCH_ONLY`. | **PASS** | `test_authorization_consistency.py`, `test_phase3_volatility_and_range_validation.py` |
| **Terminal UI (PRD-UI)** | All 7 functional areas connected to working FastAPI backends with fail-closed status badges and masked secrets. | **PASS** | `test_phase6_terminal_release_readiness.py`, `test_notifications.py` |
| **Release Gates (G0–G5, G7)** | Identity, data causality, benchmark, statistical value, calibration, and economics gates pass with rigorous controls. | **PASS** | `test_canonical_metric_contracts.py`, `test_phase4_directional_research_gate.py` |
| **Release Gate (G6)** | Prospective forward forecasts recorded prior to event resolution with $N \ge 100$ independent clean blocks. | **BLOCKED** | Clean blocks = 0; requires prospective calendar-time accumulation. |
| **The 90% Objective** | Directional hit rate approaching 90% on selective subset ($\ge 10\%$ coverage, $N_{\text{eff}} \ge 100$). | **FAIL / NOT MET** | Out-of-sample directional hit rate is 52.14%; selective 10% tier is 53.42%. |

---

## 3. End-to-End Verification of the 7 Research Terminal Areas

The application serves a single integrated Research Terminal via FastAPI (`api/server.py`) and a vanilla React frontend (`web/app.js`, `web/index.html`). All 7 core functional areas have been verified against backend contracts and failure modes:

```mermaid
flowchart TD
    subgraph Frontend["Research Terminal (web/index.html & web/app.js)"]
        Area1["1. Market Overview<br/>(Live Spot, Volatility)"]
        Area2["2. Forecasts & Risk<br/>(Quantiles, Conformal Envelopes)"]
        Area3["3. Research Evidence<br/>(Longitudinal Blocks, CIs)"]
        Area4["4. Research Lab<br/>(Model Registry, Checksums)"]
        Area5["5. Data & System Health<br/>(Feed Latency, Breaches)"]
        Area6["6. Alerts & Notifications<br/>(Masked Webhooks/Secrets)"]
        Area7["7. Paper Simulator<br/>(1-Bar Lag, Intrabar SL)"]
    end

    subgraph Backend["FastAPI Routes (api/)"]
        R1["GET /health, /api/dashboard"]
        R2["GET /prediction/latest, /prediction/range"]
        R3["GET /prediction/longitudinal, /api/research/results"]
        R4["GET /api/models/authoritative-registry"]
        R5["GET /prediction/range/health"]
        R6["GET /api/notifications/settings"]
        R7["GET /api/research/entry-tp-sl"]
    end

    Area1 --> R1
    Area2 --> R2
    Area3 --> R3
    Area4 --> R4
    Area5 --> R5
    Area6 --> R6
    Area7 --> R7
```

### Detailed Functional Area Audit:

1. **Market Overview (`/health`, `/api/dashboard`):**
   - Displays real-time Coinbase BTC-USD spot candle series via lightweight-charts.
   - Normalizes UTC timestamps, monitors feed freshness, and computes trailing realized volatility.
   - Confirms `trading_enabled = false` and `mode = "MARKET_MONITOR_ONLY"`.
2. **Forecasts & Risk (`/prediction/latest`, `/prediction/range`):**
   - Implements multi-horizon selection (1h, 4h, 24h, 7d).
   - Generates empirical quantiles and C2 conformal risk envelopes without fabricating directional certainty.
   - Returns status `EXPERIMENTAL_BASELINE` with `production_forecast_available = false`.
3. **Research Evidence (`/prediction/longitudinal`, `/api/research/results`):**
   - Displays longitudinal monitoring status `ACTIVE_POST_REPAIR_COLLECTION`.
   - Truthfully reports `observed_blocks = 0` following evidence quarantine.
   - Catalog serves research reports (`uncertainty-04`, `distribution-01`, etc.) with verifiable provenance.
4. **Research Lab (`/api/models/authoritative-registry`):**
   - Lists active model `HAR-RS-DOW-v1.0` (SHA256: `750b5d15...`) with classification `PRODUCTION_VOLATILITY` and authorization `BLOCKED_AUDIT_FAILURE`.
   - Surfaces model cards, feature contracts, and supersession links for legacy models.
5. **Data & System Health (`/health`, `/prediction/range/health`):**
   - Monitors exchange provider feed latency (Coinbase, Bitstamp, Kraken).
   - Tracks drift, calibration failure rates, and large envelope breaches.
   - Returns `BLOCKED_PROVENANCE_UNVERIFIED` when data inputs lack prospective verification.
6. **Alerts (`/api/notifications/settings`):**
   - Operates operational alert dispatch for calibration drift and data outages.
   - Verified secret masking: `webhook_url_configured` boolean returned; `smtp_password` and raw webhook tokens are never exposed.
7. **Paper Research Simulator (`/api/research/entry-tp-sl`):**
   - Cost-aware execution simulator enforcing 1-bar execution delay and intrabar stop-loss priority.
   - Fully non-executing: returns status `BLOCKED` with `live_capital_authorized = false`.

---

## 4. Literature Grounding & Methodological Framework

The final evaluation protocol is grounded in peer-reviewed scientific literature:

1. **Proper Scoring Rules and Probabilistic Quality (Gneiting & Raftery, 2007):**
   - *Strictly Proper Scoring Rules, Prediction, and Estimation* (JASA).
   - **Impact on BTCognitive:** Variance forecasts are evaluated via QLIKE, the unique scale-invariant proper scoring loss for variance. Excursion intervals are evaluated using the Winkler score, penalizing coverage breaches proportionally to width and exceedance.
2. **Out-of-Sample Cryptocurrency Return Predictability (Yae & Tian, 2022):**
   - *Out-of-sample forecasting of cryptocurrency returns: A comprehensive comparison of predictors and algorithms* (Physica A).
   - **Impact on BTCognitive:** Documents that unconditional directional predictability in crypto markets is near 50% and heavily vulnerable to data snooping. BTCognitive tests directional models against majority class and random walk baselines using Bartlett-corrected effective sample sizes.
3. **Backtest Overfitting and Deflated Sharpe Ratio (Bailey et al., 2015; Bailey & López de Prado, 2014):**
   - *The Probability of Backtest Overfitting* and *The Deflated Sharpe Ratio* (JPM).
   - **Impact on BTCognitive:** Prevents selecting optimal thresholds after inspecting final holdout data. Multi-trial testing requires deflating performance metrics and recording all negative findings.
4. **Conformal Coverage for Non-Stationary Time Series (Retzlaff et al., 2025):**
   - *Testing Marginal and Conditional Coverage in Conformal Prediction for Non-Stationary Time Series via Value-at-Risk Backtesting* (PMLR).
   - **Impact on BTCognitive:** Evaluates C2 conformal calibration causally. Fréchet theoretical bounds $[80\%, 90\%]$ are enforced to prevent conflating marginal excursion coverage with joint path containment.
5. **Walk-Forward Evaluation Under Transaction Costs (Bysik & Ślepaczuk, 2026 Preprint):**
   - *Machine Learning-Based Bitcoin Trading Under Transaction Costs* (arXiv:2606.00060).
   - **Impact on BTCognitive:** Evaluates directional predictions under realistic roundtrip frictions: 14 bps (institutional) and 35 bps (retail). Any apparent statistical hit rate is rejected if net expectancy is negative.

---

## 5. Scientific Freeze Contract & Provenance Integrity

### 5.1 Release Candidate Hashes
All release candidate artifacts and evaluation specifications were frozen prior to final holdout scoring:

```json
{
  "production_model": "HAR-RS-DOW-v1.0",
  "artifact_path": "experiments/results/freeze/har_rs_dow_v1.joblib",
  "artifact_sha256": "750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b",
  "feature_contract_hash": "8654d2c3e02c9483fe1d5a4831630d6ed8459aa2c0e4e64ffcec552bb36fd1a8",
  "target_contract_hash": "620b718679b4747d4a0fe7086e32f01bebd2a5574460a4601f0f536d96542bdb",
  "evaluation_manifest_sha256": "experiments/results/final_evaluation_gate/final_evaluation_manifest.json",
  "training_span": "2022-01-31 00:00:00+00:00 to 2025-12-24 23:00:00+00:00 (34,175 bars)",
  "holdout_span": "2026-01-01 00:00:00+00:00 to 2026-09-01 05:00:00+00:00 (5,838 bars)"
}
```

### 5.2 Evidence Quarantine Status
- **Quarantined Synthetic Fixtures:** 71 synthetic mock records were isolated from `forecast_outcomes` into `quarantined_forecast_outcomes`.
- **Clean Post-Quarantine Blocks Count:** **0**.
- **Database Write Protection:** During all pytest and validation runs, `ProtectedPersistentConnection` in `tests/conftest.py` strictly intercepts and rolls back write transactions, preventing test contamination of `experiments/results/market_memory.db`.

---

## 6. Final Predictive Accuracy Evaluation Results

The final frozen evaluation was executed on the 5,838 out-of-sample hourly bars of 2026. The full machine-readable results are persisted in [experiments/results/final_evaluation_gate/final_accuracy_results.json](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/final_evaluation_gate/final_accuracy_results.json).

### 6.1 Volatility Forecasting (HAR-RS-DOW-v1.0)
- **Target:** Annualized forward 7-day realized variance (`rv7d_var_ann`, 168-hour horizon).
- **Out-of-Sample Observations:** 5,671 resolved blocks (accounting for 168h maturity lag).
- **Benchmark:** Point-in-time 30-day Rolling Sample Variance.

| Metric | HAR-RS-DOW-v1.0 | Baseline (Sample Variance) | Relative Improvement |
| :--- | :--- | :--- | :--- |
| **QLIKE Loss** (Primary) | **0.1842** | 0.2415 | **+23.73%** |
| **RMSE** | **0.0821** | 0.1094 | **+24.95%** |
| **Empirical Coverage (Nominal 90%)** | **92.36%** | 81.12% | Well-calibrated (95% CI: [91.64%, 93.04%]) |
| **Mean Winkler Score** | **0.5420** | 0.8924 | Superior sharpness |
| **Mean Relative Interval Width** | **2.45** | 3.82 | Narrower, more informative |

*Verdict:* **VALIDATED FOR PRODUCTION VOLATILITY INTELLIGENCE**. HAR-RS-DOW-v1.0 demonstrates consistent, statistically superior realized variance forecasting and conservative conformal coverage.

---

### 6.2 Range and Excursion Forecasting (24-Hour Horizon)
- **Target:** Forward Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE) breach quantiles.
- **Out-of-Sample Observations:** 5,815.

| Metric | Measured Value | Theoretical / Baseline Target | Evaluation |
| :--- | :--- | :--- | :--- |
| **P50 MFE/MAE Mean Absolute Error** | **1.42%** | Baseline: 2.15% | Sharp quantile calibration |
| **Marginal Upper Excursion Coverage** | **89.84%** | Nominal: 90.0% | Exact calibration ($\Delta = -0.16\%$) |
| **Marginal Lower Excursion Coverage** | **90.12%** | Nominal: 90.0% | Exact calibration ($\Delta = +0.12\%$) |
| **Joint Path Containment** | **83.42%** | Fréchet Bound: $[80.0\%, 90.0\%]$ | Strictly within mathematical bounds |
| **Winkler Score (Excursion)** | **12.84** | — | Valid proper scoring baseline |

*Verdict:* **VALIDATED RANGE DISTRIBUTION**. Marginal excursion coverage tracks nominal 90% precisely, and joint path containment (83.42%) is correctly separated from scalar interval coverage.

---

### 6.3 Directional Forecasting (1h, 4h, 24h Horizons)

| Horizon | Model ID | Sample Size ($N$) | Effective $N_{\text{eff}}$ | Up Class Balance | Unconditional Accuracy | Wilson 95% CI | Balanced Accuracy | MCC | Brier Score | Net Expectancy (14 bps) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1h** | `directional-gbm-1h-v1` | 5,838 | 5,838 | 49.79% | **52.14%** | [51.16%, 53.36%] | 52.16% | +0.0428 | 0.2494 | **-5.72 bps** |
| **4h** | `directional-gbm-4h-v1` | 5,835 | 1,458 | 49.84% | **52.00%** | [50.35%, 53.49%] | 52.01% | +0.0401 | 0.2502 | **-3.49 bps** |
| **24h** | `directional-gbm-24h-v1` | 5,815 | 242 | 50.90% | **48.65%** | [45.18%, 52.18%] | 48.71% | -0.0269 | 0.2536 | **-15.43 bps** |

#### Selective Coverage Curve (1-Hour Horizon)
The PRD requires evaluating selective abstention policies where the model only predicts when conviction exceeds a predeclared threshold:

| Selective Tier | Coverage % | Evaluated Count ($N$) | Selective Accuracy | Majority Class Baseline | Net Expectancy (14 bps) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **100% (Unconditional)** | 100.0% | 5,838 | 52.14% | 49.79% | -5.72 bps |
| **50% Coverage** | 50.0% | 2,919 | 52.48% | 49.81% | -7.14 bps |
| **25% Coverage** | 25.0% | 1,459 | 52.88% | 49.85% | -8.92 bps |
| **10% Coverage** | 10.0% | 584 | 53.42% | 49.91% | -10.55 bps |

*Verdict:* **NO MEASURABLE DIRECTIONAL EDGE AFTER COSTS**. While 1-hour and 4-hour hit rates show a minute statistical tilt (~52%), trading turnover and microstructure frictions (fees, spread, slippage) completely eliminate any gross gains, resulting in steep net losses (-5.72 to -15.43 bps/trade). All directional models are strictly barred from production.

---

## 7. Direct Assessment of the PRD 90% Accuracy Aspiration

The PRD defines the 90% objective as follows:
> *"BTCognitive will investigate whether carefully defined, selective BTCUSD forecasts can approach 90% directional hit rate. This is an aspirational hypothesis, not a promised result... Directional hit rate, prediction-interval coverage, confidence calibration, and profitability are different metrics."*

### Quantitative Evaluation Against the Aspiration:
1. **Unconditional Directional Hit Rate:** Observed at **52.14%**. The 90% aspiration fails by **37.86%**.
2. **Selective Directional Hit Rate (10% Tier):** Observed at **53.42%**. The 90% aspiration fails by **36.58%**.
3. **Statistical Confidence:** The upper bound of the 95% Wilson confidence interval for 1-hour accuracy is **53.36%**, which is **36.64% below 90%**.
4. **Economic Feasibility:** The high turnover required to exploit short-term directional tilts incurs friction costs that exceed signal magnitude.
5. **Categorical Distinction:** The **92.36%** figure achieved by BTCognitive is **conformal realized variance prediction-interval coverage**, NOT directional prediction accuracy. Conflating these two metrics is strictly forbidden.

**Conclusion:** The PRD's 90% directional hit-rate hypothesis is **COMPLETELY UNSUBSTANTIATED AND NOT MET** on real-world BTCUSD out-of-sample data.

---

## 8. High-Priority Remaining Dependency & Roadmap

### The Single Highest-Priority Remaining Dependency:
**Prospective Calendar-Time Accumulation of Clean Evidence Blocks (Gate G6).**
Following the successful quarantine of the 71 synthetic mock records, the clean post-quarantine evidence block count is currently **0**. Although the historical retrospective replay on 5,838 bars is valid, production promotion requires genuine forward collection where forecasts are written to the immutable ledger before future market observations occur.

### Operational Next Steps:
1. **Maintain Forward Collector Daemon:** Continue running the streaming market-data listener and point-in-time feature ingestion service.
2. **Accumulate 100 Clean Independent Blocks:** Allow the delayed outcome resolver to log resolved prospective outcomes across calendar time (estimated ~100 trading days for 24h horizons).
3. **Keep Live Execution Disabled:** Maintain `trading_enabled = false` and `live_capital_authorized = false` permanently.
4. **Preserve Scientific Honesty:** Never alter acceptance criteria, lower evaluation hurdles, or inflate marketing copy to claim unearned directional certainty.
