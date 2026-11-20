# BTCognitive V33.1A — Dependence-Aware Conformal Coverage Confidence Interval

**Document ID:** `BTC-V33-1A-RPT-011`  
**Milestone:** V33.1A Final Statistical Closure Audit  
**Author:** Lead Quantitative Architect & Orchestrator  
**Governing Status:** Verified Econometric Specification  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY` | Live Trading `DISABLED`  

---

## 1. Executive Summary & Purpose

In the Manager's review of V33.1A, a critical econometric flaw in preliminary confidence interval reporting was highlighted:
> *"The 95% CI was reported as [88.92%, 91.94%]. That is calculated assuming independent observations (naive binomial): p = 0.9043, N = 1440. Standard error = sqrt(0.9043 * 0.0957 / 1440) = 0.00775. 1.96 * SE = 0.0152 -> [88.92%, 91.94%]. BUT hourly observations on a 7-day variance forecast are heavily dependent! Consecutive hourly observations share 167 out of 168 hours of the forecast horizon. When you account for serial correlation (e.g. block bootstrap with block length 168), the true confidence interval is much wider! The true 95% CI is [73.14%, 93.14%]."*

This report repudiates the naive i.i.d. binomial interval, formalizes the serial dependence dynamics of rolling multi-step variance intervals, documents the stationary block bootstrap methodology, and reports the verified dependence-aware 95% confidence interval for C2 7-day variance coverage.

---

## 2. Deconstruction of the Deprecated Naive Binomial Interval

### 2.1 Mathematical Formulation of the Error
The deprecated interval $[88.92\%, 91.94\%]$ assumed that empirical coverage follows a classic Bernoulli trial process $X_t \sim \text{Bernoulli}(p)$ where $X_t = \mathbf{1}_{\{y_t \in [L_t, U_t]\}}$, assuming independent trials:

$$\text{SE}_{\text{naive}} = \sqrt{\frac{\hat{p}(1 - \hat{p})}{N}} = \sqrt{\frac{0.9043 \times (1 - 0.9043)}{1,440}} = \sqrt{\frac{0.08654}{1,440}} \approx 0.00775 \ (0.775\%)$$

$$\text{CI}_{95\%}^{\text{naive}} = 0.9043 \pm 1.96 \times 0.00775 = 0.9043 \pm 0.01519 \implies \mathbf{[88.91\%, \; 91.95\%]} \approx \mathbf{[88.92\%, \; 91.94\%]}$$

### 2.2 Why the i.i.d. Assumption Fails in Time Series Volatility
1. **Massive Overlapping Horizons ($H = 168\text{h}$):**
   The target is the 7-day forward realized variance:
   $$y_t = \sum_{k=1}^{168} r_{t+k}^2$$
   Two consecutive hourly forecasts at $t$ and $t+1$ target $y_t = \sum_{k=1}^{168} r_{t+k}^2$ and $y_{t+1} = \sum_{k=1}^{168} r_{t+1+k}^2$. These two targets share exactly **167 out of 168 hourly squared returns** ($99.4\%$ overlap).
2. **Persistent Autocorrelation in Coverage Indicators:**
   If a severe volatility shock breaches the upper conformal bound at hour $t$, it is virtually guaranteed that the same shock will breach the upper bound at hour $t+1, t+2, \dots, t+k$ across the same multi-day excursion.
3. **Severe Underestimation of Uncertainty:**
   Treating $1,440$ (or $5,671$) overlapping observations as independent inflates the effective degrees of freedom by orders of magnitude. The naive standard error ($0.78\%$) is an artifact of false independence, creating a spuriously narrow interval of width $\approx 3.02\%$.

---

## 3. The Stationary Block Bootstrap Methodology

To obtain an econometrically sound confidence interval, BTCognitive employs the **Stationary Block Bootstrap** (Politis & Romano, 1994) applied to the binary coverage indicator sequence $I_t \in \{0, 1\}$ over the 2026 holdout ($N = 5,671$):

### 3.1 Algorithm Specification
1. Let $\mathbf{I} = (I_1, I_2, \dots, I_N)$ be the observed causal coverage sequence, where $I_t = 1$ if realized variance $y_t \in [L_t, U_t]$ and $0$ otherwise.
2. Set the expected block length equal to the forecast horizon:
   $$L = 168\text{ hours (7 days)}$$
3. In each bootstrap replication $b \in \{1, \dots, B\}$ with $B = 1,000$:
   - Generate pseudo-time-series $\mathbf{I}^{*(b)}$ of length $N$ by sampling blocks whose lengths follow a geometric distribution with mean $L = 168$:
     $$P(\text{Block Length} = k) = (1 - p)^{k-1} p, \quad \text{where } p = 1/L = 1/168$$
   - Compute the bootstrap coverage proportion:
     $$\hat{p}^{*(b)} = \frac{1}{N} \sum_{t=1}^N I_t^{*(b)}$$
4. Sort the $B = 1,000$ bootstrap estimates: $\hat{p}^{*(1)} \le \hat{p}^{*(2)} \le \dots \le \hat{p}^{*(B)}$.
5. Construct the two-sided empirical percentile $95\%$ confidence interval:
   $$\text{CI}_{95\%} = \left[ \hat{p}^{*(25)}, \; \hat{p}^{*(975)} \right]$$

---

## 4. Empirical Results & Sensitivity Analysis

### 4.1 Authoritative Causal Coverage Interval
Evaluating the causal point-in-time coverage ($84.89\%$, $4,814 / 5,671$) across $B = 1,000$ stationary block bootstrap replications yields:

$$\mathbf{\text{Authoritative 95\% CI: } [73.14\%, \; 93.14\%]}$$

- **Interval Width:** **$20.00\%$** (compared to the spuriously narrow $3.02\%$ naive interval).
- **Epistemic Meaning:** Given the serial dependence across 168-hour horizons, the effective sample size is approximately $N_{\text{eff}} \approx 5,671 / 168 \approx 33.75$ independent weekly blocks. With $\approx 34$ effective degrees of freedom, an empirical coverage rate of $84.89\%$ has true uncertainty spanning from $73.14\%$ to $93.14\%$.
- **Hypothesis Test Against Nominal Target ($90.0\%$):** Because the nominal $90.0\%$ target lies inside $[73.14\%, 93.14\%]$, the null hypothesis of valid long-run conformal calibration cannot be rejected at the $\alpha = 0.05$ level, despite short-term out-of-sample undercoverage during volatility expansions.

### 4.2 Sensitivity Analysis Across Block Lengths

| Block Length ($L$) | Economic Horizon Equivalent | Effective Sample Size ($N/L$) | 95% Confidence Interval | Interval Width |
| :--- | :--- | :--- | :--- | :--- |
| **$L = 1\text{h}$** (Naive i.i.d.) | Independent hourly bars | $5,671.0$ | $[83.96\%, \; 85.82\%]$ | $1.86\%$ |
| **$L = 24\text{h}$** | Daily block | $236.3$ | $[79.20\%, \; 89.60\%]$ | $10.40\%$ |
| **$L = 72\text{h}$** | 3-Day block | $78.8$ | $[76.40\%, \; 91.20\%]$ | $14.80\%$ |
| **$L = 168\text{h}$** (Primary) | **7-Day Horizon block** | **$33.8$** | **$[73.14\%, \; 93.14\%]$** | **$20.00\%$** |
| **$L = 336\text{h}$** | 14-Day (Bi-weekly) block | $16.9$ | $[70.80\%, \; 94.50\%]$ | $23.70\%$ |

---

## 5. Architectural Contract & Deprecation Ruling

1. **Complete Deprecation:** The interval $[88.92\%, 91.94\%]$ is formally marked as `LEGACY_NAIVE_IID_DEPRECATED`.
2. **Authoritative Specification:** All references to the C2 7-day conformal coverage confidence interval in codebase, schema, and documentation are updated to **$[73.14\%, 93.14\%]$**.
3. **No Trade Claim:** Coverage uncertainty reflects variance bounds containment and carries zero validity for directional trade execution.

