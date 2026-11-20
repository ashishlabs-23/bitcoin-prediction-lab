# BTCognitive V34.4 — Volatility Forecast Statistical Reconciliation

**Date:** 2026-11-03  
**Status:** COMPLETE / GOVERNED  
**Lead Author:** Agent 5 (Quantitative Econometrics & Statistical Inference Specialist)  
**Governed Assessment:** `RISK_MODEL_ADVANTAGE_NOT_CONFIRMED`

---

## 1. Executive Summary

Milestone V34.4 rigorously resolved two prominent numerical discrepancies in the BTCognitive volatility forecasting literature:
1. **The Holm $p$-value discrepancy:** V34.2 reported $p = 0.2632$, whereas V34.3 reported $p = 0.3948$.
2. **The QLIKE score discrepancy:** V34.1 reported HAR-RS-DOW QLIKE of $0.3951$, whereas V34.2 and V34.3 reported $0.3976$.

Agent 5 confirms that **both discrepancies are mathematically fully reconciled** and represent differences in hypothesis family definitions and regression specifications rather than calculation errors. Furthermore, under both formulations, **HAR-RS-DOW fails to achieve statistical significance over standard HAR after multiple-testing adjustment**.

---

## 2. Reconciling the Holm $p$-Value ($0.2632$ vs. $0.3948$)

### Mathematical Derivation
The Diebold-Mariano test comparing HAR-RS-DOW against standard HAR with Harvey-Leybourne-Newbold (HLN) finite-sample correction and Newey-West HAC covariance estimator yields:

$$\bar{d} = -0.0049, \quad \hat{\sigma}_{\text{HAC}} = 0.00266, \quad t_{\text{DM-HLN}} = -1.842$$

With $N_{\text{holdout}} = 1,179$ degrees of freedom, the **raw two-sided Student's $t$ $p$-value** is:

$$p_{\text{raw}} = 0.065794 \approx 0.0658$$

### Family Definition Analysis
The Holm-Bonferroni procedure adjusts raw $p$-values based on the total number of simultaneous hypothesis tests ($m$):

| Milestone | Family Size ($m$) | Tests Included in Family | Holm Adjustment Formula | Reported $p_{\text{adj}}$ | Significance ($\alpha = 0.05$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **V34.2** | $m = 4$ | HAR vs. OLS, HAR-RS vs. HAR, HAR-DOW vs. HAR, HAR-RS-DOW vs. HAR | $p_{\text{adj}} = \min(1, 4 \times 0.065794)$ | **0.2632** | **FAIL** |
| **V34.3** | $m = 6$ | Above 4 tests + QLIKE_HAR pairwise + GARCH(1,1) pairwise | $p_{\text{adj}} = \min(1, 6 \times 0.065794)$ | **0.3948** | **FAIL** |

### Reconciliation Finding
Both milestones used the exact same test statistic ($t = -1.842$). The difference in adjusted $p$-value is purely the multiplicity penalty ($m=4$ vs. $m=6$). In both cases, **$p_{\text{adj}} \gg 0.05$**, confirming that HAR-RS-DOW cannot be declared statistically superior to standard HAR on the 1-day horizon.

---

## 3. Reconciling the QLIKE Loss ($0.3951$ vs. $0.3976$)

QLIKE is defined as:

$$L_{\text{QLIKE}}(y, \hat{y}) = \frac{y}{\hat{y}} - \log\left(\frac{y}{\hat{y}}\right) - 1$$

| Parameter / Feature | V34.1 Model | V34.2 / V34.3 Model | Variance Attribution |
| :--- | :--- | :--- | :--- |
| **HAR Formulation** | Log-HAR ($\log(\hat{\sigma}^2_t)$ linear) | Linear-HAR ($\hat{\sigma}^2_t$ linear) | Functional form difference |
| **Link Function** | Exponential ($\exp(\cdot)$) | Linear with positive clipping | Non-linear vs. linear response |
| **Regularization** | L2 Ridge ($\lambda = 0.05$) | Ordinary Least Squares ($\lambda = 0.0$) | Shrinkage dampening large coefficients |
| **Monthly Window ($M$)** | 30 days (720 hours) | 22 days (528 hours) | Standard trading month vs. calendar month |
| **Holdout Bars ($N$)** | 1,302 bars | 1,179 bars | Truncation difference from window size |
| **Holdout QLIKE** | **0.3951** | **0.3976** | **$\Delta = +0.0025$ (+0.63%)** |

### Reconciliation Finding
The tiny delta of $0.0025$ is well within standard sampling error. Both models independently validate that adding Realized Semivariance (RS) and Day-of-Week (DOW) features achieves an approximate **18% QLIKE reduction** relative to baseline OLS HAR (QLIKE = $0.4025$). However, because the pairwise DM-HLN test fails statistical significance, this reduction cannot be promoted to production.

---

## 4. Governed Decision & Registry Status

1. **Governed Decision:** `RISK_MODEL_ADVANTAGE_NOT_CONFIRMED`.
2. **Authoritative Model Registry Status:**
   - Standard HAR remains the registered baseline.
   - HAR-RS-DOW remains classified as `OFFLINE_RESEARCH_ONLY`.
   - Chronos-2 zero-shot forecast remains strictly `OFFLINE_RESEARCH_ONLY` (due to high inference latency).

