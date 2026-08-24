# Pre-Registration: Volatility Prediction Interval & Uncertainty Calibration Trial (UNCERTAINTY-01)
**Document Status**: LOCKED PRIOR TO INFERENCE & EVALUATION  
**Target File**: `results/uncertainty_01_preregistration.md`  
**Execution Timestamp**: 2026-08-24T20:35:00Z  
**Research Paradigm**: Point Forecast Frozen (HAR-RS-DOW) $\rightarrow$ Research Focus on Conformal Uncertainty Calibration  
**Target Horizon**: 7-Day Realized Variance (`rv7d_var_ann`, $h=168\text{ hours}$)  

---

## 1. Research Question & Rationale

> **Core Scientific Question**:  
> Can **BTCognitive's scale-aware, asymmetric temporal conformal calibration engine** construct **empirically valid ($P(y_t \in [L_t, U_t]) \approx 1 - \alpha$), regime-resilient, and sharp (minimum width / Winkler score)** prediction intervals for forward 7-day realized variance beyond conventional parametric Gaussian and rolling empirical quantile baselines, when evaluated on a frozen **HAR-RS-DOW** point forecast?

### The Strategic Paradigm Shift:
* **Stages 1–3 (Directional / Macro / Micro Alpha Hunting)**: ❌ **REJECTED**. Adding exogenous features failed to produce persistent out-of-sample edge.
* **Stage 5 (Synthetic Payoff Forensic)**: ⚠️ **FROZEN**. Exposed "free option" artifact.
* **Stage 6 (VOL-EDGE-01 Incremental Information Trial)**: 🔒 **ARCHIVED**. Established that **HAR-RS-DOW** is the dominant point-forecast baseline ($\text{QLIKE} = 0.19300$), while neither 7D ATM IV nor compression added practically meaningful incremental forecasting value.
* **Stage 7 (UNCERTAINTY-01)**: 🎯 **CURRENT MILESTONE**. Transition from chasing point-forecast alpha to **quantifying predictive uncertainty around the frozen best baseline (HAR-RS-DOW)**.

---

## 2. Target Variable & Frozen Point Forecast Architecture

### A. Target Variable: Annualized 7-Day Realized Variance (`rv7d_var_ann`)
* **Sampling**: Continuous hourly log returns $r_\tau = \ln(P_\tau / P_{\tau-1})$ from authenticated BTC spot OHLCV (2022–2026).
* **Horizon**: $h = 168\text{ hours}$ (7 calendar days).
* **Formula**:
  $$\text{rv7d\_var\_ann}_t = \frac{8760}{168} \sum_{i=1}^{168} r_{t+i}^2$$

### B. Frozen Point Forecast: HAR-RS-DOW
* **Regressors**: Log realized downward semivariance $\ln(\text{rv\_down\_1d})$, log realized upward semivariance $\ln(\text{rv\_up\_1d})$, log weekly trailing variance $\ln(\text{rv7d\_var\_ann\_lag})$, log monthly trailing variance $\ln(\text{rv30d\_var\_ann})$, and Day-of-Week (DOW) categorical dummies.
* **Structural Positivity**:
  $$\ln(\hat{v}_t) = \mathbf{X}_t^\top \boldsymbol{\beta} \implies \hat{v}_t = \exp\left(\mathbf{X}_t^\top \hat{\boldsymbol{\beta}}\right) > 0$$
* **Invariant**: The point forecast $\hat{v}_t$ is strictly frozen across all uncertainty interval candidates.

---

## 3. Asymmetric, Heteroskedastic Scale-Aware Conformity Scoring

Realized variance is strictly non-negative, heavily right-skewed, heteroskedastic, and subject to volatility clustering. A constant absolute error $|y_t - \hat{v}_t|$ is invalid across volatility regimes.

### A. Heteroskedastic Normalization
* **Conditional Residual Volatility Scale**: $\hat{\sigma}_{\epsilon, t}$ estimated on trailing historical point forecast residuals $e_\tau = y_\tau - \hat{v}_\tau$ via rolling exponential weighting.
* **Scale-Normalized Residual**:
  $$z_t = \frac{y_t - \hat{v}_t}{\hat{\sigma}_{\epsilon, t} + \epsilon_{\text{floor}}}$$

### B. Asymmetric Directional Scoring
To reflect positive skewness and prevent lower intervals from collapsing into negative variance or failing upper volatility spikes:
* **Upper Deviation Score**: $s_t^+ = \max\left(0, \frac{y_t - \hat{v}_t}{\hat{\sigma}_{\epsilon, t} + \epsilon}\right)$
* **Lower Deviation Score**: $s_t^- = \max\left(0, \frac{\hat{v}_t - y_t}{\hat{\sigma}_{\epsilon, t} + \epsilon}\right)$
* **Interval Bounds Formulation**:
  $$L_t = \max\left(10^{-6}, \, \hat{v}_t - q_{1-\alpha/2}^- \cdot \hat{\sigma}_{\epsilon, t}\right)$$
  $$U_t = \hat{v}_t + q_{1-\alpha/2}^+ \cdot \hat{\sigma}_{\epsilon, t}$$

