# BTCognitive — 24H QLIKE-HAR Challenger & Prospective Evidence Accumulation Report

**Version:** 1.0.0  
**Date:** 16 October 2026  
**Track:** 24-Hour Realized Variance Forecasting & Prospective Evidence Accumulation  
**Experiment ID:** `EXP-2026-04-QLIKE-24H`  
**Status:** Complete — Evaluated, Governed & Preserved in Research Register  
**Production Status:** Baseline Preserved (`HAR-RS-DOW-v1.0`), Challenger Offline Research Only (`HAR-QLIKE-24H`)  
**Live Execution Status:** STRICTLY DISABLED (Zero capital, zero broker order placement)  

---

## 1. Executive Summary & Epistemic Verdicts

This research sprint investigated whether a loss-coherent Heterogeneous Autoregressive (HAR) model forecasting next-day (24-hour) realized variance improves upon appropriate same-target BTC volatility benchmarks, evaluated under a causally valid, preregistered testing protocol. In parallel, a tamper-evident, append-only prospective evidence pipeline was implemented and activated to collect matched out-of-sample forecasts on observations never exposed during model development.

### Core Decisions

| Decision Pillar | Status / Verdict | Epistemic Justification |
| :--- | :--- | :--- |
| **Research Experiment** | **RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY** | `HAR-QLIKE-24H` achieves a **+14.84%** raw sample QLIKE reduction over OLS HAR-24H on daily non-overlapping origins ($N=243$), but the Harvey–Leybourne–Newbold corrected Diebold–Mariano test yields $p = 0.1622$ ($p \ge 0.05$). Under secondary hourly rolling origins ($N=5,815$), $p = 0.0735$. Fails confirmatory significance gate. |
| **Prospective Evidence** | **COLLECTING** | Append-only ledger initialized at `data/prospective_forecast_ledger.jsonl`. Clean resolved blocks count = 0. A minimum of 100 non-overlapping clean blocks (~100 calendar days) is required for confirmatory prospective evaluation. |
| **Model Authorization** | **OFFLINE_RESEARCH_ONLY** | Candidate cannot inherit production status from 168h models. Production inference remains gated to `HAR-RS-DOW-v1.0` (with production endpoints failing closed under `BLOCKED_AUDIT_FAILURE`). |
| **Live Trading** | **DISABLED** | All capital deployment, broker connectors, and automated execution are strictly disabled. Volatility forecasts serve risk intelligence only. |

> [!IMPORTANT]
> **Directional Accuracy Boundary:** Volatility forecasting accuracy (measured by QLIKE or RMSE) must never be conflated with directional return prediction accuracy or trading profitability. The 90% directional hit rate remains an aspirational research hypothesis that is unsupported on unconditional cryptocurrency returns.

---

## 2. Research Foundations & Statistical Design

### 2.1 Academic Foundations

The experimental design is grounded in seven peer-reviewed econometrics and forecasting publications:

