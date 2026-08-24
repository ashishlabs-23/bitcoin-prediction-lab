# Pre-Registration: Multi-Quantile Probabilistic Volatility Forecasting (DISTRIBUTION-01)
**Document Status**: LOCKED PRIOR TO TRIAL EXECUTION  
**Target File**: `results/distribution_01_preregistration.md`  
**Execution Timestamp**: 2026-08-24T21:15:00Z  
**Research Protocol**: Conditional Predictive Distribution Estimation & Dependence-Aware Conformalization  
**Fixed Ground-Truth Target**: Forward 7-Day Realized Variance $RV_{7d, t}^2 = \frac{8760}{168} \sum_{i=1}^{168} r_{t+i}^2$  
**Evaluation Principle**: Evaluated directly and independently against ground-truth $RV_{7d, t}^2$ (Zero circular imitation of $C_2$)  

---

## 1. Research Question & Rationale

> **Core Scientific Question**:  
> Can BTCognitive estimate the **conditional predictive distribution of forward 7-day realized variance ($RV_{7d, t}^2$)** across a dense 19-quantile grid:
> $$\boldsymbol{\alpha} = [0.01, 0.025, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.975, 0.99]$$
> (exposing 7 product quantiles: $[Q_{0.05}, Q_{0.10}, Q_{0.25}, Q_{0.50}, Q_{0.75}, Q_{0.90}, Q_{0.95}]$) satisfying **nondecreasing quantile ordering ($Q_{\alpha_1} \le Q_{\alpha_2}$)**, achieving **statistically significant improvement in Continuous Ranked Probability Score (CRPS)** over baselines, and maintaining **robust extreme-tail containment ($P(y \in [Q_{0.05}, Q_{0.95}] \mid y \in Q_5) \ge 88.0\%$)**?

---

## 2. Invariants & Mathematical Formulation

### A. Nondecreasing Quantile Ordering & Isotonic Rearrangement Pipeline
All raw model forecasts $\hat{\mathbf{Q}}_t^{\text{raw}}$ are passed through an immutable isotonic rearrangement transformation (Chernozhukov et al., 2010):
$$\hat{\mathbf{Q}}_t^{\text{final}} = \operatorname{Sort}\left(\hat{\mathbf{Q}}_t^{\text{raw}}\right)$$
**Governance Rule**: ALL scoring, pinball losses, CRPS, PIT diagnostics, and calibration metrics are computed exclusively on $\hat{\mathbf{Q}}_t^{\text{final}}$. Raw crossing rates ($\text{Crossing}_{\text{raw}}$) and rearrangement distortion ($D_{\text{iso}} = \frac{1}{K}\sum |Q_k^{\text{raw}} - Q_k^{\text{final}}|$) are recorded as diagnostics.

### B. Trapezoidal Discrete CRPS Formulation
Continuous Ranked Probability Score is computed on the 19-point quantile grid using locked trapezoidal integration weights $w_k$:
$$\text{CRPS}_{\text{grid}}(F_t, y_t) = 2 \sum_{k=1}^K w_k \mathcal{L}_{\alpha_k}\left(y_t, \hat{Q}_{\alpha_k, t}^{\text{final}}\right)$$
where $\mathcal{L}_{\alpha}(y, q) = (y - q)(\alpha - \mathbb{I}(y < q))$ is the Pinball loss, and integration weights are:
$$w_1 = \frac{\alpha_2 - \alpha_1}{2} + \alpha_1, \quad w_k = \frac{\alpha_{k+1} - \alpha_{k-1}}{2} \ (1 < k < K), \quad w_K = \frac{\alpha_K - \alpha_{K-1}}{2} + (1 - \alpha_K)$$

