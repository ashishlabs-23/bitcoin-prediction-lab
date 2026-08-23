# Empirical VPIN Toxicity & Jump-Prediction: Statistical Pre-Registration
**Document Status**: LOCKED & IMMUTABLE PRIOR TO INFERENCE  
**Target File**: `results/vpin_prediction_test_preregistration.md`  
**Execution Timestamp**: 2026-08-23T21:55:00Z  
**Research Protocol**: Rigorous Dual-Window Incremental Alpha Admission Trial  

---

## 1. Primary Hypothesis

> **Hypothesis $H_1$ (Incremental Toxicity Alpha)**:  
> Order flow toxicity measured via empirical `vpin_true` over the trailing 24 hours preceding hour $t$ contains **statistically significant incremental predictive power ($\Delta IC > 0$)** for forward-looking 24-hour Maximum Adverse Excursion ($y_{\text{MAE}, 24h}$) **above and beyond baseline volatility ($\sigma_{24h}$) and momentum ($\text{RSI}_{14}$)**. Specifically: elevated pre-event order flow toxicity precedes larger forward downside liquidation cascades after controlling for prevailing volatility.
>
> **Null Hypothesis $H_0$ (Volatility Confound / Ineffective Metric)**:  
> Pre-event empirical VPIN contains no incremental predictive information for residual downside excursion magnitude ($\Delta IC \le 0$), or demonstrates non-discriminative spurious correlation during tranquil market regimes.

---

## 2. Exact Mathematical & Feature Specifications

### A. Predictor Feature (Single Locked Transformation)
* **Variable Name**: `vpin_true_24h_mean`
* **Definition**: The continuous mean of `vpin_true` over all volume buckets completed in the trailing 24-hour window strictly prior to and including hour $t$:
  $$\text{vpin\_true\_24h\_mean}_t = \frac{1}{|K_t|} \sum_{k \in K_t} \text{vpin\_true}_k, \quad K_t = \{k \mid t - 24\text{h} < \tau_k \le t\}$$
* **Causal Invariant**: Strict point-in-time boundary; zero forward lookahead. Only bucket prints timestamped $\le t$ are visible at decision timestamp $t$.

### B. Target Variable & Verified Sign Convention
* **Variable Name**: `forward_mae_24h` ($y_{\text{MAE}, 24h}$)
* **Definition**: Forward 24-hour Maximum Adverse Excursion from hourly bar close at $t$:
  $$y_{\text{MAE}, 24h}(t) = \frac{P_t - \min_{i \in (0, 24]} P_{t+i}}{P_t} \ge 0$$
* **Sign Convention Verification**: $y_{\text{MAE}}$ is strictly positive ($y_{\text{MAE}} \ge 0$). A larger downside drop produces a higher positive value. Therefore, a positive correlation ($\Delta IC > 0$) indicates that higher toxicity correctly forecasts larger forward downside crash severity.

### C. Primary Gated Metric ($\Delta IC$) vs. Baseline Ridge Regressor
1. **Baseline Model**: Ridge regression fitted on baseline covariates $X_{\text{base}} = [\sigma_{24h}, \text{RSI}_{14}]$ to predict $y_{\text{MAE}, 24h}$:
   $$\hat{y}_{\text{MAE}, 24h} = \text{Ridge}(X_{\text{base}})$$
2. **Residual Downside Target**:
   $$e_{\text{MAE}} = y_{\text{MAE}, 24h} - \hat{y}_{\text{MAE}, 24h}$$
3. **Primary Test Metric**: Incremental Information Coefficient ($\Delta IC$), defined as the Spearman rank correlation between `vpin_true_24h_mean` and the baseline residual $e_{\text{MAE}}$:
   $$\Delta IC = \text{SpearmanCorr}(\text{vpin\_true\_24h\_mean}, e_{\text{MAE}})$$
*(Note: Raw $IC(\text{vpin\_true\_24h\_mean}, y_{\text{MAE}})$ will also be reported for descriptive transparency, but only $\Delta IC$ governs statistical admission).*

---

## 3. Dual-Window Evaluation Design