1. **Puke & Schweikert (2026)**, *Coherent Forecasting of Realized Volatility*, Journal of Forecasting, 45(4), 1714–1729. [DOI: 10.1002/for.70114](https://doi.org/10.1002/for.70114)  
   *Core Finding:* When forecast performance is evaluated under QLIKE loss, parameter estimation directly minimizing sample QLIKE aligns estimation with evaluation, eliminating parameter bias present in standard OLS log-variance regressions.
2. **Corsi (2009)**, *A Simple Approximate Long-Memory Model of Realized Volatility*, Journal of Financial Econometrics, 7(2), 174–196. [DOI: 10.1093/jjfinec/nbp001](https://doi.org/10.1093/jjfinec/nbp001)  
   *Core Finding:* Heterogeneous autoregressive modeling captures multi-scale volatility persistence (daily, weekly, monthly components) through a parsimonious linear cascade.
3. **Patton (2011)**, *Volatility forecast comparison using imperfect volatility proxies*, Journal of Econometrics, 160(1), 246–256. [DOI: 10.1016/j.jeconom.2010.03.034](https://doi.org/10.1016/j.jeconom.2010.03.034)  
   *Core Finding:* QLIKE is the unique homogeneous, scale-invariant loss function that provides robust, ranking-consistent rankings of volatility models when evaluating against imperfect volatility proxies.
4. **Diebold & Mariano (1995)**, *Comparing Predictive Accuracy*, Journal of Business & Economic Statistics, 13(3), 253–263. [DOI: 10.1080/07350015.1995.10524599](https://doi.org/10.1080/07350015.1995.10524599)  
   *Core Finding:* Standard asymptotic test of equal predictive accuracy for paired loss differentials.
5. **Harvey, Leybourne & Newbold (1997)**, *Testing the equality of prediction mean squared errors*, International Journal of Forecasting, 13(2), 281–291. [DOI: 10.1016/S0169-2070(96)00719-4](https://doi.org/10.1016/S0169-2070(96)00719-4)  
   *Core Finding:* Finite-sample correction factor $S = \sqrt{\frac{T + 1 - 2h + h(h-1)/T}{T}}$ and the critical mandate to evaluate against Student's $t$ reference distribution with $T - 1$ degrees of freedom rather than standard normal critical values.
6. **Tashman (2000)**, *Out-of-sample tests of forecasting accuracy: an analysis and review*, International Journal of Forecasting, 16(4), 437–450. [DOI: 10.1016/S0169-2070(00)00065-0](https://doi.org/10.1016/S0169-2070(00)00065-0)  
   *Core Finding:* Strict adherence to rolling-origin evaluation without lookahead, feature re-centering, or hyperparameter contamination across splits.
7. **Hansen, Lunde & Nason (2011)**, *The Model Confidence Set*, Econometrica, 79(2), 453–497. [DOI: 10.3982/ECTA5771](https://doi.org/10.3982/ECTA5771)  
   *Core Finding:* Multiplicity-aware testing rules preventing model selection bias from multiple comparisons.

### 2.2 Correction of the Harvey–Leybourne–Newbold Statistic Inconsistency

During the Phase 1 audit of earlier exploratory scripts, an econometric inconsistency was discovered: while an HLN-corrected statistic was printed, the corresponding $p$-value was computed using `scipy.stats.norm.sf(uncorrected_dm)`.

In this sprint, this flaw was permanently corrected in both `models/challengers/har_qlike_challenger.py` and `models/challengers/har_qlike_24h_challenger.py`:
- The finite-sample correction factor is applied:
  $$d_{\text{HLN}} = d_{\text{DM}} \times \sqrt{\frac{T + 1 - 2h + h(h-1)/T}{T}}$$
- The one-sided $p$-value for $H_1: \bar{d} > 0$ is rigorously calculated from the survival function of Student's $t$ distribution with $T - 1$ degrees of freedom:
  $$p = \Pr(t_{T-1} \ge d_{\text{HLN}}) = \text{sf}(d_{\text{HLN}}, \text{df}=T-1)$$
- Deterministic known-answer unit tests in `tests/test_phase_24h_qlike_and_prospective.py` verify that Student's $t_{T-1}$ is used.

---

## 3. Data & Target Contract Specifications

### 3.1 Raw Market Data & Sampling Frequency

Inspection of `data/raw/ohlcv.parquet` confirms:
- **Exchange & Pair:** Coinbase BTC-USD.
- **Bar Frequency:** 1-hour OHLCV candles (timestamped at bar open in UTC).
- **History Range:** 2022-01-01 00:00:00 UTC to 2026-09-01 06:00:00 UTC ($40,903$ total candles).
- **Sampling Convention:** No sub-hourly candles (1-minute or 5-minute) exist in the local raw dataset. Therefore, the target is explicitly designated as an **hourly-sampled realized-variance proxy**, not a continuous or minute-sampled variance.

### 3.2 24-Hour Forward Target Contract (`rv24h_var_ann`)

The 24-hour forward realized variance target is defined strictly over the 24 future closed candles from issue time $t$ to maturity time $t+24\text{h}$:

$$r_{t+j} = \ln\left(\frac{\text{Close}_{t+j}}{\text{Close}_{t+j-1}}\right), \quad j = 1, \dots, 24$$

$$\text{RV}_{t, t+24\text{h}} = \sum_{j=1}^{24} r_{t+j}^2$$

$$\text{rv24h\_var\_ann}_t = \left(\frac{8760.0}{24.0}\right) \times \text{RV}_{t, t+24\text{h}} = 365.0 \times \sum_{j=1}^{24} r_{t+j}^2$$

- **Target Window:** Exactly 24 continuous hours.
- **Annualization:** Scaled by $365.0$ ($8,760 \text{ hours/year} / 24 \text{ hours/target}$).
- **Units:** Annualized variance in decimal (e.g., $0.25$ represents a $25\%$ annualized variance; equivalent volatility is $\sqrt{0.25} = 50.0\%$).
- **Causal Boundary:** Point-in-time features at time $t$ use only information available at or before $t$. The target spans $t+1\text{h}$ to $t+24\text{h}$. The last 24 rows of any dataset evaluate to `NaN` and are excluded from training and evaluation.
- **Preservation of 168h Target:** The existing `rv7d_var_ann` target is strictly preserved for 7-day models.

---

## 4. Models & Experimental Candidates

Four competing volatility forecasting models were evaluated on identical timestamps and target outcomes:

### 1. Benchmark 1: Realized Variance Persistence ($B_1$)
- **Specification:** Trailing 24-hour annualized realized variance:
  $$\hat{\sigma}^2_{B1, t} = \text{rv1d\_var\_ann}_t = 365.0 \times \sum_{k=0}^{23} r_{t-k}^2$$
- **Parameters:** Non-parametric (zero estimated coefficients).

### 2. Benchmark 2: Rolling 30-Day Mean Benchmark ($B_2$)
- **Specification:** Trailing 30-day (720 hours) annualized realized variance:
  $$\hat{\sigma}^2_{B2, t} = \text{rv30d\_var\_ann}_t = \left(\frac{8760.0}{720.0}\right) \times \sum_{k=0}^{719} r_{t-k}^2$$
- **Parameters:** Non-parametric (zero estimated coefficients).

### 3. Benchmark 3: Conventional HAR-24H (OLS Log-Variance) ($B_3$)
- **Specification:** Standard Corsi (2009) cascade estimated via Ordinary Least Squares on log variance:
  $$\ln(\text{rv24h\_var\_ann}_t) = \beta_0 + \beta_d \ln(\text{rv1d}_t) + \beta_w \ln(\text{rv7d}_t) + \beta_m \ln(\text{rv30d}_t) + \epsilon_t$$
- **Point Forecast:** $\hat{\sigma}^2_{B3, t} = \exp(\hat{y}_t)$.
- **Artifact:** `experiments/results/research_improvement/har_ols_24h_v1.joblib` (SHA256: `7a247cf1c0a9...`).

### 4. Candidate: QLIKE-Coherent HAR-24H Challenger ($C_1$)
- **Specification:** Direct minimization of sample QLIKE loss with $L_2$ Tikhonov regularization (Puke & Schweikert, 2026):
  $$\min_{\beta} \frac{1}{N} \sum_{i=1}^N \text{QLIKE}(y_i, \exp(X_i \beta)) + \lambda \|\beta\|_2^2$$
  where $\text{QLIKE}(y, \hat{y}) = \frac{y}{\hat{y}} - \ln\left(\frac{y}{\hat{y}}\right) - 1$.
- **Regularization:** $\lambda = 10^{-4}$ (selected strictly on pre-2026 chronological training data).
- **Optimization:** L-BFGS-B initialized with OLS coefficients. Guaranteed positive variance output ($\exp(X\beta) > 0$).
- **Artifact:** `experiments/results/research_improvement/har_qlike_24h_v1.joblib` (SHA256: `fbc8818da9cf...`).

---

## 5. Empirical Results & Scorecard

### 5.1 Primary Evaluation: Daily Non-Overlapping Origins ($N=243$)

To eliminate mechanical serial dependence caused by overlapping target intervals, the primary confirmatory origin schedule evaluated exactly one forecast per day at **00:00 UTC** across the entire 2026 out-of-sample window (2026-01-01 to 2026-09-01).

| Model | Mean QLIKE | Variance RMSE | Variance MAE | Relative Gain vs OLS | HLN DM Stat | $p$-value (one-sided) | Statistical Significance |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence ($B_1$)** | 0.73028 | 0.24001 | 0.13994 | -95.99% | -3.4979 | 0.9997 | Rejected ($B_1 < B_3$) |
| **Rolling 30D Mean ($B_2$)** | 0.49521 | 0.23030 | 0.13276 | -32.91% | -1.7423 | 0.9586 | Rejected ($B_2 < B_3$) |
| **Conventional HAR-24H ($B_3$)** | 0.37259 | 0.20327 | **0.10063** | *Benchmark* | — | — | Baseline Reference |
| **HAR-QLIKE-24H ($C_1$)** | **0.31729** | **0.19529** | 0.12084 | **+14.84%** | **+0.9874** | **0.16221** | **Inconclusive ($p \ge 0.05$)** |

#### Analysis of Daily Findings
1. **Economic Effect Size:** `HAR-QLIKE-24H` outperforms conventional OLS HAR by **14.84%** in QLIKE loss ($0.31729$ vs $0.37259$) and reduces variance RMSE by **3.93%** ($0.19529$ vs $0.20327$).
2. **Statistical Uncertainty:** The loss differential series exhibits volatility clustering. The Harvey–Leybourne–Newbold test statistic is $+0.9874$, yielding a Student's $t$ ($df=242$) one-sided $p$-value of **$0.1622$**.
3. **Acceptance Gate Verdict:** Because $p = 0.1622 > 0.05$, the candidate fails the preregistered hurdle for production promotion.

---

### 5.2 Secondary Evaluation: Hourly Rolling Origins ($N=5,815$)

For diagnostic comparison, all hourly forecast origins were evaluated with Newey–West heteroskedasticity-and-autocorrelation-consistent (HAC) variance estimation using lag $L=24$.

| Model | Mean QLIKE | Variance RMSE | Relative Gain vs OLS | HLN DM Stat (NW lag=24) | $p$-value (one-sided) | Significance |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence ($B_1$)** | 0.80942 | 0.24632 | -116.13% | -4.9753 | 1.0000 | Dominated |
| **Rolling 30D Mean ($B_2$)** | 0.50081 | 0.23498 | -33.73% | -2.9917 | 0.9986 | Dominated |
| **Conventional HAR-24H ($B_3$)** | 0.37450 | 0.21240 | *Benchmark* | — | — | Baseline Reference |
| **HAR-QLIKE-24H ($C_1$)** | **0.32419** | **0.20162** | **+13.43%** | **+1.4502** | **0.07353** | **Marginal ($p \ge 0.05$)** |

#### Analysis of Hourly Findings
On the high-frequency evaluation with $N=5,815$ observations, the challenger maintains a **13.43%** QLIKE reduction. While the larger sample size increases the test statistic to $+1.4502$ ($p = 0.0735$), the $p$-value remains above the confirmatory $\alpha=0.05$ threshold once the 24-hour overlapping covariance structure is accounted for via Newey–West kernels.

---

## 6. Prospective Evidence Pipeline Architecture

To prevent retrospective data snooping and ensure future evaluations test models strictly on untouched out-of-sample data, an append-only prospective research ledger was established.

### 6.1 Ledger Schema & Cryptographic Provenance

Ledger Location: `data/prospective_forecast_ledger.jsonl`

Each committed forecast entry includes:
- `forecast_id`: UUIDv4 unique identifier.
- `issue_timestamp_utc`: Exact UTC forecast creation timestamp.
- `target_name`: `rv24h_var_ann`.
- `horizon_hours`: $24$.
- `feature_availability_cutoff_utc`: Exact timestamp verifying no features post-date issue time.
- `data_source_id`: `coinbase_btcusd_hourly_parquet`.
- `data_quality`: `VALID`.
- `feature_schema_hash`: SHA256 of the active feature schema.
- `model_version`: `HAR-QLIKE-24H-v1.0`.
- `artifact_hash`: SHA256 of candidate joblib artifact.
- `baseline_predictions`: Trailing persistence, rolling 30d, and conventional HAR forecasts.
- `challenger_prediction`: Point prediction from `HAR-QLIKE-24H`.
- `scheduled_maturity_utc`: Exactly $t + 24\text{h}$.
- `resolution_state`: `PENDING` $\to$ `RESOLVED` (or `EXCLUDED`).
- `resolved_outcome`: Forward realized variance computed strictly from closed candles.
- `exclusion_reason`: Non-null only if forward data has gaps or anomalies.

### 6.2 Deterministic & Idempotent Outcome Resolver

Outcome resolution is governed by `engine/prospective_evidence_pipeline.py`:
1. **Delayed Resolution Invariant:** No forecast is resolved until current UTC time exceeds `scheduled_maturity_utc`.
2. **Deterministic Calculation:** Forward realized variance is calculated identically to the target formula from closed hourly candles.
3. **Idempotence:** Running the resolver multiple times updates pending records exactly once and leaves already-resolved rows untouched.
4. **Test Isolation:** Unit and integration tests operate on temporary ledger files and are isolated from protected prospective data.

### 6.3 Current Accumulation State

```json
{
  "ledger_path": "data/prospective_forecast_ledger.jsonl",
  "total_logged_forecasts": 1,
  "pending_resolution": 1,
  "resolved_outcomes": 0,
  "excluded_records": 0,
  "clean_prospective_blocks_count": 0,
  "prospective_status": "COLLECTING"
}
```

**Accumulation Target:** A minimum of **100 non-overlapping clean blocks** (~100 calendar days) is required before conducting the first confirmatory prospective evaluation.

---

## 7. Model Identity Registry & Research API Integration

### 7.1 Model Identity Registrations

In `models/authoritative_model_registry.py`, both 24-hour models are formally recorded as distinct entities:
- **`HAR-RS-DOW-24H`**: Conventional OLS 24-Hour Benchmark (`OFFLINE_RESEARCH_ONLY`).
- **`HAR-QLIKE-24H`**: QLIKE Loss-Coherent 24-Hour Challenger (`OFFLINE_RESEARCH_ONLY`).

Production verification gates (`verify_production_model_alignment`) reject both models, preserving the single active production volatility model (`HAR-RS-DOW-v1.0`).

### 7.2 Research API Endpoints

The following REST endpoints are live in `api/routes_research.py`:
- `GET /api/research/prospective-ledger`: Returns real-time status and recent records from the append-only ledger.
- `GET /api/research/24h-scorecard`: Returns the machine-readable scorecard, manifest, and comparative metrics.
- `GET /api/research/experiments`: Catalogues `EXP-2026-04-QLIKE-24H` alongside prior research trials.

---

## 8. Verification & Test Evidence

All unit, property, and integration tests passed cleanly:

```bash
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-8.4.1
rootdir: C:\Projects\BTCognitive\BTCognitive
collected 12 items

tests/test_phase_24h_qlike_and_prospective.py::test_target_calculation_known_returns PASSED
tests/test_phase_24h_qlike_and_prospective.py::test_target_future_boundary_strictly_ahead PASSED
tests/test_phase_24h_qlike_and_prospective.py::test_causal_feature_invariance PASSED
tests/test_phase_24h_qlike_and_prospective.py::test_hand_computed_qlike_loss PASSED
tests/test_phase_24h_qlike_and_prospective.py::test_qlike_loss_non_negative PASSED
tests/test_phase_24h_qlike_and_prospective.py::test_hln_finite_sample_correction_and_student_t PASSED
tests/test_phase_24h_qlike_and_prospective.py::test_har_models_fit_and_predict_positive PASSED
tests/test_phase_24h_qlike_and_prospective.py::test_prospective_pipeline_append_and_resolve PASSED
tests/test_phase_24h_qlike_and_prospective.py::test_model_registry_24h_authorization PASSED
tests/test_phase_24h_qlike_and_prospective.py::test_api_prospective_ledger_endpoint PASSED
tests/test_phase_24h_qlike_and_prospective.py::test_api_24h_scorecard_endpoint PASSED
tests/test_phase_24h_qlike_and_prospective.py::test_api_experiments_register_includes_24h PASSED

======================== 12 passed, 1 warning in 1.97s ========================
```

---

## 9. Limitations & Next Recommended Research

### 9.1 Limitations
1. **Sampling Frequency Ceiling:** The dataset contains hourly closes. While this enables a valid hourly-sampled realized variance proxy, intra-hour volatility spikes (5-minute or tick level) cannot be captured without higher-frequency data ingestion.
2. **Retrospective Evaluation Exposure:** The Jan–Sep 2026 window was previously inspected in earlier development stages. While useful for model discrimination, confirmatory proof requires unobserved prospective observations.
3. **Statistical Power on Daily Origins:** With $N=243$ daily origins and high persistent cryptocurrency volatility, a true 14% loss reduction requires larger sample sizes ($N \approx 400$) or multi-asset pooling to achieve $p < 0.05$ after dependence adjustments.

### 9.2 Recommended Next Sprint
1. **Maintain Prospective Shadow Accumulation:** Allow `data/prospective_forecast_ledger.jsonl` to accumulate daily forecasts without adjusting candidate hyperparameters.
2. **Multi-Scale Realized Variance Fusion:** Once 100 prospective blocks accumulate, investigate combining the 24-hour target proxy with 4-hour intermediate variance anchors.
3. **Cross-Asset Volatility Spillovers:** Integrate point-in-time ETH hourly realized variance as an exogenous HAR predictor once multi-asset raw parquet provenance is audited.