### C. Piecewise-Linear Probability Integral Transform (PIT)
$$\hat{F}_t(y) = \begin{cases}
0.0 & \text{if } y < \hat{Q}_{\alpha_1, t} \\
\alpha_k + \frac{y - \hat{Q}_{\alpha_k, t}}{\hat{Q}_{\alpha_{k+1}, t} - \hat{Q}_{\alpha_k, t}} (\alpha_{k+1} - \alpha_k) & \text{if } y \in [\hat{Q}_{\alpha_k, t}, \hat{Q}_{\alpha_{k+1}, t}] \\
1.0 & \text{if } y > \hat{Q}_{\alpha_K, t}
\end{cases}$$
$$u_t = \hat{F}_t(y_t)$$

---

## 3. Candidate Model Ladder

| Model ID | Architecture | Methodology & Dependence Treatment | Role |
| :--- | :--- | :--- | :--- |
| **D0** | Corrected Log-Normal Parametric Baseline | $\mu_t = \ln(\hat{v}_t^{\text{HAR}}) - \frac{\sigma_t^2}{2}$, $\sigma_t$ from rolling residuals (ensures $\mathbb{E}[Y] = \hat{v}_t$) | Naive Parametric Benchmark |
| **D1** | Joint Multi-Quantile HAR-RS-DOW | Simultaneous Pinball minimization on asymmetric semivariance + DOW features | Quantile Baseline |
| **D2** | Standard Conformalized Quantile Regression (CQR) | Romano et al. (2019) non-conformity adjustments on hourly calibration pool (exchangeability baseline) | Standard CQR Benchmark |
| **D3** | **Dependence-Aware Multi-Quantile Conformal Forecaster** | **Conformalized quantile calibration using $L=168\text{h}$ non-overlapping sub-sampled calibration blocks (inherits $C_2$ dependence discipline)** | **Primary Challenger** |
| **D4** | Frozen $C_2$ Risk-Envelope Benchmark | Central $[L_t, U_t]$ from $C_2$ | Production Risk Benchmark |

---

## 4. Evaluation Framework & Admission Gates

### A. Primary Scoring & Decision Hierarchy
1. **Primary Decision Metric**: Statistically significant reduction in $\overline{\text{CRPS}}_{\text{grid}}$ relative to the best baseline (D0, D1, D2):
   $$\text{Paired DM Test on } d_t = \text{CRPS}_{\text{benchmark}, t} - \text{CRPS}_{D_3, t}: \quad \text{DM} > +1.96 \ (p < 0.05, L=168)$$
2. **Secondary Metric (Marginal Quantile Calibration Error / MACE & MQCE)**:
   $$\text{MACE} = \frac{1}{K} \sum_{k=1}^K \left| \hat{P}(y \le Q_{\alpha_k}) - \alpha_k \right| \le 2.5\% \quad \text{and} \quad \text{MQCE} = \max_k \left| \hat{P}(y \le Q_{\alpha_k}) - \alpha_k \right| \le 6.0\%$$
3. **Tertiary Metric (Q5 Extreme-Tail Containment)**:
   $$P(y_t \in [Q_{0.05, t}, Q_{0.95, t}] \mid y_t \in Q_5) \ge 88.0\%$$
   where $Q_5$ is the top 20% realized volatility regime ($y_t \ge P_{80}$).

---

## 5. Execution Sequence

```
Step 0: Lock DISTRIBUTION-01 Pre-Registration [LOCKED]
  │
Step 1: Ingest aligned dataset (2022-2026) with frozen 2026 untouched holdout partition (N=5,225)
  │
Step 2: Fit candidate models (D0, D1, D2, D3) on historical training data (2022-2025)
  │
Step 3: Deploy candidate models sequentially across untouched 2026 holdout
  │
Step 4: Execute isotonic rearrangement pipeline: Q_final = Isotonic(Q_raw)
  │
Step 5: Compute Trapezoidal CRPS_grid, Pinball Losses, MACE, MQCE, PIT Uniformity, and Q5 Containment
  │
Step 6: Compute Paired DM Test on CRPS Differentials with L=168h Newey-West correction
  │
Step 7: Output Full Comparative Distribution Report & Produce results/distribution_01_final_report.md
```
