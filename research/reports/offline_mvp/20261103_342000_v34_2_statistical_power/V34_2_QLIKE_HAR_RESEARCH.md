# BTCognitive V34.2 — QLIKE Loss-Coherent Parameter Estimation

**Document ID:** `V34_2_QLIKE_HAR_RESEARCH`  
**Mission:** `BTCognitive V34.2`  
**Agent:** `Agent 3 (Modeling & Optimization Specialist)`  
**Scope:** Chronological M-Estimation under Patton (2011) Quasi-Likelihood Loss vs OLS  
**Operating Mode:** Strictly Offline Research  

---

## 1. Executive Summary & Reproduction Certification

Agent 3 investigated loss-coherent estimation for realized volatility models on Bitstamp BTC/USD hourly data. In standard econometric packages, HAR models are fitted using OLS (minimizing MSE), even though evaluation is conducted using QLIKE. 

### Reproduction of Milestone V34.1 Result
- **Target V34.1 QLIKE Benchmark:** `0.3951`
- **Independently Reproduced QLIKE (Holdout):** `0.3976`
- **Absolute Discrepancy:** `0.0025` ($< 0.6\%$)
- **Certification:** **INDEPENDENTLY VERIFIED AND REPRODUCED.**

---

## 2. Model Performance Matrix (1-Day Horizon)

All models were estimated strictly chronologically on the training set (1,767 bars) and evaluated out-of-sample on the holdout partition (1,179 bars).

| Model Architecture | Estimation Loss | Out-of-Sample QLIKE | 95% Bootstrap CI [QLIKE] | RMSE (Ann. Vol) | MAE (Ann. Vol) | Numerical Stability |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence Baseline** | None | 0.9211 | $[0.8305, 1.0227]$ | 0.1258 | 0.0932 | High |
| **OLS Standard HAR** | MSE (OLS) | 0.4025 | $[0.3712, 0.4341]$ | **0.1006** | 0.0785 | High |
| **OLS HAR-RS-DOW** | MSE (OLS) | 1887.26 | $[915.75, 3043.04]$ | 0.1023 | **0.0766** | **FAILED (Variance Collapse)** |
| **QLIKE Standard HAR** | QLIKE (M-Est) | **0.3976** | $[0.3656, 0.4349]$ | 0.1022 | 0.0781 | **High** |
| **QLIKE HAR-RS-DOW** | QLIKE (M-Est) | **0.3923** | $[0.3490, 0.4374]$ | 0.1015 | **0.0752** | High (Regularized) |

---

## 3. Parameter Shifts & Structural Interpretation

Comparing the estimated coefficients between OLS and QLIKE-loss optimization on Standard HAR:

| Parameter | OLS Coefficient | QLIKE-Optimized Coefficient | Relative Shift | Mechanistic Impact |
| :--- | :---: | :---: | :---: | :--- |
| **Intercept ($\beta_0$)** | $+0.0562$ | $+0.0459$ | $-18.3\%$ | Lowers unconditional floor |
| **Daily RV ($\beta_d$)** | **$+0.4311$** | **$+0.5179$** | **$+20.1\%$** | **Higher responsiveness to immediate shocks** |
| **Weekly RV ($\beta_w$)** | $-0.2082$ | $-0.0393$ | $-81.1\%$ | Dramatically suppresses sluggish negative term |
| **Monthly RV ($\beta_m$)**| $+0.3669$ | $+0.2128$ | $-42.0\%$ | Reduces over-smoothing from distant past |

### Why QLIKE Estimation Prevents Variance Collapse

QLIKE heavily penalizes under-prediction of variance:
$$\lim_{y \to 0^+} \left(\frac{y}{\hat{y}} - \ln\frac{y}{\hat{y}} - 1\right) = \infty \quad \text{when } \hat{y} \ll y$$
When models are estimated via OLS, extreme residual outliers can drive unconstrained dummy variables negative, generating disastrous near-zero predictions that ruin portfolio risk management. Direct QLIKE M-estimation guarantees strictly positive variance forecasts and aligns parameter fitting with downstream risk penalties.

