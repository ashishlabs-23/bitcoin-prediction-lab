# BTCognitive V33.3C — Out-of-Sample Statistical Validation & Multiple Testing Audit

**Milestone:** V33.3C — HTF Strategy Final Evidence Reconciliation  
**Date:** 2026-10-31  
**Target:** Rigorous Statistical Testing, Confidence Intervals, and Family-Wise Bonferroni Audit  
**Authoritative Ledger:** `v33_3c_cross_milestone_trade_mapping.csv`  

---

## 1. Executive Summary & Epistemic Verdict

The statistical evaluation establishes two complementary conclusions:
1. **Descriptive Empirical Improvement:** Across the historical dataset, the regime filter improves trade expectancy (+59.25 bps vs +9.57 bps full-period; +16.53 bps vs +2.68 bps OOS) by suppressing adverse consolidation false breakouts.
2. **Confirmatory Statistical Hurdle Fails:** Under rigorous econometrics standards (Welch's t-test, finite-sample uncertainty, and family-wise Bonferroni correction for testing 19 strategy candidates), the Out-of-Sample improvement **does not achieve statistical significance** ($p = 0.827$ against baseline; $p = 0.683$ against excluded trades).

> **Epistemic Invariant (Operating Contract Principle 4):**  
> Because the regime exclusion logic was developed after inspecting the full 2022–2026 dataset, the 2024–2026 period represents **retrospective development data**, not fresh confirmatory evidence. Under no circumstances can these figures be cited as proof of a production-ready edge.

---

## 2. Chronological Performance and Statistical Estimation

### Table: Statistical Comparison Across All Three Cohorts (Binance VIP0 26 bps)

| Metric | Full Period (2022–2026) | In-Sample (2022–2023) | Out-of-Sample (2024–2026) |
| :--- | :---: | :---: | :---: |
| **Baseline Trade Count ($N_{\text{base}}$)** | 194 | 75 | 119 |
| **Filtered Trade Count ($N_{\text{filt}}$)** | 110 | 46 | 64 |
| **Excluded Trade Count ($N_{\text{excl}}$)** | 84 | 29 | 55 |
| **Baseline Net EV ($\mu_{\text{base}}$)** | **+9.57 bps** | **+20.51 bps** | **+2.68 bps** |
| Baseline Std Dev ($\sigma_{\text{base}}$) | 437.36 bps | 494.78 bps | 399.02 bps |
| Baseline Win Rate | 43.8% | 44.0% | 43.7% |
| **Filtered Net EV ($\mu_{\text{filt}}$)** | **+59.25 bps** | **+118.70 bps** | **+16.53 bps** |
| Filtered Std Dev ($\sigma_{\text{filt}}$) | 454.08 bps | 504.66 bps | 412.78 bps |
| Filtered Win Rate | 48.2% | 50.0% | 46.9% |
| **Excluded Net EV ($\mu_{\text{excl}}$)** | **−55.49 bps** | **−135.25 bps** | **−13.43 bps** |
| Excluded Std Dev ($\sigma_{\text{excl}}$) | 407.99 bps | 443.51 bps | 385.54 bps |
| Excluded Win Rate | 38.1% | 34.5% | 40.0% |
| **Filter Net Advantage ($\Delta_{\text{filt - base}}$)** | **+49.68 bps** | **+98.20 bps** | **+13.85 bps** |
| **Filter Avoidance Gain ($\Delta_{\text{filt - excl}}$)** | **+114.74 bps** | **+253.95 bps** | **+29.96 bps** |

---

## 3. Parametric & Non-Parametric Hypothesis Tests

### A. Full Period (2022–2026)
- **Filtered vs. Baseline:**  
  $$t = 0.929, \quad p = 0.3539 \quad (\text{Welch's } t\text{-test, two-tailed})$$
- **Filtered vs. Excluded:**  
  $$t = 1.848, \quad p = 0.0662 \quad (\text{Welch's } t\text{-test, two-tailed; one-tailed } p = 0.0331)$$
  *The full-period difference between retained and excluded trades approaches marginal significance at $\alpha = 0.05$ (one-tailed), driven primarily by the massive avoidance gain during 2022–2023.*

### B. Out-of-Sample Period (2024–2026)
- **Filtered vs. Baseline:**  
  $$t = 0.219, \quad p = 0.8271 \quad (\text{Welch's } t\text{-test, two-tailed})$$
- **Filtered vs. Excluded:**  
  $$t = 0.409, \quad p = 0.6833 \quad (\text{Welch's } t\text{-test, two-tailed})$$
- **95% Confidence Interval for OOS Filtered Net EV:**
  $$\mu \in [+16.53 \pm 1.96 \times (412.78 / \sqrt{64})] = [+16.53 \pm 101.13\text{ bps}] = [−84.60\text{ bps}, \mathbf{+117.66\text{ bps}}]$$
  *Because the 95% confidence interval spans zero widely, the positive OOS point estimate (+16.53 bps) cannot be distinguished from zero or the baseline (+2.68 bps).*

---

## 4. Family-Wise Multiple Testing Audit (Bonferroni Correction)

BTCognitive evaluates a candidate pool of **19 strategy engines** in the Strategy Tournament (`engine/regime_strategy_tournament.py`):

$$\alpha_{\text{family}} = 0.05$$
$$\alpha_{\text{Bonferroni}} = \frac{0.05}{19} = \mathbf{0.00263}$$

| Candidate Scope | Test Comparison | Observed $p$-value | Bonferroni Threshold | Decision |
| :--- | :--- | :---: | :---: | :---: |
| Full Period | Filtered vs Excluded | $p = 0.0662$ | $\alpha = 0.00263$ | **FAIL (Insignificant)** |
| In-Sample | Filtered vs Excluded | $p = 0.0120$ | $\alpha = 0.00263$ | **FAIL (Insignificant)** |
| Out-of-Sample | Filtered vs Baseline | $p = 0.8271$ | $\alpha = 0.00263$ | **FAIL (Insignificant)** |
| Out-of-Sample | Filtered vs Excluded | $p = 0.6833$ | $\alpha = 0.00263$ | **FAIL (Insignificant)** |

Across all horizons, the hypothesis that the regime filter produces a statistically distinguishable edge fails the Bonferroni multiple testing hurdle.

---

## 5. Strategic Determination

The filter provides a **positive empirical heuristic** that successfully eliminated 84 trades with negative aggregate returns (−55.49 bps full-period). However, the resulting out-of-sample edge is thin (+16.53 bps) and statistically unconfirmed.

**Governed Category:** `EXPLORATORY_ONLY_SELECTION_BIAS` / `REPRODUCIBLE_IMPROVEMENT_CANDIDATE` (Retained as research candidate; production promotion prohibited).

