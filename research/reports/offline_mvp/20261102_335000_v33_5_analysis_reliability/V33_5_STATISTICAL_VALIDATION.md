# BTCognitive V33.5 — Statistical Validation & Overfitting Risk Audit Report

**Date:** November 2026  
**Document ID:** `V33_5_STATISTICAL_VALIDATION.md`  
**Specialist Workstream:** Agent 8 — Quantitative Validation and Overfitting Specialist  
**Operating Standard:** BTCognitive Epistemic Contract & V33.5 Multi-Agent Orchestration Protocol  
**Repository Branch:** `main` (BTCognitive V33.5)  

---

## 1. Executive Summary & Audit Census

Milestone **V33.5** conducts an exhaustive, mathematically rigorous statistical and econometric audit of BTCognitive across `engine/`, `models/`, `research/`, and `tests/`. This audit evaluates forecast evaluation loss functions, finite-sample paired hypothesis testing, multiple hypothesis testing corrections in strategy tournaments, and prospective sampling requirements.

### Key Audit Verdicts:
1. **Diebold–Mariano & HLN (1997) Correction:** Verified mathematically sound in `models/challengers/har_qlike_24h_challenger.py` and `har_qlike_challenger.py`. A critical squaring defect was identified in `research/run_v18_price_and_strategy_tournament.py` (line 168) where QLIKE losses are passed into a residual-squared DM implementation, computing $(L_{\text{base}}^2 - L_{\text{cand}}^2)$ instead of linear loss differentials.
2. **QLIKE Loss Coherence:** Patton (2011) QLIKE loss is robustly implemented with floor containment (`1e-6`), scale-invariance, and strict non-negativity. Direct QLIKE parameter minimization in `HARQLIKEChallenger` satisfies Puke & Schweikert (2026) loss coherence and eliminates log-retransformation bias.
3. **Tournament Multiple Testing & Overfitting:** In `engine/strategy_selection.py`, candidate selection is protected by hard eligibility gates ($N \ge 30$, $\text{CI}_{\text{lower}} \ge 42\%$, $\text{CI}_{\text{width}} \le 22\%$, Net EV $\ge +2.0$ bps). However, final tournament winner determination lacks White's Reality Check, Hansen's Model Confidence Set (MCS), or False Discovery Rate (FDR) control, exposing multi-archetype selection to selection bias ("Winner's Curse").
4. **Non-Overlapping Confirmatory Blocks:** Confirmed the mathematical flaw audited in V30.9: multiplying 100 blocks by $E[L]=5$ to mandate 500 trades is unsupported by Politis & Romano (1994) bootstrap theory. Under serial correlation $\rho \approx 0.30$, 100 nominal observations yield an effective sample size $N_{\text{eff}} \approx 54$. Currently, prospective shadow ledgers contain $< 100$ clean non-overlapping resolved outcomes, keeping the confirmatory gate appropriately locked.

---

## 2. Loss Function Formulation & Volatility Evaluation

### 2.1 The Patton (2011) Robust Family
In financial econometrics, the true latent volatility $\sigma_t^2$ is unobservable. Forecasts $\hat{v}_t$ must be evaluated against an imperfect volatility proxy $\hat{\sigma}_t^2$ (such as realized variance computed from intra-day or hourly squared returns):
$$\hat{\sigma}_t^2 = \sigma_t^2 + \eta_t, \quad E[\eta_t \mid \mathcal{F}_{t-1}] = 0$$

Patton (2011) proved that a loss function $L(\hat{\sigma}^2, \hat{v})$ generates forecast rankings that are **robust to proxy noise** if and only if it belongs to the homogeneous family parameterized by:
$$L(\hat{\sigma}^2, \hat{v}) = \frac{1}{(b+1)(b+2)} \left( \hat{\sigma}^{2(b+2)} - \hat{v}^{b+2} \right) - \frac{1}{b+1} \hat{v}^{b+1} (\hat{\sigma}^2 - \hat{v})$$

Setting $b = -2$ yields the **Quasi-Likelihood (QLIKE)** loss function:
$$L_{\text{QLIKE}}(\hat{\sigma}^2, \hat{v}) = \frac{\hat{\sigma}^2}{\hat{v}} - \ln\left(\frac{\hat{\sigma}^2}{\hat{v}}\right) - 1$$

Setting $b = 0$ yields the **Mean Squared Error (MSE)** loss on variance:
$$L_{\text{MSE}}(\hat{\sigma}^2, \hat{v}) = (\hat{\sigma}^2 - \hat{v})^2$$

