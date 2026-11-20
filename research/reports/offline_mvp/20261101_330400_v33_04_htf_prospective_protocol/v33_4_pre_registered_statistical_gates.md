# BTCognitive V33.4 — Pre-Registered Statistical Gates & Power Analysis

**Milestone:** V33.4 — HTF Breakout Prospective Shadow Validation  
**Date:** 2026-11-01  
**Target:** Pre-Registered Confirmatory Inference Standards & Stopping Rules  

---

## 1. The Methodological Imperative

In V33.3C, the Manager emphasized:
> *"The filtered 64 trades are a subset of the original 119 trades. These are not independent samples. A two-sample Welch test is therefore not my preferred test... A more appropriate comparison would construct two chronological portfolio-return streams over identical time intervals and evaluate the paired return differences using a dependence-aware block bootstrap."*

This document pre-registers the exact mathematical tests, hypotheses, stopping rules, and statistical power calculations for V33.4.

---

## 2. Statistical Formulation: Paired Portfolio Return Difference

Let $t \in \{1, 2, \dots, T\}$ denote discrete daily portfolio periods.  
Let $r_{\text{base}, t}$ denote the daily return of the unconditioned baseline strategy.  
Let $r_{\text{filt}, t}$ denote the daily return of the regime-filtered strategy.

We define the daily incremental value stream $\Delta_t$:
$$\Delta_t = r_{\text{filt}, t} - r_{\text{base}, t}$$

Notice that on days where no trade is active in either strategy, $\Delta_t = 0$.  
On days where both strategies hold the same trade, $\Delta_t = 0$.  
$\Delta_t \ne 0$ occurs exclusively on days where the baseline strategy holds a trade that the regime filter suppressed (`SUPPRESSED_CHOP`).  
On such days:
$$\Delta_t = 0 - r_{\text{suppressed}, t} = -r_{\text{suppressed}, t}$$
Thus, $\Delta_t > 0 \iff r_{\text{suppressed}, t} < 0$. The filter adds value if and only if the suppressed trade lost money.

---

## 3. Primary Gate: Stationary Block Bootstrap on $\Delta_t$

Because financial return series exhibit volatility clustering and serial autocorrelation, standard i.i.d. bootstrap resampling yields artificially deflated standard errors.

### Protocol Specification
1. **Resampling Algorithm:** Stationary block bootstrap (Politis & Romano, 1994).
2. **Mean Block Length:** $L = 3\text{ days}$ (matching the 72-hour maximum trade holding horizon).
3. **Replications:** $B = 2,000$ resamples.
4. **Target Metric:** Mean annualized excess return $\bar{\Delta}_{\text{ann}}$.
5. **Confidence Level:** 95% two-sided ($[q_{0.025}, q_{0.975}]$).
6. **Acceptance Threshold:**
   $$q_{0.025}(\bar{\Delta}_{\text{ann}}) > 0.0\%$$
   The lower bound of the 95% block bootstrap confidence interval must be strictly positive.

---

## 4. Secondary Gate: Diebold–Mariano with Harvey–Leybourne–Newbold Correction

To test whether the loss differential between baseline and filtered configurations is statistically significant:

$$d_t = L(r_{\text{base}, t}) - L(r_{\text{filt}, t})$$
where $L(r)$ is the portfolio negative utility or shortfall loss.

The test statistic with the Harvey–Leybourne–Newbold (1997) finite-sample correction is:
$$\text{DM}_{\text{HLN}} = \sqrt{\frac{T + 1 - 2h + h(h-1)/T}{T}} \times \left[ \frac{\bar{d}}{\sqrt{\hat{V}(\bar{d})}} \right]$$
where $h = 3$ is the multi-step horizon and $\hat{V}(\bar{d})$ is the Newey–West heteroskedasticity-and-autocorrelation-consistent (HAC) variance estimator.

**Reference Distribution:** Student's $t$ with $T - 1$ degrees of freedom.  
**Acceptance Threshold:** $p < 0.025$ (one-tailed test for superiority of the filtered strategy).

---

## 5. Statistical Power Analysis & Sample Size Determination

- Historical per-trade standard deviation: $\sigma \approx 400.0\text{ bps}$.
- Target economic effect size: $\mu_{\Delta} \ge \mathbf{+25.0\text{ bps}}$ per trade.
- Desired statistical power: $1 - \beta = 0.80$ at $\alpha = 0.05$.

The required number of non-overlapping trade blocks $N$ is calculated via:
$$N = \left( \frac{z_{1 - \alpha/2} + z_{1 - \beta}}{\mu_{\Delta} / \sigma} \right)^2 = \left( \frac{1.96 + 0.8416}{25.0 / 400.0} \right)^2 = \left( \frac{2.8016}{0.0625} \right)^2 = (44.83)^2 \approx \mathbf{2,010\text{ trades}}$$

However, when evaluated on **paired differences** where variance is confined strictly to the discordant/suppressed trades ($\sigma_{\Delta} \approx 250\text{ bps}$, effect size $\mu_{\text{avoidance}} \ge \mathbf{70.0\text{ bps}}$):
$$N_{\text{paired}} = \left( \frac{1.96 + 0.8416}{70.0 / 250.0} \right)^2 = \left( \frac{2.8016}{0.28} \right)^2 = (10.0)^2 = \mathbf{100\text{ trades}}$$

Therefore, **$N = 100$ non-overlapping trade blocks** is the mathematically justified minimum sample size to achieve 80% power for detecting the historical avoidance edge.

---

## 6. Strict Non-Peeking Stopping Rule

To prevent alpha decay from continuous monitoring:
1. No interim hypothesis testing will be conducted before $N = 100$ closed signals are recorded.
2. The ledger will accumulate silently in shadow mode.
3. The confirmatory gates will be executed exactly once upon reaching block $N = 100$.

