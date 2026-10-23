# BTCognitive — Quantitative Research Synthesis: Bitcoin Realized Volatility Forecasting & Statistical Evaluation

**Document Identifier:** `RES-2026-SYNTH-01`  
**Date:** 16 October 2026  
**Author:** Quantitative Research Specialist (Agent B)  
**Governing Standard:** BTCognitive Permanent Research Contract (AGENTS.md)  
**Status:** Approved Quantitative Research Synthesis  

---

## Executive Summary

This research synthesis provides an econometric evaluation of Bitcoin realized volatility forecasting models, loss function robustness under proxy noise, finite-sample predictive accuracy testing, and modern non-exchangeable conformal prediction. 

Eight primary sources are analyzed to establish why **Heterogeneous Autoregressive with Realized Semivariance and Day-of-Week Seasonality (`HAR-RS-DOW`)** serves as our canonical production reference, how the **24-Hour QLIKE-coherent challenger (`HAR-QLIKE-24H`)** relates to it, and why high-frequency jump estimators and deep learning architectures must remain bounded by strict data resolution contracts.

---

## 1. Primary Source Analysis & Methodological Rigor

### 1. Shen, Urquhart & Wang (2020) — Jumps & Structural Breaks
- **Citation:** Shen, D., Urquhart, A., & Wang, P. (2020). *Forecasting the volatility of Bitcoin: The importance of jumps and structural breaks.* European Financial Management, 26(5), 1294–1326. DOI: `10.1111/eufm.12254`.
- **Target & Horizon:** Daily realized volatility ($RV_t$) and multi-day horizons (1-day, 5-day, 22-day).
- **Required Resolution & Input Data:** High-frequency intraday prices (e.g., 5-minute or 1-minute bars) to compute Realized Bipower Variation ($BV_t$):
  $$BV_t = \frac{\pi}{2} \left(\frac{M}{M-1}\right) \sum_{i=2}^{M} |r_{t,i}| |r_{t,i-1}|$$
  The continuous sample path component is estimated by $C_t = BV_t$, and the jump component by $J_t = \max(RV_t - BV_t, 0)$, combined with formal test statistics (Barndorff-Nielsen & Shephard, 2006).
- **Core Findings & Mathematical Assumptions:**
  - Jumps account for a substantial fraction of total quadratic variation in Bitcoin.
  - Adding jump components to a standard HAR model (HAR-J) significantly improves forecast accuracy across horizons.
  - Accounting for endogenous structural breaks (using Bai & Perron tests) substantially mitigates forecast decay during regime transitions.
- **Critical Architectural Boundary for BTCognitive:**
  > [!WARNING]
  > **Resolution Integrity Warning:** A model utilizing hourly closed candles ($M=24$) cannot compute a reliable high-frequency jump estimator. Bipower variation with $M=24$ has insufficient power and will conflate intra-hour volatility clustering with true discontinuous Poisson jump arrivals. Jump-aware HAR-J models in BTCognitive are strictly restricted to datasets with 5-minute or higher resolution.

---

### 2. Bergsli, Bjønnes & Liang (2022) — Crypto Realized Volatility & Semivariance
- **Citation:** Bergsli, L. O., Bjønnes, G. H., & Liang, C. (2022). *Forecasting volatility of Bitcoin.* Research in International Business and Finance, 59, 101540. DOI: `10.1016/j.ribaf.2021.101540`.
- **Target & Horizon:** 1-day, 7-day, and 30-day realized volatility.
- **Required Resolution & Input Data:** Intraday or hourly returns to compute signed semivariances ($RV^+, RV^-$).
- **Core Findings:**
  - Traditional GARCH-type models (GARCH, EGARCH, GJR-GARCH) are systematically outperformed by HAR-family models.
  - Decomposing realized variance into continuous upside ($RV^+$) and downside ($RV^-$) semivariances (Barndorff-Nielsen et al., 2010) delivers persistent gains because Bitcoin exhibits asymmetric volatility responses to price drops.
  - HAR models incorporating day-of-week seasonality (DOW) capture the regular drop in trading volume and variance observed during weekends.
- **Local Application in BTCognitive:**
  This paper provides direct empirical validation for BTCognitive's canonical production model: `HAR-RS-DOW-v1.0`.

---