### 2.2 Mathematical Properties of QLIKE
Let $z_t = \frac{\hat{\sigma}_t^2}{\hat{v}_t} \in (0, \infty)$ be the forecast ratio. Then:
$$g(z_t) = z_t - \ln(z_t) - 1$$

1. **Global Minimum & Non-Negativity:**
   $$g'(z_t) = 1 - \frac{1}{z_t} = 0 \implies z_t = 1 \quad (\hat{v}_t = \hat{\sigma}_t^2)$$
   $$g''(z_t) = \frac{1}{z_t^2} > 0 \quad \forall z_t > 0$$
   Therefore, $g(z_t) \ge 0$ for all $z_t > 0$, with $g(z_t) = 0$ if and only if $\hat{v}_t = \hat{\sigma}_t^2$.
2. **Scale Invariance:**
   If both actual variance and forecast are scaled by factor $c > 0$, $z_t = \frac{c \hat{\sigma}_t^2}{c \hat{v}_t} = \frac{\hat{\sigma}_t^2}{\hat{v}_t}$, meaning $L_{\text{QLIKE}}$ is purely a function of relative forecast error.
3. **Asymmetric Risk Penalty:**
   - Under-forecasting risk ($\hat{v}_t \to 0 \implies z_t \to \infty$): $L_{\text{QLIKE}} \sim z_t \to \infty$ (linear divergence).
   - Over-forecasting risk ($\hat{v}_t \to \infty \implies z_t \to 0$): $L_{\text{QLIKE}} \sim -\ln(z_t) \to \infty$ (logarithmic divergence).
   Severe under-prediction of market volatility is penalized significantly more heavily than over-prediction, matching institutional risk preservation requirements.

### 2.3 Loss-Coherence vs. Retransformation Bias (Puke & Schweikert 2026)
Conventional HAR models estimate parameters via OLS on log-variance:
$$\ln(y_t) = X_t \beta + \epsilon_t, \quad \hat{\beta}_{\text{OLS}} = \arg\min_\beta \sum_{t=1}^T (\ln(y_t) - X_t \beta)^2$$
When taking the natural exponential to produce variance forecasts $\hat{v}_t = \exp(X_t \hat{\beta}_{\text{OLS}})$, a systematic **retransformation bias** occurs because by Jensen's inequality:
$$E[y_t \mid X_t] = \exp(X_t \beta) \cdot E[\exp(\epsilon_t)] > \exp(X_t \beta)$$
Furthermore, estimating parameters under MSE of log-variance but evaluating out-of-sample performance under QLIKE creates an estimator-evaluator loss incoherence.

In `models/challengers/har_qlike_challenger.py`, direct QLIKE minimization solves:
$$\hat{\beta}_{\text{QLIKE}} = \arg\min_\beta \left\{ \frac{1}{T} \sum_{t=1}^T \left[ \frac{y_t}{\exp(X_t \beta)} - \ln\left(\frac{y_t}{\exp(X_t \beta)}\right) - 1 \right] + \lambda \sum_{j=1}^p \beta_j^2 \right\}$$
This guarantees that parameter estimates directly minimize out-of-sample QLIKE risk, eliminating retransformation bias.

---

## 3. Diebold–Mariano with Harvey–Leybourne–Newbold (1997) Finite-Sample Correction

### 3.1 Mathematical Derivation
Let $d_t = L(e_{1,t}) - L(e_{2,t})$ denote the loss differential at time $t$ between Benchmark 1 and Challenger 2. The sample mean loss differential across $T$ observations is:
$$\bar{d} = \frac{1}{T} \sum_{t=1}^T d_t$$
Under the null hypothesis of equal forecast accuracy:
$$H_0: E[d_t] = 0$$

For $h$-step-ahead forecasts, forecast errors overlap and exhibit autocorrelation up to lag $h-1$, following an $\text{MA}(h-1)$ structure. The asymptotic long-run variance of $\sqrt{T} \bar{d}$ is:
$$\sigma_d^2 = \gamma_0 + 2 \sum_{k=1}^{h-1} \gamma_k$$
where $\gamma_k = \text{Cov}(d_t, d_{t-k})$. Using the Newey–West / Bartlett kernel to guarantee positive semi-definiteness:
$$\hat{V}(\bar{d}) = \frac{1}{T} \left( \hat{\gamma}_0 + 2 \sum_{k=1}^{h-1} \left(1 - \frac{k}{h}\right) \hat{\gamma}_k \right)$$