| Dimension | 1. Jump Evaluation Window | 2. Calm Control Window |
| :--- | :--- | :--- |
| **Dataset File** | `results/vpin_true_series.parquet` | `results/vpin_true_series_control.parquet` |
| **Date Range** | **2024-06-01 00:00 to 2024-08-15 23:59 UTC** | **2023-06-01 00:00 to 2023-08-15 23:59 UTC** |
| **Span / Duration** | 76 Calendar Days (1,824 Hourly Bars) | 76 Calendar Days (1,824 Hourly Bars) |
| **Market Regime** | Pre-cascade stress + **August 5, 2024 crash** | Summer 2023 low-vol range compression |
| **Peak 24h Downside** | **$-19.75\%$** (Violent liquidation shock) | **$-4.72\%$** (Benign low-vol drift) |
| **Volume Buckets** | 3,751 ground-truth trade buckets | 3,751 ground-truth trade buckets |
| **Raw Hourly Bars ($N$)**| 1,824 | 1,824 |
| **Baseline $N_{\text{eff}}$** | **$248.83$** (Newey-West Bartlett shrink) | **$267.87$** (Newey-West Bartlett shrink) |
| **Standard Error $SE(\Delta IC)$**| **$0.0637$** | **$0.0614$** |
| **MDE Admission Gate** | **$+0.1275$** ($2.0 \times SE$) | **$+0.1228$** ($2.0 \times SE$) |

---

## 4. Pre-Registered Decision Rules & Success Criteria

To establish an authentic, non-overfit empirical finding, **both** criteria must be met simultaneously on $\Delta IC$:

### Criterion 1: Jump Window Admission Gate (Incremental Toxicity Detection)
1. **Direction**: $\Delta IC_{\text{jump}} > 0$ (positive incremental correlation with residual downside risk).
2. **Significance**: $\Delta IC_{\text{jump}}$ must clear the conservative adaptive MDE threshold:
   $$\Delta IC_{\text{jump}} \ge +0.1275 \quad (2.0 \times SE(N_{\text{eff}}))$$
3. **P-Value & Confidence Bound**: $p < 0.05$ with lower 95% confidence interval strictly greater than zero.

### Criterion 2: Calm Control Window Gate (False-Positive Discrimination)
1. **Discrimination**: In the tranquil 2023 control window (where no extreme cascades occurred), VPIN must demonstrate a **substantially attenuated or null incremental effect**:
   $$\Delta IC_{\text{control}} < +0.1228 \quad (\text{Fail to clear admission gate})$$
2. **False-Positive Rejection Rule**: If `vpin_true` exhibits equal or stronger incremental correlation in the tranquil control regime as in the jump regime, it indicates generic non-specific noise rather than true jump-predictive toxic flow.

### Joint Outcome Decision Matrix:
* **CONFIRMED INCREMENTAL ALPHA**: $\Delta IC_{\text{jump}} \ge +0.1275$ **AND** $\Delta IC_{\text{control}} < +0.1228$.
* **REGIME-AGNOSTIC SPURIOUS NOISE (REJECT)**: $\Delta IC_{\text{jump}} \ge +0.1275$ **AND** $\Delta IC_{\text{control}} \ge +0.1228$.
* **HONEST EMPIRICAL NULL (REJECT)**: $\Delta IC_{\text{jump}} < +0.1275$.

---

## 5. Statistical Power Ceiling Disclosure

> **Methodological Note on Power & Detectable Effect Size**:  
> Due to the 76-day duration of the evaluation windows and the Newey-West effective degrees of freedom ($N_{\text{eff}} \approx 250$), the Minimum Detectable Effect ($MDE = 2.0 \times SE \approx 0.125$) represents a high bar. A null result ($\Delta IC < 0.1275$) conclusively rules out large, high-conviction order flow signals, but does not rule out sub-threshold micro-effects that require multi-year trade datasets to resolve.

---

## 6. Execution Integrity Lock

* **Status**: Pre-registration locked.
* **Modification Policy**: Zero parameter tuning, lookback searches, or date shifting permitted after test execution.