### 3. Patton (2011) — Volatility Forecast Comparison Under Imperfect Proxies
- **Citation:** Patton, A. J. (2011). *Volatility forecast comparison using imperfect volatility proxies.* Journal of Econometrics, 160(1), 246–256. DOI: `10.1016/j.jeconom.2010.03.034`.
- **Mathematical Foundation:**
  Because true latent conditional variance $\sigma_t^2$ is unobservable, empirical models evaluate forecasts $\hat{h}_t$ against an imperfect proxy $\tilde{\sigma}_t^2$ (such as $RV_t$). Patton proves that model rankings are **invariant to proxy noise** (i.e., preserve the same expected ranking as if evaluated against true latent variance $\sigma_t^2$) **if and only if** the loss function $L(\tilde{\sigma}_t^2, \hat{h}_t)$ belongs to the homogeneous Bregman loss family:
  $$L(\tilde{\sigma}^2, \hat{h}; p) = \frac{1}{(p+1)(p+2)} \left( \tilde{\sigma}^{2(p+2)} - \hat{h}^{p+2} \right) - \frac{1}{p+1} \hat{h}^{p+1} (\tilde{\sigma}^2 - \hat{h})$$
- **The Two Canonical Losses:**
  1. **Mean Squared Error (MSE, $p=0$):**
     $$L_{\text{MSE}}(y, \hat{y}) = (y - \hat{y})^2$$
  2. **Quasi-Likelihood (QLIKE, $p=-2$):**
     $$L_{\text{QLIKE}}(y, \hat{y}) = \frac{y}{\hat{y}} - \ln\left(\frac{y}{\hat{y}}\right) - 1$$
- **Economic Asymmetry of QLIKE:**
  Unlike MSE, which penalizes absolute deviations symmetrically, QLIKE heavily penalizes underpredicting variance ($\hat{y} \ll y$) compared to overpredicting. In risk intelligence and margin requirement estimation, volatility underestimation leads to catastrophic insolvency; hence, QLIKE is the mathematically mandated loss function for our 24h research challenger.

---

### 4. Diebold & Mariano (1995) — Asymptotic Predictive Accuracy Comparison
- **Citation:** Diebold, F. X., & Mariano, R. S. (1995). *Comparing Predictive Accuracy.* Journal of Business & Economic Statistics, 13(3), 253–263. DOI: `10.1080/07350015.1995.10524599`.
- **Formulation:**
  Let $d_t = L(y_t, \hat{y}_{1t}) - L(y_t, \hat{y}_{2t})$ be the loss differential series between model 1 and model 2. Under the null hypothesis of equal predictive accuracy:
  $$H_0: \mathbb{E}[d_t] = 0$$
  The test statistic is:
  $$DM = \frac{\bar{d}}{\sqrt{\hat{V}(\bar{d}) / T}} \xrightarrow{d} \mathcal{N}(0, 1)$$
  where $\hat{V}(\bar{d})$ is a consistent estimate of the asymptotic long-run variance of $\bar{d}$ accounting for serial correlation up to horizon $h-1$.

---

### 5. Harvey, Leybourne & Newbold (1997) — Finite-Sample Correction
- **Citation:** Harvey, D., Leybourne, S., & Newbold, P. (1997). *Testing the equality of prediction mean squared errors.* International Journal of Forecasting, 13(2), 281–291. DOI: `10.1016/S0169-2070(96)00719-4`.
- **Problem with Standard DM:**
  In financial time-series with finite samples ($T < 500$) and multi-step forecast horizons ($h > 1$), the standard DM test suffers from severe over-rejection of the null hypothesis (inflated Type I error), causing false discoveries.
- **The HLN Correction:**
  Harvey, Leybourne, and Newbold introduce a finite-sample modified statistic:
  $$HLN = DM \times \left[ \frac{T + 1 - 2h + h(h-1)/T}{T} \right]^{1/2}$$
  Critically, HLN is evaluated against **Student's $t$ distribution with $T-1$ degrees of freedom**, rather than standard normal critical values.
- **Governance Requirement in BTCognitive:**
  All paired model comparisons in BTCognitive must report both raw $DM$ and corrected $HLN$ with exact $p$-values.

---

### 6. Time-Series Cross-Validation (Hyndman)
- **Citation:** Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice* (3rd ed.). OTexts: `https://otexts.com/fpptr/tscv.html`.
- **Principle:** Rolling-origin (rolling evaluation) evaluates a model on a series of test windows where the training set consists only of observations that occurred strictly prior to the forecast origin.
- **Purging & Embargoing:** For multi-step targets (such as $h=24$ or $h=168$), training sets must purge overlapping label windows, and an embargo period equal to the target horizon must separate train and test splits to prevent lookahead leakage from autocorrelated labels.

---

### 7. Dependence-Aware Conformal Coverage Inference (Preprint, Sep 2026)
- **Citation:** Preprint (arXiv:2609.33868, Sep 2026). *Dependence-Aware Conformal Coverage Inference.*
- **Epistemic Classification:** Research Preprint (Exploratory / Emerging literature, not settled consensus).
- **Core Insight:**
  Standard split conformal prediction relies on the assumption of exchangeability ($i.i.d.$ data). In financial time series, returns and volatility exhibit strong serial autocorrelation, volatility clustering, and conditional heteroscedasticity. Under serial dependence, naive conformal sets experience severe localized undercoverage during volatility expansion shocks.