The asymptotic Diebold–Mariano (1995) test statistic is:
$$\text{DM} = \frac{\bar{d}}{\sqrt{\hat{V}(\bar{d})}} \xrightarrow{d} \mathcal{N}(0, 1) \quad \text{as } T \to \infty$$

### 3.2 The Harvey–Leybourne–Newbold (HLN 1997) Correction
Harvey, Leybourne, and Newbold (1997) demonstrated that the asymptotic DM test suffers from severe size distortion in small to moderate samples ($T < 250$), over-rejecting the null hypothesis when it is true. They proposed the finite-sample adjusted test statistic:
$$\text{HLN} = \text{DM} \times \sqrt{\frac{T + 1 - 2h + h(h-1)/T}{T}}$$

For 1-step ahead forecasts ($h = 1$):
$$\text{HLN} = \text{DM} \times \sqrt{\frac{T - 1}{T}}$$

### 3.3 Reference Distribution & Degrees of Freedom
Crucially, HLN (1997) proved that rather than referencing the standard normal distribution $\mathcal{N}(0, 1)$, the critical values must be derived from **Student's $t$ distribution with $T - 1$ degrees of freedom ($t_{T-1}$)**:
$$p\text{-value}_{\text{two-sided}} = 2 \left( 1 - F_{t_{T-1}}(|\text{HLN}|) \right)$$
$$p\text{-value}_{\text{one-sided}} = 1 - F_{t_{T-1}}(\text{HLN}) \quad (\text{for } H_1: E[d_t] > 0)$$

Because Student's $t$ distribution has heavier tails than the standard normal ($F_{t_{T-1}}^{-1}(1-\alpha) > \Phi^{-1}(1-\alpha)$ for all finite $T$), this test requires a higher hurdle to claim statistical superiority, preventing spurious challenger promotion.

### 3.4 Cross-Codebase Implementation Audit

| Location | Differential Definition | Kernel / Variance | HLN Factor | Reference Dist | Status / Audit Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `models/challengers/har_qlike_24h_challenger.py` (L48-105) | $d = L_{\text{base}} - L_{\text{chal}}$ | Bartlett ($k < h$) or sample var ($h=1$) | $\sqrt{\frac{T + 1 - 2h + h(h-1)/T}{T}}$ | Student's $t_{T-1}$ (`stats.t.sf`) | **Exemplary.** Correct one-sided test for model superiority. |
| `models/challengers/har_qlike_challenger.py` (L135-156) | $d = L_{\text{base}} - L_{\text{chal}}$ | Bartlett ($k < h$) | Correct HLN formula | Student's $t_{T-1}$ | **Exemplary.** Loss-coherent evaluation. |
| `engine/price_forecast_engine.py` (L57-101) | $d = e_{\text{base}}^2 - e_{\text{cand}}^2$ | Rectangular ($w_k = 1$) | Correct HLN formula | Student's $t_{T-1}$ (`stats.t.cdf`) | **Mathematically sound for squared errors.** However, assumes residual inputs. |
| `research/experiments/run_v32_37_chronos2_benchmark.py` (L56-98) | $d = e_{\text{model}}^2 - e_{\text{base}}^2$ | Bartlett ($k < h$) | Correct HLN formula | Student's $t_{T-1}$ | **Sign inverted:** Positive indicates model is *inferior*. |
| `research/run_v18_price_and_strategy_tournament.py` (L168) | Passes $L_{\text{QLIKE}}$ into `compute_diebold_mariano_hln` | Calls `price_forecast_engine` | Calls `price_forecast_engine` | Student's $t_{T-1}$ | **CRITICAL DEFECT:** Computes $(L_{\text{base}}^2 - L_{\text{cand}}^2)$. Squares the QLIKE loss! |

---

## 4. Multiple Hypothesis Testing & Tournament Selection Audit

### 4.1 The Winner's Curse and Data Snooping Bias
When evaluating $M$ candidate trading strategies or model specifications, the expected maximum performance across the pool is strictly positive even under the universal null hypothesis that all strategies have zero true edge:
$$H_0: E[R_1] = E[R_2] = \dots = E[R_M] = 0 \implies E\left[ \max_{m=1,\dots,M} \bar{R}_m \right] > 0$$
Selecting the top-ranking candidate based on the highest sample return or Sharpe ratio without statistical correction results in severe **overfitting to retrospective noise (Data Snooping / Selection Bias)**.