---

## 4. Candidate Uncertainty Interval Ladder (U0 $\rightarrow$ U4)

Target nominal coverage: **$1 - \alpha = 0.90$** (90% prediction interval).

| Interval ID | Model Name | Calibration Mechanism | Epistemic Hypothesis Role |
| :--- | :--- | :--- | :--- |
| **U0** | **Parametric Gaussian** | $\hat{v}_t \pm z_{0.95} \hat{\sigma}_{\epsilon, t}$ (assuming normal residuals) | Classical Parametric Benchmark (known to fail heavy tails) |
| **U1** | **Rolling Empirical Quantiles** | Trailing 720-hour empirical quantiles of $(y_\tau - \hat{v}_\tau)$ | Non-parametric Rolling Benchmark |
| **U2** | **Standard Split Conformal** | Exchangeable conformal calibration on held-out split | Standard Conformal Benchmark (violates time series dependence) |
| **U3** | **Block Conformal (EnbPI)** | Sequential block-resampled residuals (preserving $L=168$ autocorrelation) | Time-Series Overlap-Aware Conformal Benchmark |
| **U4** | **Adaptive Asymmetric Conformal** | **BTCognitive Challenger**: Scale-aware asymmetric conformal with regime tracking | **Primary Challenger Engine** |

---

## 5. Multi-Dimensional Evaluation Framework (Coverage + Sharpness)

Prediction intervals cannot be evaluated on coverage alone (an infinite interval trivially achieves 100% coverage).

### A. Primary Evaluation Metrics:
1. **Empirical Coverage**:
   $$\hat{C} = \frac{1}{N} \sum_{t=1}^N \mathbb{I}\left(y_t \in [L_t, U_t]\right) \quad (\text{Target: } 90.0\% \pm 2.0\%)$$
2. **Mean Interval Width (Sharpness)**:
   $$\overline{W} = \frac{1}{N} \sum_{t=1}^N (U_t - L_t)$$
3. **Winkler Interval Score** (Proper Scoring Rule for $\alpha=0.10$):
   $$\text{Score}_t = (U_t - L_t) + \frac{2}{\alpha}(L_t - y_t)\mathbb{I}(y_t < L_t) + \frac{2}{\alpha}(y_t - U_t)\mathbb{I}(y_t > U_t)$$
   $$\overline{\text{Winkler}} = \frac{1}{N} \sum_{t=1}^N \text{Score}_t \quad (\text{Lower is better})$$
4. **Tail Balance Metrics**:
   * Upper Breach Rate: $\alpha_{\text{upper}} = \frac{1}{N} \sum \mathbb{I}(y_t > U_t) \quad (\text{Target: } 5.0\%)$
   * Lower Breach Rate: $\alpha_{\text{lower}} = \frac{1}{N} \sum \mathbb{I}(y_t < L_t) \quad (\text{Target: } 5.0\%)$

### B. Mandatory Regime-Conditional Coverage Audit:
Coverage must be reported independently across all 4 historical macro epochs:
* Regime 2 (Fed Hiking Bear: 2022–2023)
* Regime 3 (Transition Compression: 2023–2024)
* Regime 4 (Spot ETF Institutional Era: 2024–2026)
* High-Volatility Clustered Epochs vs. Quiet Epochs

---

## 6. Decisive Admission Gate for UNCERTAINTY-01

For **U4 (Adaptive Asymmetric Conformal)** to be validated for production promotion into BTCognitive:
1. **Valid Overall Coverage**: $|\hat{C}_{\text{overall}} - 0.90| \le 0.025$ ($87.5\% \le \hat{C} \le 92.5\%$).
2. **Regime Robustness**: $\hat{C}_{\text{regime}} \ge 82.5\%$ for every individual macro regime (no catastrophic blindspots).
3. **Strict Sharpness Advantage**:
   $$\overline{\text{Winkler}}_{\text{U4}} < \overline{\text{Winkler}}_{\text{U0, U1, U2, U3}} \quad \text{and} \quad \overline{W}_{\text{U4}} < \overline{W}_{\text{U3}}$$
4. **Tail Breach Symmetry**: $|\alpha_{\text{upper}} - \alpha_{\text{lower}}| \le 0.030$.

---

## 7. Execution Sequence

```
Step 0: Lock UNCERTAINTY-01 Pre-Registration (Nominal 90%, Winkler, L=168) [LOCKED]
  │
Step 1: Fit and freeze HAR-RS-DOW point forecasts out-of-sample (40,455 hours)
  │
Step 2: Generate baseline intervals (U0 Gaussian, U1 Empirical Quantile, U2 Split Conformal)
  │
Step 3: Generate sequential block-overlap conformal intervals (U3 EnbPI)
  │
Step 4: Generate scale-aware asymmetric adaptive conformal intervals (U4 Challenger)
  │
Step 5: Compute Overall & Regime-Conditional Coverage, Mean Width, and Winkler Scores
  │
Step 6: Execute Tail Breach Symmetry & Stress-Testing Audit
  │
Step 7: Output Full Comparative Table & Produce results/uncertainty_01_final_report.md
```
