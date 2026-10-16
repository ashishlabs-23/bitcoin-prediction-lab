# BTCognitive Stage 7: Research-Driven Regime-Conditioned Prediction and Signal Discovery

**Execution Date:** October 16, 2026  
**Auditor / Quantitative Research Role:** Independent Quantitative Researcher, Financial Machine Learning Engineer, Microstructure Auditor  
**Repository Working Tree:** `c:/Projects/BTCognitive/BTCognitive`  
**Git Branch:** `main` | **Active Commit:** `50e362e` (Clean working tree relative to production contracts)  
**Machine-Readable Artifact:** [`stage7_experiment_results.json`](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/stage7_regime_research/stage7_experiment_results.json)  
**Reproducible Research Pipeline:** [`stage7_regime_experiments.py`](file:///c:/Projects/BTCognitive/BTCognitive/research/stage7_regime_experiments.py)  
**Verification Test Suite:** [`test_stage7_regime_experiments.py`](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_stage7_regime_experiments.py) (5/5 Passing)  
**Production Gate Model:** `HAR-RS-DOW-v1.0` (Classification: `PRODUCTION_VOLATILITY`, Authorization: `AUTHORIZED_FOR_PRODUCTION`)  
**Offline Research Baseline:** `directional-gbm-4lag-v1` (Classification: `DIRECTIONAL_RESEARCH_BENCHMARK`, Authorization: `OFFLINE_RESEARCH_ONLY`)

---

## Executive Summary

Stage 7 investigated the central empirical question: **Does Bitcoin's 1-hour directional return predictability vary meaningfully across objectively defined market states (volatility regimes, trend states, and return trajectory paths), and can conditioning on those states produce reliable, reproducible out-of-sample forecasting improvements over the global 4-lag baseline?**

Following the disciplined quantitative research methodology established in Stage 6, we formulated a falsifiable hypothesis ($H_1$), conducted in-depth external literature synthesis across six peer-reviewed publications, strictly enforced causal in-train regime thresholding across 5 purged walk-forward folds ($N = 33,919$ out-of-sample test bars spanning 2022 to 2026), and executed a 3-tier controlled experimental ladder.

### Key Empirical Findings

1. **Falsification of Hypothesis $H_1$:**
   Conditioning models on volatility regimes, trend states, or return trajectory paths **does not** yield statistically significant out-of-sample predictive gains over the global 4-lag baseline.
   - **Global 4-Lag GBDT Baseline:** $53.28\%$ accuracy ($ROC\text{-}AUC = 0.5445$, Brier score $= 0.2488$, Train time $= 13.29\text{s}$).
   - **Challenger 1 (GBDT + Causal Regime Interactions):** $53.23\%$ accuracy ($\Delta = -0.05\%$, paired bootstrap $p = 0.6154$, McNemar $p = 0.6507$, Holm-Bonferroni adjusted $p = 1.000$).
   - **Challenger 2 (Logistic Regression + Regime Interactions):** $53.06\%$ accuracy ($\Delta = -0.22\%$, paired bootstrap $p = 0.3448$, McNemar $p = 0.3458$, Holm-Bonferroni adjusted $p = 1.000$).
   - **Challenger 3 (Regime-Partitioned GBDT):** $52.83\%$ accuracy ($\Delta = -0.45\%$, unadjusted $p = 0.0357$, Holm-Bonferroni adjusted $p = 0.1785$). Partitioning the training dataset into separate volatility subsets **degrades** predictive accuracy by fragmenting training sample size and elevating model variance.
   - **Challenger 4 (Regime-Partitioned Logistic Regression):** $53.39\%$ accuracy ($\Delta = +0.11\%$, paired bootstrap $p = 0.5930$, McNemar $p = 0.6061$, Holm-Bonferroni adjusted $p = 1.000$). Statistically indistinguishable from baseline.

2. **Resolution of Apparent Trajectory Differences:**
   While the canonical 4-lag model achieved $54.37\%$ accuracy on the `Traj_Bear_Push` state ($ret_{24h} \le 0$ and $ret_{1h} \le 0$) and $51.38\%$ on `Traj_Bear_Bounce` ($ret_{24h} \le 0$ and $ret_{1h} > 0$), rigorous diagnostic decomposition proves this is **not** an alpha discovery. Rather, it is an artifact of conditional class balance shifts: in the `Traj_Bear_Push` state, the empirical probability of a positive bounce in the subsequent hour is $54.81\%$. The baseline majority-class predictor ($54.81\%$) actually outperforms the GBDT model ($54.37\%$). When evaluated by balanced accuracy, the model scores a near-random $50.71\%$.

3. **Persistent Economic Barrier (Transaction Friction Gap):**
   In selective prediction evaluations, causal confidence thresholds raised directional accuracy from $53.28\%$ (100% coverage) to $56.81\%$ at $5.1\%$ coverage. However, net trading expectancy remained **severely negative** after realistic market friction:
   - **Institutional Tier A (14 bps round-trip):** $-4.12$ to $-5.19\text{ bps/bar}$.
   - **Retail Tier B (35 bps round-trip):** $-11.64$ to $-13.94\text{ bps/bar}$.
   High turnover (averaging $1.70$ transitions per active bar) ensures that fee decay rapidly consumes raw gross margins ($+0.19$ to $+1.93\text{ bps/bar}$). Directional accuracy without cost-aware holding filters cannot generate economic alpha.

4. **External Data Opportunity Verification:**
   Audit of raw repository data verified that derivative and on-chain histories are severely truncated:
   - `funding.parquet`: Exactly 375 rows (Jan–May 2026).
   - `oi.parquet`: Exactly 3,000 rows (Jan–May 2026).
   - `onchain.parquet`: Exactly 30 rows (Sep–Oct 2026).
   - `ohlcv.parquet`: 40,902 rows (40,702 usable hourly bars spanning 2022–2026).
   Integrating derivatives or on-chain feeds into the current 4-year walk-forward matrix would discard over $90\%$ of the canonical evaluation history. Acquisition of multi-year, point-in-time funding and order-flow data is identified as the only defensible route to genuine incremental feature discovery.

5. **Architectural & Governance Recommendation:**
   **STOP** adding model complexity or expanding technical feature engineering on price-only OHLCV. Preserve `HAR-RS-DOW-v1.0` as the sole authorized production risk/volatility model. Maintain directional models strictly in offline research mode.

---

## 1. Repository State and Governance Verification

Before initiating Stage 7 experiments, an exhaustive audit of the repository state, commit lineage, model registry, and runtime configuration was completed:

- **Git Status:** Clean working tree on `main` branch. Active commit `50e362e` (`docs(research): empirical directional accuracy audit and 70% feasibility report`). All changes for Stage 7 remain strictly local without remote pushes or branch branching.
- **Model Registry Lineage:** Verified against [`authoritative_model_registry.py`](file:///c:/Projects/BTCognitive/BTCognitive/models/authoritative_model_registry.py):
  - **Active Production Model:** `HAR-RS-DOW-v1.0` (Version `1.0.0`). Authorized exclusively for 7-day realized variance forecasting and C2 conformal risk envelopes. Directional prediction capability: `False`.
  - **Directional Research Baseline:** `directional-gbm-4lag-v1` (Version `1.0.0`). Offline benchmark only. Directional prediction capability: `True`. Status: `OFFLINE_RESEARCH_ONLY`.
  - **Archived Candidate:** `ridge_excursion_core` (Version `v3.0.0-excursion-ridge-conformal`). Status: `BLOCKED_PROVENANCE_UNVERIFIED`.
- **Runtime Startup Gate:** Verified against [`startup_gate.py`](file:///c:/Projects/BTCognitive/BTCognitive/validation/startup_gate.py). Any attempt to pass an unauthorized directional model into production inference routes (`/api/terminal/live`) fails closed with an HTTP 403 / SystemExit exception.
- **Experimental Isolation:** All Stage 7 feature pipelines, causal regime transformations, and model evaluations are strictly isolated in `research/stage7_regime_experiments.py` and output to `experiments/results/stage7_regime_research/`. Zero production routes or schemas were altered.

---

## 2. Verified Research Baseline and Canonical Distinctions

The canonical Stage 6 baseline metrics were reproduced across 5 purged walk-forward folds on 40,702 total hourly bars (33,919 out-of-sample evaluated test bars spanning January 2022 to September 2026):

| Baseline Model / Configuration | OOS Directional Accuracy | Balanced Accuracy | ROC-AUC | Brier Score | ECE | Train Time | Verified Role |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **GBDT (4 Lags)** (`directional-gbm-4lag-v1`) | **53.28%** | 53.27% | 0.5445 | 0.2488 | 0.0122 | 13.29s | Primary Directional Research Benchmark |
| **L2 Logistic Regression (4 Lags)** | **53.20%** | 53.10% | 0.5419 | 0.2489 | 0.0131 | 0.06s | Fast Linear Challenger (221x speedup) |
| **GBDT (High-Confidence 10% Hurdle)** | **55.96%** | 55.84% | N/A | N/A | N/A | N/A | Selective Prediction Benchmark (10.0% coverage) |
| **GBDT (High-Confidence 5% Hurdle)** | **56.81%** | 56.62% | N/A | N/A | N/A | N/A | Selective Prediction Benchmark (5.1% coverage) |

### Critical Methodological Distinctions

To avoid common pitfalls in financial machine learning, the following distinctions are strictly maintained:
1. **Directional Accuracy vs. Probability Discrimination:** A model can achieve $53.28\%$ binary accuracy while exhibiting minimal probability discrimination ($ROC\text{-}AUC = 0.5445$, where $0.5000$ is random). Log loss ($0.6908$) and Brier score ($0.2488$) confirm that predicted probabilities cluster tightly around the base rate ($0.48 - 0.52$).
2. **Directional Accuracy vs. Selective Conditional Accuracy:** Filtering predictions by confidence increases empirical accuracy on the retained subset ($56.81\%$ at $5.1\%$ coverage), but rejects $94.9\%$ of trading opportunities.
3. **Forecast Coverage vs. Risk-Envelope Containment:** `HAR-RS-DOW-v1.0` achieves $92.84\%$ empirical holdout containment for its $90\%$ nominal conformal volatility envelope. Conformal quantile coverage measures uncertainty dispersion, whereas directional accuracy measures price sign classification. They are mathematically distinct.
4. **Forecast Quality vs. Net Trading Profitability:** A positive gross return per active bar ($+0.19\text{ bps}$) is completely swamped by bid-ask spread, slippage, and taker commissions ($-5.12\text{ bps}$ net at 14 bps round-trip). High directional accuracy does not imply a tradable strategy.
5. **Statistical vs. Economic Significance:** A tiny accuracy advantage ($\Delta = +0.11\%$) may appear in sample, but fails statistical significance tests ($p = 0.5930$) and provides negative economic value after execution friction.

---

## 3. Focused External Literature Research & Comparison

Six foundational peer-reviewed studies were audited to guide hypothesis selection, regime construction, and evaluation discipline.

### Literature Comparison Matrix

| Study | Asset & Frequency | Forecast Horizon | Validation Protocol | Key Methodological Findings | Relevance & Applicability to BTCognitive |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Rudkin, Rudkin, & Dłotko (2025)**<br>*Financial Review*<br>DOI: [10.1111/fire.12420](https://doi.org/10.1111/fire.12420) | Bitcoin (BTC-USD)<br>Daily & Intraday | 1-step Ahead Return Direction | Topological Data Analysis (Ball Mapper - TDABM) | Return predictability is highly localized. Certain return trajectory paths exhibit higher conditional predictability, while the global space resembles a random walk. High-accuracy subsets suffer from small sample sizes. | Informs our Trajectory Pattern state definitions (Combinatorial path signs). Demonstrates that apparent high-accuracy balls in TDA often reflect localized drift rather than stable alpha. |
| **Yae & Tian (2022)**<br>*Physica A*<br>DOI: [10.1016/j.physa.2022.127379](https://doi.org/10.1016/j.physa.2022.127379) | Major Cryptos<br>Daily Returns | 1-day Forward Returns | Rolling out-of-sample comparison across dozens of ML models and predictors | Complex non-linear models and technical indicators heavily overfit in-sample and fail out-of-sample. Penalized linear models (L2 Ridge / Lasso) consistently match or exceed complex ML trees. | Explains why L2 Logistic Regression matches GBDT ($53.20\%$ vs $53.28\%$) in BTCognitive. Warns against unmotivated feature engineering. |
| **Li et al. (2026)**<br>*Pacific-Basin Finance Journal*<br>DOI: [10.1016/j.pacfin.2025.103033](https://doi.org/10.1016/j.pacfin.2025.103033) | Cross-Sectional Cryptocurrencies<br>Daily | Multi-day Cross-Sectional Returns | High-dimensional factor modeling with 12 ML algorithms and SHAP interpretability | Macroeconomic and price technicals provide weak marginal power. On-chain metrics (MVRV, active addresses, network growth) dominate feature importance and provide genuine incremental information. | Confirms that price-lag features face an informational ceiling. Fundamental improvements require external on-chain or microstructure data, but notes these are daily/weekly factors. |
| **Hewamalage, Ackermann, & Bergmeir (2023)**<br>*Data Mining and Knowledge Discovery*<br>DOI: [10.1007/s10618-022-00894-5](https://doi.org/10.1007/s10618-022-00894-5) | General Time Series<br>Multi-frequency | Multi-step Time Series | Comprehensive tutorial on forecasting pitfalls | Documents critical flaws: temporal data leakage, inadequate naive baselines, non-causal preprocessing, and failure to account for autocorrelation in uncertainty estimation. | Dictates our validation standards: purged walk-forward splits, training-only regime threshold derivation, majority-class baseline reporting, and moving-block bootstrap uncertainty. |
| **Bysik & Ślepaczuk (2026)**<br>*arXiv:2406.00060*<br>[arXiv:2406.00060](https://arxiv.org/abs/2406.00060) | Bitcoin (BTC-USDT)<br>Hourly (~70,000 bars) | 1-hour Forward Log Return | 27-fold walk-forward validation (XGBoost, LSTM, iTransformer) under costs | Naive sign-based trading produces positive gross returns but collapses into severe losses under 10–14 bps costs. A cost-aware hurdle filter is required to reduce turnover and achieve profitability. | Directly validates Stage 6 and Stage 7 economic findings: naive hourly execution loses $-5.12\text{ bps/trade}$ due to excessive turnover ($75.9\%$). Execution filtering is mandatory. |
| **Arian, Mobarekeh, & Seco (2024)**<br>*Knowledge-Based Systems*<br>DOI: [10.1016/j.knosys.2024.112477](https://doi.org/10.1016/j.knosys.2024.112477) | Financial Time Series<br>Daily & Intraday | Forward Path Prediction | Combinatorial Purged Cross-Validation (CPCV) and PBO analysis in synthetic environments | Sequential model selection on a fixed historical holdout leads to severe backtest overfitting and false discovery. Multiplicity controls (Holm-Bonferroni) and prospective testing are essential. | Mandates classifying all historical holdout experiments as exploratory, requiring Holm-Bonferroni correction across challenger models, and enforcing prospective shadow validation. |

---

## 4. Pre-Registered Research Hypotheses and Evaluation Plan

### Primary Research Hypothesis $H_1$ (Falsifiable)
> **$H_1$:** *Bitcoin's 1-hour directional return predictability varies across objectively defined market states (volatility regimes, trend states, or return trajectory paths), and a simple model conditioned on those states outperforms the existing global 4-lag baseline on some states without sacrificing robustness across the full evaluation period.*

### Pre-Registered Acceptance Criteria
To accept $H_1$, a challenger model must satisfy ALL of the following:
1. **Statistical Outperformance:** Achieve a statistically significant improvement over the global 4-lag baseline ($\Delta_{\text{acc}} > 0$) with a moving-block bootstrap $p < 0.05$ and McNemar test $p < 0.05$, surviving Holm-Bonferroni family-wise error rate control.
2. **Temporal Robustness:** Outperform or match the baseline across at least 4 of the 5 chronological walk-forward folds without catastrophic degradation in any single period.
3. **Economic Viability:** Demonstrate positive net return expectancy after accounting for 14 bps institutional transaction friction.
4. **No Chasing of 70% Accuracy:** The evaluation must reflect the entire out-of-sample test set ($N = 33,919$) or pre-declared coverage tiers, without cherry-picking arbitrary micro-regimes.

### Causal Market State Definitions

All regime boundaries and thresholds are determined **strictly from the training data** available within each walk-forward fold. Zero full-sample quantiles or future lookahead were permitted.

1. **Volatility Regimes (3 States — In-Train Terciles):**
   - Metric: 24-hour realized volatility $\sigma_{24h} = \text{std}(r_{1h})_{24}$.
   - Causal Boundaries: In-train 33.33% percentile ($\theta_{vol,1}$) and 66.67% percentile ($\theta_{vol,2}$).
   - States: `Vol_Low` ($\sigma_{24h} \le \theta_{vol,1}$), `Vol_Normal` ($\theta_{vol,1} < \sigma_{24h} \le \theta_{vol,2}$), `Vol_High` ($\sigma_{24h} > \theta_{vol,2}$).
2. **Trend Regimes (3 States — In-Train Terciles):**
   - Metric: 24-hour log return $r_{24h} = \ln(Close_t / Close_{t-24})$.
   - Causal Boundaries: In-train 33.33% percentile ($\theta_{trend,1}$) and 66.67% percentile ($\theta_{trend,2}$).
   - States: `Trend_Bear` ($r_{24h} \le \theta_{trend,1}$), `Trend_Range` ($\theta_{trend,1} < r_{24h} \le \theta_{trend,2}$), `Trend_Bull` ($r_{24h} > \theta_{trend,2}$).
3. **Return-Trajectory Patterns (4 States — Point-in-Time Signs):**
   - Metric: Interaction of session momentum ($r_{24h}$) and immediate hourly momentum ($r_{1h}$).
   - States:
     - `Traj_Bull_Push`: $r_{24h} > 0$ and $r_{1h} > 0$ (Session uptrend with immediate upward continuation).
     - `Traj_Bull_Pullback`: $r_{24h} > 0$ and $r_{1h} \le 0$ (Session uptrend with immediate hourly dip).
     - `Traj_Bear_Push`: $r_{24h} \le 0$ and $r_{1h} \le 0$ (Session downtrend with immediate downward continuation).
     - `Traj_Bear_Bounce`: $r_{24h} \le 0$ and $r_{1h} > 0$ (Session downtrend with immediate counter-trend bounce).

---

## 5. Experiment Ladder Execution & Empirical Results

### Experiment A: Conditional Performance Diagnostics across Regimes

Without modifying the forecasting model, we measured the performance of the canonical 4-lag GBDT and Logistic Regression baselines across all causal market states over 33,919 out-of-sample observations.

#### Comprehensive Diagnostic Results

| Regime Family | Market State | Sample Count $N$ | Dataset Coverage | Class Balance (% Up) | Majority Baseline | GBDT Accuracy | Wilson 95% CI | Fold Dispersion (Acc %) | Delta vs Global | Bootstrap $p$-value | LogReg Accuracy |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Volatility** | `Vol_Low` | 15,759 | 46.46% | 50.46% | 50.46% | 53.21% | [52.43, 53.99] | [54.1, 54.0, 53.3, 52.2, 52.0] | -0.07% | 0.8619 | 53.14% |
| | `Vol_Normal` | 10,998 | 32.42% | 50.43% | 50.43% | 53.15% | [52.21, 54.08] | [54.3, 53.5, 53.3, 52.1, 53.0] | -0.13% | 0.7651 | 53.24% |
| | `Vol_High` | 7,162 | 21.12% | 51.52% | 51.52% | 53.63% | [52.47, 54.78] | [53.6, 55.3, 54.9, 51.0, 52.4] | +0.35% | 0.5122 | 53.30% |
| **Trend** | `Trend_Bear` | 9,977 | 29.41% | 53.13% | 53.13% | 53.38% | [52.40, 54.36] | [53.7, 53.9, 54.8, 53.1, 51.6] | +0.10% | 0.8265 | 53.49% |
| | `Trend_Range`| 12,939 | 38.15% | 50.85% | 50.85% | 52.74% | [51.88, 53.60] | [53.7, 53.4, 51.6, 51.5, 52.9] | -0.54% | 0.1947 | 52.82% |
| | `Trend_Bull` | 11,003 | 32.44% | 48.24% | 51.76% | 53.82% | [52.89, 54.75] | [55.0, 55.2, 54.7, 51.2, 52.9] | +0.54% | 0.2457 | 53.39% |
| **Trajectory**| `Traj_Bull_Push` | 9,707 | 28.62% | 45.73% | 54.27% | 53.93% | [52.94, 54.92] | [54.8, 54.6, 54.5, 52.4, 53.2] | +0.65% | 0.1705 | 54.07% |
| | `Traj_Bull_Pullback`| 7,939 | 23.41% | 52.32% | 52.32% | 53.07% | [51.97, 54.16] | [53.3, 53.9, 53.4, 51.4, 53.3] | -0.21% | 0.6973 | 52.53% |
| | `Traj_Bear_Push` | 8,791 | 25.92% | 54.81% | 54.81% | 54.37% | [53.33, 55.41] | [54.3, 56.6, 55.2, 53.9, 52.3] | +1.09% | 0.0338 | 54.48% |
| | `Traj_Bear_Bounce` | 7,482 | 22.06% | 50.48% | 50.48% | 51.38% | [50.24, 52.51] | [53.6, 50.9, 51.8, 49.7, 50.9] | -1.90% | 0.0011 | 51.30% |

#### Deep-Dive Analysis of Experiment A Diagnostics

1. **Volatility Invariance:** Across low ($53.21\%$), normal ($53.15\%$), and high ($53.63\%$) volatility regimes, the baseline GBDT model exhibits nearly identical directional accuracy. The paired bootstrap test against the global baseline yields $p$-values of $0.86$, $0.77$, and $0.51$. All Wilson 95% confidence intervals overlap extensively. Directional predictability does not systematically expand during high volatility.
2. **Deconstruction of the Trajectory Push Effect:**
   - At first glance, `Traj_Bear_Push` shows higher accuracy ($54.37\%$, unadjusted $p = 0.0338$). However, examining the empirical class balance reveals that **$54.81\%$ of forward returns in this state are positive** (reflecting strong intraday mean-reversion following downward session momentum).
   - A naive majority-class predictor achieves **$54.81\%$ accuracy**, which is strictly superior to the machine learning model ($54.37\%$).
   - The balanced accuracy of GBDT on `Traj_Bear_Push` is only **$50.71\%$**, and its ROC-AUC collapses to **$0.5221$**.
   - Similarly, in `Traj_Bull_Push`, the empirical majority class is $54.27\%$ downward, while GBDT achieves only $53.93\%$ (balanced accuracy $50.70\%$).
   - **Conclusion:** The apparent variation in raw accuracy across trajectory patterns reflects **unconditional base rate shifts (class imbalance drift)** rather than superior conditional information extraction.

---

### Experiment B: Global versus Regime-Conditioned Models

To determine whether incorporating market states directly into model architectures can capture state-dependent dynamics, we evaluated six distinct model configurations across identical out-of-sample walk-forward evaluation slices ($N = 33,919$ test bars).

#### Comparative Model Performance Matrix

| Model Specification | Overall Accuracy | Balanced Accuracy | ROC-AUC | Brier Score | ECE | Train Time | Paired $\Delta_{\text{acc}}$ vs Baseline | Moving-Block Bootstrap 95% CI | Bootstrap $p$-value | McNemar $p$-value | Holm-Bonferroni Adjusted $p$-value | Statistically Significant |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: Global GBDT (4 Lags)** | **53.28%** | 53.27% | 0.5445 | 0.2488 | 0.0122 | 13.29s | Baseline | Baseline | Baseline | Baseline | Baseline | Benchmark |
| **Baseline 2: Global LogReg (4 Lags)** | **53.20%** | 53.10% | 0.5419 | 0.2489 | 0.0131 | 0.06s | -0.08% | [-0.50, +0.36] | 0.7279 | 0.7430 | 1.0000 | No |
| **Challenger 1: GBDT + Regime Interactions** | **53.23%** | 53.21% | 0.5447 | 0.2488 | 0.0124 | 18.48s | -0.05% | [-0.25, +0.15] | 0.6154 | 0.6507 | 1.0000 | No |
| **Challenger 2: LogReg + Regime Interactions** | **53.06%** | 52.98% | 0.5430 | 0.2490 | 0.0069 | 0.11s | -0.22% | [-0.68, +0.26] | 0.3448 | 0.3458 | 1.0000 | No |
| **Challenger 3: GBDT Volatility-Partitioned** | **52.83%** | 52.84% | 0.5379 | 0.2501 | 0.0232 | 12.40s | -0.45% | [-0.86, -0.05] | 0.0357 | 0.0358 | 0.1785 | No |
| **Challenger 4: LogReg Volatility-Partitioned**| **53.39%** | 53.34% | 0.5429 | 0.2490 | 0.0092 | 0.10s | +0.11% | [-0.30, +0.53] | 0.5930 | 0.6061 | 1.0000 | No |

#### Chronological Fold Stability Breakdown

| Model Configuration | Fold 0 (2022-23) | Fold 1 (2023-24) | Fold 2 (2024-25) | Fold 3 (2025-26) | Fold 4 (2026) | Fold Std ($\sigma_{\text{fold}}$) | Min Fold | Max Fold |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: Global GBDT (4 Lags)** | 54.06% | 54.12% | 53.81% | 51.94% | 52.47% | 0.90% | 51.94% | 54.12% |
| **Baseline 2: Global LogReg (4 Lags)** | 54.83% | 54.00% | 53.69% | 51.36% | 52.13% | 1.27% | 51.36% | 54.83% |
| **Challenger 1: GBDT Interactions** | 54.14% | 54.30% | 53.87% | 51.66% | 52.17% | 1.09% | 51.66% | 54.30% |
| **Challenger 2: LogReg Interactions** | 53.97% | 54.02% | 54.00% | 51.53% | 51.76% | 1.15% | 51.53% | 54.02% |
| **Challenger 3: GBDT Partitioned** | 53.80% | 53.31% | 53.24% | 52.01% | 51.78% | 0.79% | 51.78% | 53.80% |
| **Challenger 4: LogReg Partitioned** | 54.80% | 54.31% | 53.59% | 52.35% | 51.92% | 1.11% | 51.92% | 54.80% |

#### Statistical Verdict on Experiment B

1. **Interaction Features Add No Value:** Augmenting GBDT with causal regime indicators and return-volatility interaction terms resulted in a negligible $-0.05\%$ accuracy difference ($p = 0.6154$). For Logistic Regression, interaction features reduced accuracy by $-0.22\%$ ($p = 0.3448$).
2. **Partitioning Trees Causes Sample Starvation:** Challenger 3 (dedicated GBDTs trained exclusively on low, normal, or high volatility subsets) suffered a statistically significant drop in performance before multiplicity correction ($\Delta = -0.45\%$, unadjusted $p = 0.0357$). Dividing 20,000–30,000 training observations into three separate pools reduces tree depth effectiveness, prevents global feature split sharing, and inflates Brier loss ($0.2501$).
3. **Partitioned Linear Model Fails Multiplicity Gate:** Challenger 4 achieved a nominal $+0.11\%$ increase ($53.39\%$ vs $53.28\%$). However, its paired bootstrap confidence interval $[-0.30\%, +0.53\%]$ heavily spans zero ($p = 0.5930$, Holm-Bonferroni adjusted $p = 1.000$).
4. **Primary Hypothesis $H_1$ is REJECTED:** None of the regime-conditioned models satisfy the pre-registered acceptance criteria.

---

### Experiment C: Conditional Decision Quality and Economic Viability

We tested whether regime-conditioned probabilities enable superior selective prediction (abstaining on uncertain forecasts) and whether cost-aware selective filtering can convert statistical signal into positive net economic expectancy.

#### Selective Prediction and Trading Expectancy Comparison

| Model | Coverage Tier | Target Coverage | Empirical Coverage | Active Bars ($N$) | Directional Accuracy | Wilson 95% CI | Hourly Turnover Rate | Gross Return (bps/active bar) | Net Return: Inst. 14 bps (bps/bar) | Net Return: Retail 35 bps (bps/bar) | Economic Viability Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Baseline GBDT** | 100% (Unfiltered) | 100.0% | 100.00% | 33,919 | 53.28% | [52.75, 53.81] | 0.759 | +0.19 | -5.12 | -13.09 | UNPROFITABLE |
| | 50% Coverage | 50.0% | 50.03% | 16,970 | 55.12% | [54.37, 55.87] | 1.121 | +0.30 | -4.48 | -11.64 | UNPROFITABLE |
| | 25% Coverage | 25.0% | 25.04% | 8,492 | 55.69% | [54.63, 56.74] | 1.404 | +0.22 | -5.02 | -12.88 | UNPROFITABLE |
| | 10% Coverage | 10.0% | 10.02% | 3,399 | 55.96% | [54.28, 57.62] | 1.612 | +0.54 | -5.19 | -13.79 | UNPROFITABLE |
| | 5% Coverage | 5.0% | 5.13% | 1,741 | 56.81% | [54.47, 59.12] | 1.732 | +1.35 | -4.77 | -13.94 | UNPROFITABLE |
| **Regime-Interaction GBDT** | 100% (Unfiltered) | 100.0% | 100.00% | 33,919 | 53.23% | [52.70, 53.76] | 0.762 | +0.22 | -5.12 | -13.12 | UNPROFITABLE |
| | 50% Coverage | 50.0% | 50.16% | 17,015 | 55.24% | [54.49, 55.99] | 1.148 | +0.22 | -4.70 | -12.09 | UNPROFITABLE |
| | 25% Coverage | 25.0% | 25.06% | 8,501 | 55.57% | [54.51, 56.62] | 1.435 | +0.66 | -4.71 | -12.77 | UNPROFITABLE |
| | 10% Coverage | 10.0% | 10.03% | 3,403 | 56.51% | [54.84, 58.17] | 1.632 | +1.15 | -4.74 | -13.57 | UNPROFITABLE |
| | 5% Coverage | 5.0% | 5.05% | 1,714 | 56.01% | [53.65, 58.34] | 1.700 | +1.93 | -4.12 | -13.20 | UNPROFITABLE |

#### Economic Analysis and the Prediction-to-Trading Gap

1. **Selective Accuracy Improves, but Remains Under 57%:** Filtering by model confidence steadily improves accuracy from $53.28\%$ to $56.81\%$ for baseline GBDT, and to $56.51\%$ at $10\%$ coverage for the interaction model. However, even under the strictest $5\%$ hurdle ($N = 1,714$ bars), accuracy falls far short of hypothetical $70\%$ claims.
2. **The Turnover Penalty:** As the confidence threshold rises, the model flips between active positions and cash. At the $5\%$ tier, the turnover rate reaches **$1.70 - 1.73$ transitions per active bar**. Each position change incurs transaction friction ($7\text{ bps}$ institutional, $17.5\text{ bps}$ retail per side).
3. **Severe Fee Drag Destroys Alpha:** Gross returns increase with selectivity (reaching $+1.35$ to $+1.93\text{ bps/bar}$ at $5\%$ coverage). However, transaction friction deducts $6.0$ to $16.0\text{ bps/bar}$, resulting in net returns of **$-4.12\text{ bps}$** (institutional) and **$-13.20\text{ bps}$** (retail).
4. **Consistency with Bysik & Ślepaczuk (2026):** Our simulation independently reproduces the findings of Bysik & Ślepaczuk (2026): in 1-hour cryptocurrency forecasting, naive directional signals cannot overcome transaction friction without an execution filter specifically designed to minimize portfolio turnover.

---

## 6. Sensitivity Analysis and Multiplicity Controls

### Robustness across Alternative Parameter Specifications

To verify that conclusions are not artifacts of specific parameter choices, we performed sensitivity audits varying trailing estimation windows:

1. **48-Hour Realized Volatility Terciles:**
   - Low Volatility 48h ($N = 16,703$): $53.05\%$ accuracy ($\Delta = -0.23\%$).
   - Normal Volatility 48h ($N = 10,330$): $53.77\%$ accuracy ($\Delta = +0.49\%$).
   - High Volatility 48h ($N = 6,886$): $53.11\%$ accuracy ($\Delta = -0.17\%$).
   - *Finding:* Expanding the volatility lookback from 24h to 48h maintains the same result: no statistically significant predictive divergence across volatility regimes.
2. **50-Bar Simple Moving Average Ratio (`sma_ratio_50`):**
   - Bearish Trend ($N = 9,670$): $53.25\%$ accuracy ($\Delta = -0.03\%$).
   - Range-Bound Trend ($N = 12,891$): $52.70\%$ accuracy ($\Delta = -0.58\%$).
   - Bullish Trend ($N = 11,358$): $53.97\%$ accuracy ($\Delta = +0.69\%$).
   - *Finding:* Filtering by trend relative to moving averages exhibits minor variations ($52.7\%$ to $54.0\%$), all spanning the baseline $53.28\%$.

### Multiplicity Control via Holm-Bonferroni Procedure

Across the family of 5 challenger comparisons in Experiment B, raw $p$-values were adjusted to control the Family-Wise Error Rate (FWER):
- `challenger_gbdt_vol_partitioned`: Raw $p = 0.0357 \rightarrow$ Adjusted $p = 0.1785$ (Not significant).
- `challenger_logistic_regime_interactions`: Raw $p = 0.3448 \rightarrow$ Adjusted $p = 1.0000$ (Not significant).
- `challenger_logistic_vol_partitioned`: Raw $p = 0.5930 \rightarrow$ Adjusted $p = 1.0000$ (Not significant).
- `challenger_gbdt_regime_interactions`: Raw $p = 0.6154 \rightarrow$ Adjusted $p = 1.0000$ (Not significant).
- `baseline_logistic_4lags`: Raw $p = 0.7279 \rightarrow$ Adjusted $p = 1.0000$ (Not significant).

Zero challenger models achieved statistical significance after multiplicity adjustment.

---

## 7. Data Opportunity Matrix & External Input Evaluation

The Stage 6 and Stage 7 reports emphasize that price-only OHLCV data has reached an informational asymptote. Before considering external data acquisition, we audited the actual historical availability and point-in-time integrity of potential features.

### Empirical Audit of Existing Repository Parquet Feeds

```
+---------------------------------------------------------------------------------------------------+
| Dataset File           | Rows    | Span Min                   | Span Max                   | Usable % |
+---------------------------------------------------------------------------------------------------+
| data/raw/ohlcv.parquet   | 40,902  | 2022-01-01 00:00:00+00:00  | 2026-09-01 06:00:00+00:00  | 100.0%   |
| data/raw/funding.parquet | 375     | 2026-01-01 00:00:00+00:00  | 2026-05-05 16:00:00+00:00  | 0.9%     |
| data/raw/oi.parquet      | 3,000   | 2026-01-01 00:00:00+00:00  | 2026-05-05 23:00:00+00:00  | 7.3%     |
| data/raw/onchain.parquet | 30      | 2026-09-16 15:01:29+00:00  | 2026-10-15 15:01:29+00:00  | 0.07%    |
+---------------------------------------------------------------------------------------------------+
```

### Data Opportunity Matrix

| Candidate Data Stream | Proposed Mechanism | Frequency & Historical Depth Required | Availability & Cost in Repository | Point-in-Time & Survivorship Risks | Research Priority | Justification & Preconditions |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Funding Rates & Open Interest** | Derivatives leverage positioning & liquidation squeeze risk | Hourly observations matching 2022–2026 ($>35,000$ bars) | **Severely Incomplete:** `funding.parquet` has only 375 bars; `oi.parquet` has only 3,000 bars. Free API endpoints available. | Exchange timestamp alignment, funding rate payment conventions (8h vs continuous), backfill survivorship bias. | **High (Research Only)** | Must acquire continuous 4-year historical parquet from major exchanges (Binance, Bybit) with verified point-in-time timestamps before modeling. |
| **On-Chain Valuation (MVRV, Realized Cap, SOPR)** | Structural network accumulation & aggregate holder profit/loss state | Daily aggregated metrics (expanded hourly via forward-fill) for 2020–2026 | **Severely Incomplete:** Repository contains only 30 daily observations (Sep–Oct 2026). Requires node or paid API (Glassnode/CryptoQuant). | Restatement risks, block timestamp reorgs, reporting lags (2–6 hours), forward-fill lookahead. | **Medium (Evaluate)** | Informs multi-day or weekly regime shifts (as proven by Li et al. 2026), but unlikely to resolve 1-hour directional noise. High cost. |
| **Macro Risk Variables (DXY, US 10Y, SPX Futures)** | Global liquidity proxy and risk-on/risk-off sentiment transmission | Hourly synchronized market bars (accounting for market closures) | Absent in repository. Available via Yahoo Finance / FRED / Interactive Brokers. | Trading session mismatches (24/7 crypto vs 23/5 macro), holiday closures, stale price propagation. | **Medium (Evaluate)** | Useful for cross-asset spillover modeling during US cash open. Must verify causal availability timestamps. |
| **Order Book Depth & Event Microstructure** | Short-horizon order flow toxicity, bid-ask queue imbalance | Tick / sub-second L2/L3 order book depth | **Absent:** Repository has only live websocket snapshot capability; zero multi-year historical depth. Extremely high storage ($>1\text{TB}$). | Timestamp drift, exchange colocation differences, microsecond latency simulation, prohibitive storage costs. | **Low (Defer)** | Unjustified for 1-hour horizon. Order flow imbalance alpha decays within seconds to minutes. Prohibitive cost and complexity. |

---

## 8. Test Execution and Verification Audit

All Stage 5, Stage 6, and Stage 7 verification test suites were executed to ensure quantitative integrity and system consistency.

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-8.4.1, pluggy-1.6.0
rootdir: C:\Projects\BTCognitive\BTCognitive
collected 19 items

tests\test_stage5_dependency_and_model_identity.py .........             [ 47%]
tests\test_stage6_feature_parity_and_runtime_verification.py .....       [ 73%]
tests\test_stage7_regime_experiments.py .....                            [100%]

======================= 19 passed, 1 warning in 12.69s ========================
```

### Exact Audit Breakdown of Completed Tests
1. `test_stage7_results_file_exists_and_valid`: PASSED. Confirms `stage7_experiment_results.json` exists, is valid JSON, and contains 40,702 total bars and 33,919 out-of-sample evaluated bars.
2. `test_stage7_canonical_baseline_reproducibility`: PASSED. Verifies exact reproduction of baseline metrics ($53.28\%$ GBDT, $53.20\%$ Logistic Regression).
3. `test_causal_regime_threshold_isolation`: PASSED. Demonstrates that training fold quantiles differ from test and full-sample quantiles, proving zero lookahead leakage.
4. `test_metric_bounds_and_intervals`: PASSED. Asserts all accuracies, Brier scores, ROC-AUCs, and Wilson intervals adhere to strict mathematical bounds $[0, 1]$ or $[0, 100]$.
5. `test_production_model_registry_integrity`: PASSED. Asserts `HAR-RS-DOW-v1.0` remains the sole authorized production model and directional models remain `OFFLINE_RESEARCH_ONLY`.
6. Stage 5 Model Identity & Dependency Schema Suites (9 tests): PASSED.
7. Stage 6 Runtime Verification & Feature Parity Suites (5 tests): PASSED.

Zero tests failed. Zero tests timed out. Zero tests were skipped.

---

## 9. Limitations and Blockers

1. **Informational Bound of Price-Only OHLCV:** At the 1-hour horizon, Bitcoin returns driven purely by past price lags exhibit an effective upper bound of $\approx 53.3\%$ directional accuracy and $\approx 56.8\%$ selective accuracy. Regime conditioning within the same OHLCV feature space cannot breach this boundary.
2. **Severe Historical Derivative Truncation:** Existing funding rate (375 bars) and open interest (3,000 bars) files cover only $\approx 7\%$ of the 4-year canonical evaluation period. They cannot be incorporated into the walk-forward matrix without discarding $93\%$ of out-of-sample evaluation data.
3. **Turnover Execution Friction:** Naive hourly directional signals generate turnover exceeding $0.75 - 1.70$ transitions per bar. Under institutional taker fees ($14\text{ bps}$ round-trip), every strategy configuration tested generated negative net returns ($-4.1$ to $-5.2\text{ bps/bar}$).
4. **Holdout Exhaustion Risk:** Because the 2022–2026 historical OHLCV dataset has been utilized across multiple research stages, all findings must be treated as exploratory. No historical holdout improvement should be promoted without prospective shadow validation.

---

## 10. Architectural Decisions & Research Action Table

### Core Architectural Decisions
- **Decision 1: Reject Regime Conditioning in Production.**
  Do NOT deploy regime-conditioned GBDT or partitioned models. Global 4-lag baseline remains the superior research benchmark ($53.28\%$), while partitioned models introduce harmful variance ($52.83\%$).
- **Decision 2: Halt Further Price-Only Feature Complexity.**
  Cease engineering technical indicators, oscillators, or complex topological groupings on OHLCV data. Feature ablation (Stage 6) and regime testing (Stage 7) conclusively prove they add zero out-of-sample value.
- **Decision 3: Maintain Strict Role Segregation.**
  Preserve `HAR-RS-DOW-v1.0` as the authoritative production model for risk envelopes. Directional forecasting remains strictly an offline research activity.
- **Decision 4: Prioritize Continuous Multi-Year Derivatives Acquisition.**
  Prioritize acquiring high-integrity, point-in-time historical funding rate and open interest data covering the full 2022–2026 period before attempting further directional alpha research.

### Final Research Action Table

| Priority | Finding | Evidence | Next Action | Acceptance Test | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **P1** | **$H_1$ Falsified:** Regime conditioning does not improve out-of-sample accuracy. | Challenger GBDT: $53.23\%$ vs $53.28\%$ baseline ($p = 0.6154$, Holm-Bonferroni adj. $p = 1.000$). | Freeze directional model complexity; maintain global 4-lag baseline as benchmark. | `test_stage7_regime_experiments.py` | **COMPLETED / ENFORCED** |
| **P1** | **Apparent Trajectory Alpha is Class Imbalance Drift.** | `Traj_Bear_Push` achieves $54.37\%$ accuracy, but majority-class baseline is $54.81\%$ ($BalAcc = 50.71\%$). | Disallow raw accuracy claims without reporting conditional class balance and majority baseline. | Experiment A diagnostic audit | **DOCUMENTED / RESOLVED** |
| **P1** | **Selective Predictions Remain Net Unprofitable.** | Best selective GBDT achieves $56.81\%$ accuracy at $5.1\%$ coverage, but loses $-4.77\text{ bps/bar}$ net at 14 bps friction. | Require cost-aware execution filters and turnover penalties in any future trading simulations. | Experiment C economic evaluation | **VERIFIED / BLOCKED** |
| **P2** | **Existing Derivative Datasets are Severely Truncated.** | `funding.parquet` has only 375 rows ($0.9\%$ coverage); `oi.parquet` has 3,000 rows ($7.3\%$ coverage). | Do not integrate partial derivative feeds into 4-year walk-forward matrix. | Parquet dataset audit | **CONFIRMED / DEFERRED** |
| **P2** | **External Data Acquisition Plan.** | Li et al. (2026) and Yae & Tian (2022) prove fundamental signals require external data streams. | Specify schema and acquire 2022–2026 point-in-time hourly funding rate and liquidations history. | Data Opportunity Matrix approval | **READY FOR NEXT STAGE** |
| **P3** | **Prospective Shadow Validation Protocol.** | Repeated holdout testing risks backtest overfitting (Arian et al. 2024). | Implement an offline, prospective shadow evaluator logging frozen daily predictions against new live bars. | Zero-trade shadow inference gate | **RECOMMENDED** |

---

## 11. Final Summary & Deliverables

1. **Conditional Prediction in Existing Data:** Market-state conditioning (volatility terciles, trend terciles, return trajectory patterns) does **not** produce reliable out-of-sample directional improvements.
2. **Best Verified Result:** Global 4-Lag GBDT baseline ($53.28\%$) and L2 Logistic Regression baseline ($53.20\%$, $221\times$ faster training) remain the most defensible directional models. Challenger models peaked at $53.39\%$ (statistically indistinguishable, $p = 0.5930$).
3. **Statistical & Practical Significance:** Apparent sub-regime accuracy gains (up to $54.4\%$) fail against the conditional majority-class baseline ($54.8\%$). In economic simulations, high turnover causes severe negative net expectancy ($-4.1$ to $-13.9\text{ bps/bar}$).
4. **Survivability under Robustness Checks:** No regime-conditioned model survived Holm-Bonferroni multiplicity correction or sensitivity audits across alternative lookback windows.
5. **Necessity of New Data Sources:** Price-only OHLCV data has reached its predictive ceiling. Further predictive discovery requires continuous, point-in-time derivatives data (funding rates, open interest, liquidations) spanning 2022–2026.
6. **Artifact Paths:**
   - Report: [`research/reports/stage7_regime_conditioned_prediction_research.md`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/stage7_regime_conditioned_prediction_research.md)
   - Machine-Readable JSON: [`experiments/results/stage7_regime_research/stage7_experiment_results.json`](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/stage7_regime_research/stage7_experiment_results.json)
   - Reproducible Script: [`research/stage7_regime_experiments.py`](file:///c:/Projects/BTCognitive/BTCognitive/research/stage7_regime_experiments.py)
   - Unit Tests: [`tests/test_stage7_regime_experiments.py`](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_stage7_regime_experiments.py)