### 4.2 White's Reality Check (2000) & Hansen's SPA (2005)
White (2000) proposed testing:
$$H_0: \max_{k=1,\dots,M} E[f_k] \le 0$$
where $f_{k,t} = L(e_{0,t}) - L(e_{k,t})$ is the performance of model $k$ relative to benchmark model 0.
White's Reality Check uses the Politis & Romano (1994) stationary bootstrap to generate $B$ resamples of the centered matrix $\bar{f}_k^{*,b} - \bar{f}_k$, evaluating the test statistic:
$$T_{\text{RC}} = \max_{k=1,\dots,M} \sqrt{T} \bar{f}_k$$
$$p_{\text{RC}} = \frac{1}{B} \sum_{b=1}^B \mathbb{I}\left( \max_{k=1,\dots,M} \sqrt{T} (\bar{f}_k^{*,b} - \bar{f}_k) > T_{\text{RC}} \right)$$

Hansen (2005) introduced the **Superior Predictive Ability (SPA)** test, improving White's Reality Check by studentizing the test statistic and re-centering only over candidates where $\bar{f}_k \ge - \sqrt{2 \ln \ln T \cdot \hat{\sigma}_k^2 / T}$, preventing poor models from diluting the test's statistical power.

### 4.3 Hansen, Lunde, and Nason (2011) Model Confidence Set (MCS)
Rather than comparing against a fixed benchmark, the Model Confidence Set (MCS) determines a subset of models $\widehat{\mathcal{M}}_{1-\alpha}^* \subset \mathcal{M}_0$ that contains the best model(s) with confidence $(1 - \alpha)$:
1. Set initial pool $\mathcal{M} = \mathcal{M}_0$.
2. Test the null hypothesis of equal predictive ability across all models in $\mathcal{M}$:
   $$H_{0,\mathcal{M}}: E[d_{ij,t}] = 0 \quad \forall i, j \in \mathcal{M}$$
   using the range statistic $T_R = \max_{i, j \in \mathcal{M}} \frac{|\bar{d}_{ij}|}{\hat{\sigma}(\bar{d}_{ij})}$ or max statistic $T_{\max} = \max_{i \in \mathcal{M}} \frac{\bar{d}_{i\cdot}}{\hat{\sigma}(\bar{d}_{i\cdot})}$.
3. If $H_{0,\mathcal{M}}$ is rejected at significance $\alpha$, eliminate the worst model using the elimination rule:
   $$e_{\mathcal{M}} = \arg\max_{i \in \mathcal{M}} \frac{\bar{d}_{i\cdot}}{\hat{\sigma}(\bar{d}_{i\cdot})}$$
4. Repeat until the null hypothesis is not rejected. The surviving set is $\widehat{\mathcal{M}}_{1-\alpha}^*$.

### 4.4 Family-Wise Error Rate (FWER) vs. False Discovery Rate (FDR)

| Correction Procedure | Formal Threshold / Formulation | Error Metric Controlled | Strengths | Limitations | Current Codebase Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bonferroni** | Reject if $p_i \le \frac{\alpha}{M}$ | Family-Wise Error Rate (FWER): $P(V \ge 1) \le \alpha$ | Simple, distribution-free | Highly conservative under correlated strategies | Used as reference in `reconcile_trial_census()` |
| **Holm (1979) Step-Down** | Sort $p_{(1)} \le \dots \le p_{(M)}$. Reject if $p_{(k)} \le \frac{\alpha}{M - k + 1}$ | FWER: $P(V \ge 1) \le \alpha$ | Strictly more powerful than Bonferroni | Still conservative for large $M$ | **Implemented in `research/foundation_statistical_gate.py`** ($K=48$ trials) |
| **Benjamini-Hochberg (1995)** | Reject for $k \le k_{\max}$ where $p_{(k)} \le \frac{k}{M} q^*$ | False Discovery Rate (FDR): $E\left[\frac{V}{\max(R, 1)}\right] \le q^*$ | High power, scalable to large strategy universes | Assumes PRDS (positive regression dependence) | **Missing in tournament selection** |
| **Benjamini-Yekutieli (2001)** | Reject for $p_{(k)} \le \frac{k}{M \sum_{i=1}^M \frac{1}{i}} q^*$ | FDR under arbitrary dependence structures | Valid under arbitrary strategy correlation | Slightly more conservative than B-H | **Missing in tournament selection** |