- **Methodology:**
  Introduces block-wise non-conformity score quantile estimation with temporal decay weighting, ensuring valid conditional coverage over autocorrelated horizons without requiring arbitrary residual Gaussianity assumptions.

---

### 8. Rolling-Origin Conformal Prediction Under Local Stationarity (Preprint, May 2026)
- **Citation:** Preprint (arXiv:2605.08422, May 2026). *Rolling-Origin Conformal Prediction Under Local Stationarity and Weak Dependence.*
- **Epistemic Classification:** Research Preprint (Exploratory / Emerging literature, not settled consensus).
- **Core Insight:**
  Extends online conformal prediction by modeling financial time-series as locally stationary processes. Rather than pooling residuals over long historical windows where the market regime has shifted, conformal quantiles are estimated using an exponentially weighted rolling origin:
  $$\hat{q}_t(\alpha) = \inf \left\{ q : \sum_{i=1}^{t-1} w_{t,i} \cdot \mathbb{I}_{\{s_i \le q\}} \ge 1 - \alpha \right\}$$
  where $w_{t,i} = \lambda^{t-i} / \sum_{j} \lambda^{t-j}$ dynamically adapts the prediction interval width to the prevailing volatility regime.

---

## 2. Comparative Matrix: Realized Volatility Candidates

| Candidate Model | Target & Horizon | Required Resolution | Primary Mathematical Assumption | Expected Advantage | Failure Modes | Computational Cost | Local Testability |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Conventional HAR-RV** (Corsi 2009) | $RV_{t+h}$ (Daily/Weekly) | Hourly / Intraday | Linear cascade of heterogeneous horizons (daily, weekly, monthly) | Simple, robust, linear, highly interpretable | Ignores return sign asymmetry and day-of-week drop | Negligible (<5ms OLS) | **Yes** (fully supported) |
| **HAR-RS-DOW-v1.0** (Canonical Baseline) | $\text{rv7d\_var\_ann}$ (168h) | Hourly closed bars ($N=40,902$) | Asymmetric semivariances ($RV^+, RV^-$) and weekend volume seasonality | Captures weekend liquidity drop and negative return volatility spikes | Parameter drift over multi-year regimes | Negligible (<10ms OLS) | **Yes** (Frozen & Authorized) |
| **HAR-QLIKE-24H** (Research Challenger) | $\text{rv24h\_var\_ann}$ (24h) | Hourly closed bars ($N=40,902$) | Nonlinear QLIKE loss minimization via BFGS | Direct loss coherence with Patton 2011; penalizes variance underprediction | Insignificant HLN gain ($p \ge 0.05$); non-convex optimization | Low (<2s BFGS) | **Yes** (Retained Research Only) |
| **Rolling Structural Break HAR** (Shen 2020) | $RV_{t+h}$ (1d–7d) | Hourly / 5m bars | Structural breaks in intercept and autoregressive parameters | Adapts to secular regime changes (e.g., ETF approval) | Overfitting break dates on short windows; lag in break detection | Moderate (~30s Bai-Perron) | **Yes** (Planned for Milestone 3) |
| **HAR-J Jump Estimator** (Shen 2020) | $RV_{t+h}$ (1d–7d) | High-Frequency ($\le 5\text{m}$) | Bipower variation isolates continuous sample path from jump process | Disentangles persistent continuous variance from transitory jump noise | **Invalid on hourly bars** ($M=24$ lacks test power) | Moderate (Requires 5m storage) | **Blocked** (Awaiting 5m feed) |
| **Adaptive Conformal C2** (arXiv:2605.08422) | Risk Envelope $[L_t, U_t]$ | Matched to model | Local stationarity; exponentially weighted non-conformity scores | Responsive conditional coverage without interval blow-up | Tuning decay parameter $\lambda$; lag during abrupt regime shift | Low (<50ms per origin) | **Yes** (Under Milestone 3 Gate) |

---

## 3. Governed Research Decision on Candidates

1. **Retain `HAR-RS-DOW-v1.0` as Sole Authorized Production Reference:**
   - Evaluated on forward 168-hour annualized variance target.
   - Robust, OLS-based, cryptographically verified, fully causal.
2. **Classify `HAR-QLIKE-24H` as Offline Research Challenger:**
   - Raw QLIKE is 14.84% lower than OLS, but HLN $p = 0.1622$ on daily non-overlapping origins and $p = 0.0735$ on hourly origins.
   - Fails the confirmatory threshold ($p < 0.05$); retained for prospective tracking.
3. **Reject High-Frequency Jump Claims on Hourly Data:**
   - As established from Shen et al. (2020), jump decomposition requires 5-minute or tick data. BTCognitive strictly prohibits labeling hourly bipower variation approximations as high-frequency jump models.
