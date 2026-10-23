# BTCognitive Master Product Requirements Document (PRD)

**Version:** 1.0 (Superseded & Continued by [Version 2.0](file:///C:/Projects/BTCognitive/BTCognitive/docs/BTCognitive_Master_PRD_v2_Continuation.md))  
**Date:** 16 October 2026  
**Product:** BTCognitive — Research-Based BTCUSD Forecasting and Market-Risk Intelligence  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Status:** Continued in Version 2.0; research-first, non-execution  
**Document purpose:** Establish one product vision, technical direction, research methodology, and implementation plan for improving the existing BTCognitive application.

> [!NOTE]
> **Product Requirements Continuation Notice:** This document is continued and expanded by [BTCognitive Master PRD v2.0 Continuation](file:///C:/Projects/BTCognitive/BTCognitive/docs/BTCognitive_Master_PRD_v2_Continuation.md) (dated 16 October 2026), incorporating the 6-state governance model, quantitative literature synthesis, dual-target prospective collection protocols, and live telemetry UX contracts.

**Critical research boundary:** BTCognitive will investigate whether carefully defined, selective BTCUSD forecasts can approach 90% directional hit rate. This is an aspirational hypothesis, not a promised result. No credible evidence reviewed for this PRD establishes that a general-purpose BTCUSD platform can sustain 90% directional accuracy on all forecasts across meaningful out-of-sample periods after realistic costs. Directional hit rate, prediction-interval coverage, confidence calibration, and profitability are different metrics.

---

## 1. Executive Summary

BTCognitive is a research platform for studying and forecasting BTCUSD, not a black-box buy/sell bot. Its goal is to help a researcher understand what may happen, over which horizon, how uncertain the forecast is, what evidence supports it, and whether the forecast has shown repeatable out-of-sample value.

The recommended decision is to continue using the existing repository and evolve it incrementally. The current codebase already contains relevant foundations: FastAPI endpoints, a Research Terminal, market-data providers, point-in-time features, a HAR-RS-DOW volatility model, quantile/excursion forecasting, conformal calibration research, model registries, experiment reports, validation utilities, and an execution simulator. Rebuilding from scratch would discard useful work and create additional integration risk.

The repository does, however, contain a material governance problem that must be solved first: README and model/research documents describe different serving and authorization states, and historical model cards have been superseded by later research. Before improving model performance, BTCognitive must identify the exact model artifact and feature contract used by every endpoint, authenticate their provenance, and show the correct status to the UI.

### Product thesis
Build an **Evidence-Gated, Regime-Conditioned Forecasting system (EGRF)** by combining proven, independently testable concepts:
- Target-specialized models instead of one model pretending to solve every horizon and task.
- A reliable statistical baseline before complex ML challengers.
- Incremental feature testing for volatility, market microstructure, derivatives, and cross-market context.
- Regime-conditioned expert routing only when sufficient evidence exists.
- Causal uncertainty calibration, calibrated probabilities, and a formal abstention state.
- Immutable forecast records, independent evaluation, and economic-cost checks before any promotion.

*EGRF is a proposed BTCognitive architecture, not a claim that a novel algorithm has already been invented or validated.*

### Near-term priority
The first release goal is not to achieve a headline accuracy number. It is to make every forecast reproducible and falsifiable. Then test whether additional features and specialized models improve performance over a frozen baseline. Directional accuracy toward 90% is a stretch research question for a predeclared selective subset; it is not an unconditional product requirement.

---

## 2. Product Definition

### 2.1 Problem statement
BTCUSD returns are noisy, market regimes change, data quality differs by provider and instrument, and apparent model improvements can be created by leakage, repeated experiments, overfitting, or ignored trading costs. Many retail forecasting platforms display directional predictions or confidence scores without explaining their target definition, sample size, uncertainty, or true out-of-sample performance.

BTCognitive must provide a disciplined workflow that helps a researcher answer:
1. What is the exact target: direction, return magnitude, realized volatility, price excursion, or interval containment?
2. What horizon does the prediction cover?
3. What information was available at the forecast timestamp?
4. Does the model beat a relevant baseline out of sample?
5. Does performance persist across independent chronological periods and market regimes?
6. Is uncertainty calibrated, and when should the model abstain?
7. Does any signal remain useful after fees, spread, slippage, funding, and execution uncertainty?

### 2.2 Product vision
A transparent BTCUSD research platform that combines multi-horizon forecast specialists, regime-aware feature evidence, calibrated uncertainty, and auditable validation to discover where Bitcoin is and is not predictably forecastable.

### 2.3 Primary users
- **Researcher / project owner:** designs experiments, inspects features, compares models, audits failures, and approves promotion.
- **Research viewer:** inspects current market context, forecast distributions, calibration, and past forecast outcomes.
- **Developer / operator:** checks API, data feeds, provenance, model identity, runtime health, and release status.

*This PRD does not include public financial-advice positioning or automated trading.*

### 2.4 Product principles
1. **Evidence before complexity:** A new model is only useful if it adds reproducible value against the baseline.
2. **Causality by construction:** A forecast may use only information available as of its issue timestamp.
3. **Separate tasks and horizons:** Direction, volatility, excursions and trading outcomes are not interchangeable.
4. **Abstention is valid:** The system must be allowed to say `NO_EDGE`, `INSUFFICIENT_DATA`, `STALE_DATA`, or `OUT_OF_DISTRIBUTION`.
5. **Coverage is not accuracy:** Range containment and quantile coverage cannot be marketed as directional prediction accuracy.
6. **No manufactured certainty:** Missing data, model disagreement, failed provenance and expired authorization must remain visible.
7. **Research is not execution:** No live order placement or real-capital management in the scope of this PRD.
8. **Laptop-first:** The core project must be runnable and useful without a discrete GPU.

---

## 3. The 90% Objective: Precise Definition and Limits

### 3.1 What the objective means
The phrase “up to 90% accuracy” is only meaningful when the target, horizon, prediction population, selection policy and evaluation period have been fixed in advance. BTCognitive will investigate the following as a stretch research hypothesis:
> *Can a selective directional model attain a directional hit rate approaching 90% on a predeclared subset of BTCUSD forecast origins, at a declared horizon, with sufficient resolved outcomes, acceptable uncertainty, evidence across multiple chronological periods, and no post-hoc threshold selection?*

The platform must report the **coverage** of the selective model: the percentage of forecast origins on which it actually issues a directional prediction. A 90% hit rate on a tiny hand-selected sample is not a useful system-level result. It can be misleading if the selection threshold is tuned on the same data used to report performance.

### 3.2 Metrics that must never be conflated

| Term | Definition | What it does not mean |
| :--- | :--- | :--- |
| **Directional hit rate** | Fraction of issued directional calls whose predicted return sign matches the realized sign at a fixed horizon | Probability the next move will occur; profitability; accuracy for all regimes |
| **Selective accuracy** | Directional hit rate among forecasts allowed through a preregistered abstention rule | Performance on forecasts the system declined to issue |
| **Prediction-interval coverage** | Fraction of realized outcomes inside a defined prediction interval/envelope | Directional accuracy or a universal guarantee of conditional coverage |
| **Probability calibration** | Agreement between forecast probabilities and empirical event frequencies | A promise that any single forecast is correct |
| **Forecast loss** | Error score for a specified numeric target (e.g., QLIKE, MAE, pinball or Winkler score) | A percentage that can be compared directly to classification accuracy |
| **Strategy profitability** | Performance of a fully specified policy after costs and execution assumptions | A consequence automatically implied by model accuracy |

### 3.3 Proposed research policy
1. Establish unconditional directional performance first, including majority-class, zero-return and simple momentum/reversion baselines.
2. Evaluate fixed horizons independently: 5m, 15m, 1h, 4h and 24h. Do not merge their scores.
3. Test selective prediction using thresholds selected on training/validation data and frozen before the final test.
4. As an initial governance proposal, require at least 10% forecast coverage for a headline selective-accuracy result, at least 100 effective independent selected outcomes, and evaluation across at least three chronological test windows. Effective sample size must account for overlapping labels and dependence.
5. Report point estimate, block-aware confidence interval, selected forecast count, effective sample size, coverage, class distribution and results by regime.
6. Treat 90% as achieved only if the preregistered test supports it on untouched outcomes. If evidence is insufficient, report `INCONCLUSIVE`; if performance fails, retain the negative finding and do not keep adjusting the threshold on the holdout.
7. Never use 90% confidence as shorthand for an empirical 90% hit rate or a nominal 90% conformal envelope.
8. **Product requirement:** no screen, README, chart, demo or marketing copy may claim 90% directional accuracy until the exact metric has passed the defined evaluation and governance gates.

---

## 4. Can the Existing Application Be Used?

Yes. The existing BTCognitive repository should be the foundation. Do not rewrite the project. Reuse its working subsystems, then consolidate overlapping research paths behind one authoritative contract.

### 4.1 Reuse map

| Existing area | Planned action | Rationale |
| :--- | :--- | :--- |
| `api/` and FastAPI routes | Keep; audit model-serving and research gates | Existing API boundaries should remain stable while model governance is repaired |
| `web/` Research Terminal | Keep; evolve status, evidence and forecast panels | Current UI avoids an unnecessary frontend rewrite |
| `engine/point_in_time_features.py` and feature pipeline | Reuse and extend after leakage tests | Central place for time-aligned feature construction |
| `models/registry/` and authoritative model registry | Keep; reconcile identities and statuses | Every forecast needs one authoritative model/artifact identity |
| `models/registry/HAR-RS-DOW-v1.0/` | Retain as documented volatility baseline pending re-verification | Existing baseline should be challenged with evidence rather than replaced by preference |
| `engine/uncertainty_calibration.py` and Stage 12 causal calibration | Reuse after independent verification | Existing research already focuses on causal calibration failures |
| `validation/` and `research/` evaluation scripts | Consolidate into a canonical evaluation CLI | Avoid multiple inconsistent metric implementations and duplicated workflows |
| `backtest/execution_simulator.py` and related cost models | Reuse for research-only economic tests | Existing execution work is preferable to a new optimistic simulator |
| `experiments/results/` and manifests | Keep as an experiment ledger; mark superseded results | Historical negative findings must remain auditable |
| Hawkes, Mamba, TFT, foundation model and genetic search | Isolate as challengers; no automatic production coupling | Complexity only earns a place with demonstrated incremental value |

### 4.2 Mandatory reconciliation before model work
The public README states that frozen production inference and production forecasts are disabled until provenance is authenticated. The HAR-RS-DOW model card describes an authorized volatility model, while earlier Ridge excursion cards are archived or superseded. These may represent successive development stages, but the active endpoint state must be made unambiguous.

Phase 0 must determine and record:
- Exact repository commit and clean/dirty state;
- Authoritative model ID, target, horizon, artifact checksum and feature schema;
- Which artifact each serving route actually loads;
- Required data and calibration manifests;
- Whether the release gate passes or fails and why;
- Tests that reproduce the claims in the relevant model card;
- Exact UI copy for blocked, experimental, historical, shadow, and authorized statuses.

Do not delete old reports just to make the documentation consistent. Supersede them with a clear status header and links to the canonical replacement.

---

## 5. Proposed Differentiator: Evidence-Gated, Regime-Conditioned Forecasting (EGRF)

EGRF is the proposed architecture for combining ideas into one coherent research system. It is not a promise of superior accuracy, and no claim of algorithmic novelty is made until a separate literature and novelty review is completed.

### 5.1 Operating loop
1. **Observe:** Ingest verified spot, derivatives, order-book, on-chain, options and cross-market data where accessible.
2. **Validate:** Check schema, freshness, time semantics, instrument, data gaps and provider status.
3. **Construct features:** Create only point-in-time features whose input timestamps are no later than the forecast issue time.
4. **Identify context:** Assign a market-state estimate using causal features, with an `UNKNOWN` state when evidence is weak.
5. **Forecast by task:** Run a target-specific baseline and only those specialized candidate models that have met readiness criteria.
6. **Calibrate:** Convert raw outputs into probability or quantile forecasts using only outcomes resolved before the forecast timestamp.
7. **Gate:** Select an expert or abstain based on predeclared validation evidence, calibration health, data quality, out-of-distribution checks and model agreement.
8. **Log:** Save an immutable prediction record and feature/data/model provenance.
9. **Resolve:** Once the target horizon passes and valid market data exist, resolve the outcome and update monitoring/calibration with appropriate delay.
10. **Evaluate:** Compare forecasts with baseline predictions and persist paired errors for future model reviews.

### 5.2 Expert groups and task boundaries

| Expert | Primary target | Candidate horizon | First baseline | Advanced challenger options |
| :--- | :--- | :--- | :--- | :--- |
| **Volatility expert** | Realized variance / volatility | 24h and 7d | HAR-RS-DOW; HAR-RV; EWMA | Quantile tree, selected cross-asset features |
| **Range/excursion expert** | Forward MFE/MAE quantiles and breach risk | 1h, 4h, 24h only where labels are valid | Historical quantiles and volatility-scaled baseline | Quantile regression / gradient boosting plus causal calibration |
| **Direction expert** | Return sign or thresholded return event | 5m, 15m, 1h, 4h, 24h as separately evaluated tasks | Majority class, zero-drift, simple momentum/reversion | Logistic/Ridge, gradient boosting, return-trajectory conditioning |
| **Microstructure expert** | Short-horizon price move / adverse selection | 5m and 15m | Naive event baseline | OFI/depth models; Hawkes only with verified event-time inputs |
| **Cross-market context** | Incremental information from other assets | Primarily 1h–7d | Base model without external context | Low-dimensional factors / correlation changes |

*An expert may be unavailable for a horizon if data, sample size or validation do not support it. The router must never silently substitute an unrelated target or make unsupported claims.*

### 5.3 Regime and evidence gate
Regimes are research labels, not immutable market truths: `LOW_VOL`, `NORMAL_VOL`, `VOL_EXPANSION`, `JUMP_STRESS`, `TRENDING`, `RANGE_BOUND`, `ILLIQUID`, and `UNKNOWN`.

The system chooses an expert only if:
- Feature and market-data contracts pass;
- Expert has sufficient independent historical evaluation outcomes for the relevant context;
- Calibration and drift checks pass;
- Expert adds reproducible value over its baseline in that context;
- Uncertainty and disagreement are within predeclared bounds.

Otherwise, output is a baseline forecast or explicit abstention.

### 5.4 Confidence decomposition
Do not publish one opaque “AI confidence” number. Present only:
- Predicted class probabilities (if validated and calibrated);
- Forecast interval or quantile range;
- Calibration error and recent empirical coverage;
- Effective independent sample size and evaluation window;
- Model disagreement;
- Data freshness/health;
- Current market-state classification and representation in evaluation;
- Reason for abstention, if applicable.

---

## 6. Data and Feature Requirements

### 6.1 Data-source policy
Prioritize correctness and accessible data over collecting many feeds. Existing public market feeds support the core application. Additional feeds must be optional behind adapters and never represented as configured until verified.

| Data family | Candidate data | Initial use | Required controls |
| :--- | :--- | :--- | :--- |
| **Spot market** | BTC-USD OHLCV from verified provider(s) | All horizons; baseline & realized volatility | Closed-candle checks, UTC normalization, gap detection, provider identity |
| **Perpetual derivatives** | Funding, open interest, basis, liquidations | 15m–24h context | Contract/settlement timestamps, unit & symbol normalization |
| **Order book / trades** | Top-of-book, depth, spread, signed trade flow, OFI | 5m–15m | Event-time ordering, snapshot vs delta, sequence checks, latency logs |
| **Options** | Implied volatility term structure, skew | Volatility/tail risk | Provider access, expiry correctness; no synthetic fallbacks |
| **Cross-market** | Selected crypto, equity proxies, USD/rates | 1h–7d hypotheses | Trading-hours alignment, publication lag, time-zone policy |
| **On-chain** | Exchange flows, active network measures | Slower contexts | Publication lag, vendor semantics, missing-data handling |
| **News/events** | Time-stamped event labels / sentiment | Optional experiment | No look-ahead; archive timestamp, source, model version |

### 6.2 Feature policy
Every feature must have a documented hypothesis, source, timestamp contract, transform, target/horizon scope, missing-data policy, ablation test and maintenance cost. Added in small preregistered groups.

Priority feature candidates:
1. Realized volatility: daily/weekly/monthly realized variance, semivariances, jumps, vol-of-vol.
2. Volatility term structure: ratios across recent windows, options IV/RV gaps when genuine.
3. Microstructure: OFI, depth imbalance, spread, microprice, signed volume.
4. Derivatives: funding changes, open-interest changes, basis, liquidation intensity.
5. Cross-market: BTC correlation with crypto and equity indices.
6. Regime/trajectory: return trajectory, trend/chop, jump indicators.
7. On-chain/event: slower moving, tested separately at suitable horizons.

---

## 7. Model and Evaluation Standards

### 7.1 Baseline-first evaluation
- **Direction:** majority class, zero-drift, lagged sign, simple momentum/reversion.
- **Realized variance:** HAR-RV/HAR-RS-DOW, EWMA, persistence baselines.
- **Quantiles/excursions:** unconditional historical quantiles, volatility-scaled quantiles.
- **Strategy economics:** no-trade and simple predeclared execution policies.

### 7.2 Validation protocol
- Chronological walk-forward splits with purging and embargoing.
- Reserve an untouched final chronological holdout.
- Non-overlapping outcomes or block-bootstrap resampling (never treat overlapping labels as independent).
- Paired model comparisons, effect sizes, and corrected significance tests.
- Record all experiments (including negative findings). Freeze test plan prior to holdout evaluation.
- Calculate Probability of Backtest Overfitting (PBO) / Deflated Sharpe Ratio (DSR) where multiple trials exist.
- Distinguish historical replay from prospective forward forecasts recorded prior to event resolution.

### 7.3 Metric contracts

| Task | Primary metric | Supporting views |
| :--- | :--- | :--- |
| **Direction** | Balanced accuracy & MCC; directional hit rate | ROC-AUC, calibrated Brier score, selective coverage, block CIs, regime slices |
| **Continuous return** | MAE / RMSE and out-of-sample $R^2$ vs zero-return | Error distribution, regime stability |
| **Realized volatility** | QLIKE on defined variance target | MSE/RMSE, regime loss, uncertainty calibration |
| **Quantile distribution**| Pinball loss | Coverage by quantile, sharpness, conditional failure |
| **Prediction interval** | Empirical coverage & Winkler/interval score | Width, breach magnitude, block CIs, tail/regime slices |
| **Strategy research** | Net expectancy & risk-adjusted return | Drawdown, turnover, fees, spread, slippage, funding, capacity |

---

## 8. CPU-First Technical Architecture (No Dedicated GPU)

Local environment: Intel Core i7-13620H CPU, 16 GB RAM, Intel integrated graphics (no CUDA GPU).

### 8.1 Stack
- **API/Product:** FastAPI backend, vanilla HTML/CSS/JavaScript Research Terminal.
- **Data processing:** NumPy, pandas, Polars/DuckDB/Parquet for large historical data.
- **Classical models:** scikit-learn, statsmodels, LightGBM (`device_type=cpu`).
- **Calibration:** conformal modules, SciPy, stationary/moving block-bootstrap.
- **Storage/Provenance:** SQLite, Parquet, JSON manifests, immutable ledger records.

### 8.2 Resource rules
- No transformer training from scratch on the local laptop.
- Use hourly/5m aggregates as primary; 1m/tick data only for isolated experiments.
- Stream or partition large datasets; do not duplicate multi-million row DataFrames in memory.
- Bound CPU concurrency to prevent system freezing.

---

## 9. User Experience Requirements

The Research Terminal makes the distinction between observed market data, model output, and research evidence explicit.

### 9.1 Core views
- **Market Monitor:** verified quotes, candle freshness, provider status, realized volatility.
- **Forecast Lab:** horizon selector, target, quantiles, optional directional probability, model identity, abstention status.
- **Research Evidence:** benchmark comparisons, effective sample size, chronological evaluation windows, confidence intervals, regime slices, manifests.
- **Calibration & Failures:** realized coverage, interval width, drift, large breaches, stale data flags.
- **Model Registry:** artifact hash, trained-through timestamp, feature schema, validation status, limitations, supersession links.
- **Forecast Ledger:** immutable forecasts with delayed resolved outcomes.

### 9.2 UI status vocabulary
`OBSERVED_MARKET_DATA`, `HISTORICAL_RESEARCH_RESULT`, `EXPERIMENTAL_MODEL`, `SHADOW_EVALUATION`, `AUTHORIZED_VOLATILITY_FORECAST`, `BLOCKED_PROVENANCE`, `STALE_DATA`, `INSUFFICIENT_HISTORY`, `OUT_OF_DISTRIBUTION`, `NO_DIRECTIONAL_EDGE`, `ABSTAINED`.

---

## 10. Phased Implementation Roadmap

- **Phase 0 — Repository and model-identity audit (Current):** Reconcile registry, model cards, endpoints, artifact hashes, and test reproducibility.
- **Phase 1 — Data contracts and forecast ledger:** UTC event schemas, freshness checks, lookahead audits, immutable forecast ledger, deterministic delayed resolution.
- **Phase 2 — Canonical baselines and evaluation engine:** Standardized target definitions, walk-forward splits, canonical evaluation CLI, paired bootstrap CIs.
- **Phase 3 — Incremental feature research:** Preregistered feature ablations (HAR volatility, cross-market, derivatives, order flow).
- **Phase 4 — Specialist models and regime-conditioned routing:** CPU-friendly Ridge, LightGBM, return-trajectory conditioning, regime-conditioned gating.
- **Phase 5 — Calibration, selective prediction and the 90% hypothesis:** Causal calibration, selective abstention, freeze thresholds, run the preregistered 90% directional hypothesis.
- **Phase 6 — Prospective shadow evaluation and economic validation:** Forward shadow ledger, cost stress tests, PBO/DSR analysis.
- **Phase 7 — Research Terminal integration and controlled release:** Traceable forecast-to-evidence UI, health alerts, release checklist.

---

## 11. Release Gates

- **G0 (Identity):** Artifact hash, target, horizon, feature schema, provenance manifest verified.
- **G1 (Data):** Causal timestamp contracts pass; no synthetic fallback.
- **G2 (Benchmark):** Reproducible comparison against proper target-specific baseline.
- **G3 (Statistical value):** Predeclared paired comparison with selection-bias controls.
- **G4 (Calibration):** Causal calibration; interval/probability diagnostics by regime pass.
- **G5 (Economics):** Cost-aware validation for any economic/trading claims.
- **G6 (Prospective evidence):** Prospective forecasts logged before outcomes; adequate independent sample size.
- **G7 (Product safety):** API and UI status consistency, all failure modes tested.

---

## 12. Scope Exclusions

- Automatic real-money trading or broker order execution.
- Guaranteed 90% directional accuracy or guaranteed profitability.
- Automatic retraining or model replacement without research approval.
- Unsupported “AI confidence” or fabricated TP/SL levels.
- LLMs replacing numeric evaluation or inventing market narratives.
- Training large deep-learning transformers locally.
- Unnecessary full-stack rewrites.
- Paid data subscriptions without licensing and source review.

---

## 13. Research References

- **R1:** Corsi, F. (2009). *A Simple Approximate Long-Memory Model of Realized Volatility.* Journal of Financial Econometrics, 7(2), 174–196.
- **R2:** Jaquart, P., Dann, D., & Weinhardt, C. (2021). *Short-term bitcoin market prediction via machine learning.* Journal of Finance and Data Science, 7, 45–66.
- **R3:** Yae, J., & Tian, G. Z. (2022). *Out-of-sample forecasting of cryptocurrency returns: A comprehensive comparison of predictors and algorithms.* Physica A, 598, 127379.
- **R4:** Yi, Y., He, M., & Zhang, Y. (2022). *Out-of-sample prediction of Bitcoin realized volatility: Do other cryptocurrencies help?* North American Journal of Economics and Finance, 62, 101731.
- **R5:** Xu, C., & Xie, Y. (2021). *Conformal Prediction Interval for Dynamic Time-Series.* ICML, PMLR 139, 11559–11569.
- **R6:** Rudkin, S., Rudkin, W., & Dłotko, P. (2025). *Return trajectory and the forecastability of bitcoin returns.* Financial Review, 60, 509–539.
- **R7:** Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2015). *The Probability of Backtest Overfitting.* Journal of Computational Finance.
- **R8:** Bailey, D. H., & López de Prado, M. (2014). *The Deflated Sharpe Ratio.* Journal of Portfolio Management, 40(5), 94–107.
- **R9:** Cont, R., Kukanov, A., & Stoikov, S. (2014). *The Price Impact of Order Book Events.* Journal of Financial Econometrics, 12(1), 47–88.
- **R10:** Nagula, P. K., & Alexakis, C. (2022). *A new hybrid machine learning model for predicting the bitcoin (BTC-USD) price.* Journal of Behavioral and Experimental Finance, 36, 100741.
- **R11:** Arain, H. (2026). *When Are Statistical Forecast Gains Economically Relevant? Evidence From Bitcoin Returns.* International Journal of Forecasting.