### 4.5 Gap Analysis in `engine/strategy_selection.py`
In `engine/strategy_selection.py`:
- 5 canonical MEIE archetypes (`MEIE-IGNITION`, `MEIE-ABSORPTION`, `MEIE-VACUUM`, `MEIE-TOXICITY`, `MEIE-COMBINED`) each evaluate dual hypotheses ($H_{\text{long}}$ and $H_{\text{short}}$), yielding 10 comparisons per bar.
- Selection logic (lines 566–595) computes:
  $$\text{Score}_i = \text{Net EV}_i \times \text{RegimeFit}_i$$
  and selects $\arg\max_i \text{Score}_i$.
- **Finding:** While hard eligibility gates (sample size $N \ge 30$, confidence interval width $\le 22\%$, net EV $\ge +2.0$ bps) prevent selecting catastrophic outliers, there is **zero multiple testing adjustment (Holm, FDR, or MCS)** applied across the 10 candidate hypotheses at decision time.
- **Remediation Recommendation:** Before ranking eligible strategies, apply a Benjamini-Hochberg FDR hurdle ($q^* = 0.10$) across the candidate hypotheses, or enforce that the selected candidate must belong to the Hansen (2011) Model Confidence Set $\widehat{\mathcal{M}}_{0.90}^*$.

---

## 5. Non-Overlapping Block Requirements & Confirmatory Testing

### 5.1 Calendar Blocks vs. Event-Driven Trade Units
`AGENTS.md` mandates:
> *"A minimum of 100 non-overlapping clean blocks is required before confirmatory prospective evaluation."*

The codebase contains two fundamentally distinct sampling regimes:
1. **Continuous Fixed-Interval Forecasting (`rv24h_var_ann` / `rv7d_var_ann`):**
   - Observations occur at fixed calendar intervals ($t, t+1\text{h}, t+2\text{h}$).
   - 1 non-overlapping block = exactly 24 closed hourly candles (1 calendar day).
   - 100 clean non-overlapping blocks = exactly 100 calendar days (2,400 hours) of continuous market data without temporal gaps or data corruption.
2. **Event-Driven Trade Setup Strategies (`HTF_RANGE_EXPANSION_BREAKOUT` / MEIE):**
   - Signals trigger sporadically (e.g., when price breaks out of the 20-bar 4h high).
   - Positions have variable holding periods (stochastically resolving between 4 hours and 72 hours).
   - Flat periods of variable length (12 hours to 144 hours) separate trades.
   - 1 trade outcome = one discrete economic excursion $[t_{\text{entry}}, t_{\text{exit}}]$. Because in-position gating suppresses subsequent signals until trade exit, trade holding intervals are strictly non-overlapping.

### 5.2 Refutation of the V30.8 Multiplication Fallacy ($100 \times 5 = 500$ Trades)
In milestone V30.8, it was asserted that 100 confirmatory blocks required $100 \times 5 = 500$ completed trades by multiplying the 100-block hurdle by the stationary bootstrap mean block length $E[L]=5$.
As proven in V30.9 (`tests/test_v30_9_statistical_gate_audit.py`):
- In Politis & Romano (1994), $E[L] = 1/p$ is the mean parameter of a geometric distribution used to randomly resample contiguous blocks during Monte Carlo simulation:
  $$L \sim \text{Geometric}(p), \quad P(L = k) = (1 - p)^{k-1} p, \quad E[L] = \frac{1}{p} = 5$$
- The stationary bootstrap takes a sample of size $N$ and resamples $N$ observations. **It does NOT partition the dataset into $N / 5$ chunks.**
- Multiplying sample size requirements by the resampling parameter $E[L]$ is an econometric category error.

### 5.3 Effective Sample Size ($N_{\text{eff}}$) under Serial Correlation
Even when trade intervals do not overlap in calendar time, their outcomes (net returns, holding durations) exhibit autocorrelation because market volatility regimes and trend persistence cluster in time.

The asymptotic variance of the sample mean under serial correlation is:
$$\text{Var}(\bar{X}) = \frac{\sigma^2}{N} \left( 1 + 2 \sum_{k=1}^{N-1} \left(1 - \frac{k}{N}\right) \rho_k \right)$$

The **effective sample size ($N_{\text{eff}}$)**—the number of truly independent observations carrying equivalent statistical information—is:
$$N_{\text{eff}} = \frac{N}{1 + 2 \sum_{k=1}^\infty \rho_k}$$

For a first-order autoregressive process $\text{AR}(1)$ with autocorrelation $\rho_1$:
$$N_{\text{eff}} = N \cdot \frac{1 - \rho_1}{1 + \rho_1}$$

#### Empirical Impact on Gate Requirements:
- At $\rho_1 = 0.00$ (independent trades): $N_{\text{eff}} = 100$.
- At $\rho_1 = 0.20$: $N_{\text{eff}} = 100 \cdot (0.80 / 1.20) = 66.7$.
- At $\rho_1 = 0.30$ (typical regime clustering): $N_{\text{eff}} = 100 \cdot (0.70 / 1.30) \approx 53.8$.
- At $\rho_1 = 0.40$: $N_{\text{eff}} = 100 \cdot (0.60 / 1.40) \approx 42.9$.

Therefore, requiring 100 completed trades under $\rho_1 = 0.30$ provides approximately 54 effective degrees of freedom.

### 5.4 Confirmatory Gate Audit Status
- In `research/combined_statistical_gate.py`, the production system was evaluated across only $N = 31$ blocks (744 hours), which failed the 100-block confirmatory hurdle.
- In `data/prospective_entry_ledger_v2.jsonl` and `data/prospective_shadow_v1.jsonl`, accumulated resolved prospective outcomes remain below $N=100$.
- **Governed Status:** The confirmatory evidence gate is strictly maintained at:
  $$\text{PROSPECTIVE EVIDENCE: COLLECTING (INSUFFICIENT\_FOR\_CONFIRMATORY\_GATE)}$$

---

## 6. Concrete Code Audit Findings & Remediation Plan

### Finding 1: Squared QLIKE Loss in Diebold–Mariano Call
- **File:** `BTCognitive/research/run_v18_price_and_strategy_tournament.py` (line 168)
- **Defect:** `loss_hist` and `loss_har` are passed into `compute_diebold_mariano_hln(loss_hist, loss_har, h=7)`. `price_forecast_engine.py` computes $d = e_{\text{benchmark}}^2 - e_{\text{candidate}}^2$, effectively squaring the QLIKE losses:
  $$d_{\text{erroneous}} = (L_{\text{hist}})^2 - (L_{\text{har}})^2$$
- **Remediation:** Replace with `models/challengers/har_qlike_24h_challenger.py::compute_diebold_mariano_test`, which accepts loss arrays directly and computes linear loss differentials $d = L_{\text{base}} - L_{\text{chal}}$.

### Finding 2: Inverted Test Statistic Sign Convention
- **Files:** `engine/price_forecast_engine.py` vs. `research/experiments/run_v32_37_chronos2_benchmark.py`
- **Defect:** `price_forecast_engine` defines $d = e_{\text{base}}^2 - e_{\text{cand}}^2$ (positive = candidate is superior). `chronos2_benchmark` defines $d = e_{\text{model}}^2 - e_{\text{base}}^2$ (positive = model has higher error / is inferior).
- **Remediation:** Standardize all DM implementations across the repository to the canonical econometric convention:
  $$d_t = L(\text{Benchmark})_t - L(\text{Candidate})_t \implies d_t > 0 \iff \text{Candidate is superior}$$

### Finding 3: Missing Multiple Testing Correction in Real-Time Strategy Selection
- **File:** `BTCognitive/engine/strategy_selection.py` (lines 566–595)
- **Defect:** 10 hypotheses (5 archetypes $\times$ Long/Short) are evaluated per bar. Winning strategy is selected purely by $\max \text{Score}$, without FWER, FDR, or Model Confidence Set filtering.
- **Remediation:** Implement a real-time Benjamini-Hochberg FDR check ($q^* = 0.10$) across eligible hypothesis p-values prior to final archetype selection.

---

## 7. Formal Governed Decisions

In strict accordance with Phase 7 of `AGENTS.md` and the V33.5 Operating Contract, the following four binding governance determinations are recorded:

1. **Research Experiment:** `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`  
   *(Challengers show theoretical and local promise, but lack multi-regime prospective confirmation across 100 clean blocks).*
2. **Prospective Evidence:** `COLLECTING`  
   *(Accumulated clean prospective observations have not satisfied the 100-block confirmatory hurdle; early stopping review triggers at $N=50$).*
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`  
   *(No candidate model inherits production authorization).*
4. **Live Trading:** `DISABLED`  
   *(Strictly research and market risk intelligence; zero live capital execution).*

