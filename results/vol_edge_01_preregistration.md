# Pre-Registration: Incremental Volatility Information Trial (VOL-EDGE-01)
**Document Status**: LOCKED & IMMUTABLE PRIOR TO DATA INGESTION & INFERENCE  
**Target File**: `results/vol_edge_01_preregistration.md`  
**Execution Timestamp**: 2026-08-24T20:15:00Z  
**Research Protocol**: Multi-Regime Purged Walk-Forward Incremental Variance Evaluation  
**Decisive Test**: Challenger M6 (HAR + IV² + Compression) vs Benchmark M5 (HAR + IV²)  

---

## 1. Research Question & Rationale

> **Core Scientific Question**:  
> Does the **conformal excursion compression signal** ($\text{CompressionPercentile}_{168h}(W_t) \le 0.10$) contain **statistically significant incremental out-of-sample information** for forward 7-day realized variance (`rv7d_var_ann`) beyond what is already captured by a state-of-the-art **HAR-RV volatility baseline AND contemporaneous 7-day option-implied variance (`iv7d_var_ann`)**?

### Epistemic Trajectory:
* **Stage 1 (Directional Classification)**: ❌ **REJECTED** ($\text{AUC} \approx 0.5041$).
* **Stage 2 (Macro Features)**: ❌ **REJECTED** ($\Delta\text{IC} \le 0$).
* **Stage 3 (Microstructure Toxicity / VPIN)**: ❌ **REJECTED** ($\Delta\text{IC} < +0.1275$).
* **Stage 4 (Conformal Risk Envelopes)**: ✅ **VALIDATED CALIBRATION** (90.2% P90 empirical containment).
* **Stage 5 (Compression Trigger / STRAT-VOLCOMP-01)**: ⚠️ **FROZEN**. Proved compression precedes elevated realized movement ($\bar{r} = +1.03\%$), but economic tradability was unvalidated due to the synthetic "free option" artifact.
* **Stage 6 (VOL-EDGE-01)**: 🎯 **CURRENT MILESTONE**. Strict out-of-sample incremental information evaluation across a multi-regime dataset.

---

## 2. Target Variable & Mathematical Specifications

### A. Primary Target Variable: Annualized 7-Day Realized Variance (`rv7d_var_ann`)
* **Sampling Frequency**: Hourly log return $r_\tau = \ln(P_\tau / P_{\tau-1})$ from authenticated continuous 24/7 BTC spot OHLCV (UTC timestamps).
* **Aggregation Horizon**: $h = 168\text{ hours}$ (7 calendar days).
* **Annualization Factor**: $\frac{8760}{168} = 52.142857$ (where $8760 = 24 \times 365$).
* **Mathematical Notation**:
  $$\text{rv7d\_ann}_t = \sqrt{\frac{8760}{168} \sum_{i=1}^{168} r_{t+i}^2}$$
  $$\text{rv7d\_var\_ann}_t = \left(\text{rv7d\_ann}_t\right)^2 = \frac{8760}{168} \sum_{i=1}^{168} r_{t+i}^2$$
* **Realized-Implied Variance Spread**:
  $$\Delta \text{Var}_{\text{RV-IV}, t} = \text{rv7d\_var\_ann}_t - \text{iv7d\_var\_ann}_t$$
  *(Note: Defined strictly as an ex-post variance spread; economic risk-premium claims reserved for post-screening).*

### B. Explanatory & Baseline Regressors
1. **HAR-RV Component Regressors** (Corsi, 2009):
   * $\text{rv1d\_var\_ann}_t = \frac{8760}{24} \sum_{i=0}^{23} r_{t-i}^2$ (Daily trailing realized variance)
   * $\text{rv7d\_var\_ann\_lag}_t = \frac{8760}{168} \sum_{i=0}^{167} r_{t-i}^2$ (Weekly trailing realized variance)
   * $\text{rv30d\_var\_ann}_t = \frac{8760}{720} \sum_{i=0}^{719} r_{t-i}^2$ (Monthly trailing realized variance)
2. **Point-in-Time 7-Day Implied Variance**:
   * $\text{iv7d\_var\_ann}_t = \left(IV_{7d, t}^{\text{ATM}}\right)^2$: Annualized ATM 7-day implied variance reconstructed strictly point-in-time from Deribit historical mark/index snapshots ($\text{snapshot\_ts} \le t$).
3. **Conformal Compression Regressor**:
   * $\text{Compression}_{168h}(t) = \mathbb{I}\left(\text{CompressionPercentile}_{168h}(W_t) \le 0.10\right)$ (Binary compression indicator)
   * $W_t = \hat{y}_{\text{MFE}, 24h}^{\text{P90}}(t) + \hat{y}_{\text{MAE}, 24h}^{\text{P90}}(t)$ (Continuous envelope width)

---

## 3. Deribit Option-Implied Volatility Specifications & Zero-Imputation Data Gate

### A. Point-in-Time IV Reconstruction Protocol
* **Instrument Source**: Deribit BTC options mark prices & volatility index records.
* **Expiry Target**: $T = 7.000\text{ days}$ ($168.0\text{ hours}$).
* **Expiry Tolerance**: $T \in [6.0\text{ days}, 8.0\text{ days}]$. Linear interpolation in total variance space ($w = \sigma^2 \tau$) between the two closest expiries straddling $7.0\text{ days}$ to produce a constant 7.0-day maturity.
* **Maturity Error Tracking**: Log $\epsilon_{\text{TTM}}(t) = |T_{\text{actual}}(t) - 7.0\text{d}|$ for every bar.
* **ATM Strike Selection**: Delta $\Delta \in [-0.55, -0.45]$ for puts, $[0.45, 0.55]$ for calls, or nearest forward strike $|K - F_t| / F_t \le 0.025$.
* **Timestamp Invariant**: Strict point-in-time rule: $\text{snapshot\_timestamp} \le t$ (minimum 5-minute availability buffer; zero forward lookahead).
* **Scope Boundary Disclosure**: This experiment evaluates standardized ATM implied volatility as an aggregate market volatility expectation. Full volatility skew, smile curvature, and risk reversals are explicitly defined as out of scope for VOL-EDGE-01.

### B. Pre-Flight Zero-Imputation IV Data Gate
Before model estimation, the ingested IV series must satisfy:

| Quality Dimension | Rejection Threshold | Requirement |
| :--- | :--- | :--- |
| **7-Day IV Date Coverage** | $< 90.0\%$ | $\ge 90.0\%$ valid hourly observations across multi-regime span |
| **Stale Quotes ($\Delta t > 2\text{h}$)** | $> 2.0\%$ | $\le 2.0\%$ repeated quote prints |
| **Invalid / Non-Positive IV** | $> 0$ instances | Strictly $0$ ($IV > 0$ and finite for all $t$) |
| **Future Lookahead Violations** | $> 0$ instances | Strictly $0$ ($\text{snapshot\_timestamp} \le t$) |
| **Duplicate Snapshots** | $> 0$ instances | Strictly $0$ unique hourly timestamps |
| **Imputation Policy** | $> 0$ synthetic rows | **ZERO IMPUTATION**: Gaps are never forward-filled or synthesized. |

---

## 4. Baseline Model Ladder & Structural Positivity

### A. Structural Forecast Positivity & Estimation Procedure
Models are estimated via log-variance linear regression:
$$\ln(\hat{v}_t) = \mathbf{X}_t^\top \boldsymbol{\beta} \implies \hat{v}_t = \exp\left(\mathbf{X}_t^\top \hat{\boldsymbol{\beta}}\right) > 0$$
This guarantees strictly positive variance forecasts $\hat{v}_t > 0$ without post-hoc artificial clipping, ensuring mathematical validity under QLIKE loss.

### B. Model Hierarchy (M0 -> M6 + Robustness)

| Model ID | Specification | Hypothesis Role |
| :--- | :--- | :--- |
| **M0** | $\ln(\hat{v}_t) = \mu_{\text{train}}$ | Naive Historical Mean Baseline |
| **M1** | $\ln(\hat{v}_t) = \alpha + \beta \ln(\text{rv7d\_var\_ann\_lag}_t)$ | Autoregressive Persistence Baseline |
| **M2** | $\ln(\hat{v}_t) = \alpha + \beta_d \ln(\text{rv1d}) + \beta_w \ln(\text{rv7d}) + \beta_m \ln(\text{rv30d})$ | Standard HAR-RV Volatility Baseline |
| **M2-R** | $\ln(\hat{v}_t) = \text{HAR-RS-DOW}(\text{Semivariance, Day-of-Week})$ | **Benchmark Robustness Check** (Contemporary BTC HAR) |
| **M3** | $\ln(\hat{v}_t) = \text{HAR}_t + \gamma \text{Compression}_t$ | Compression without Options Context |
| **M4** | $\ln(\hat{v}_t) = \alpha + \beta \ln(\text{iv7d\_var\_ann}_t)$ | Market-Implied Expectations Baseline |
| **M5** | $\ln(\hat{v}_t) = \text{HAR}_t + \beta \ln(\text{iv7d\_var\_ann}_t)$ | **Strong Combined Benchmark (HAR + IV²)** |
| **M6** | $\ln(\hat{v}_t) = \text{HAR}_t + \beta \ln(\text{iv7d\_var\_ann}_t) + \gamma \text{Compression}_t$ | **BTCognitive Challenger Model** |

---

## 5. Primary Decision Gate: Decisive Test ($M_6 \text{ vs. } M_5$)

For `VOL-EDGE-01` to establish a genuine scientific discovery, **$M_6$ must strictly outperform $M_5$ out-of-sample** across all criteria:

### Criterion 1: Out-of-Sample QLIKE Improvement (Paired Diebold-Mariano)
$$\text{QLIKE}(y_t, \hat{v}_t) = \frac{y_t}{\hat{v}_t} - \ln\left(\frac{y_t}{\hat{v}_t}\right) - 1$$
* **Paired Loss Differential**:
  $$d_t = \text{QLIKE}(y_t, \hat{v}_{M5, t}) - \text{QLIKE}(y_t, \hat{v}_{M6, t})$$
* **Diebold-Mariano Test**: Test $H_0: E[d_t] \le 0$ vs $H_1: E[d_t] > 0$ with fixed ex-ante Newey-West bandwidth $L = 168$ (reflecting the 168-hour forecast horizon overlap).
* **Admission Gate**: $\bar{d} > 0$ with $\text{DM } p\text{-value} < 0.05$.

### Criterion 2: Incremental Out-of-Sample Information ($\Delta R^2_{\text{OOS}} > 0$ and $\Delta \text{IC} > 0$)
* $\Delta R^2_{\text{OOS}} = R^2_{M6} - R^2_{M5} > 0$
* $\Delta \text{IC} = \text{SpearmanCorr}(\hat{v}_{M6} - \hat{v}_{M5}, e_{M5}) > 2.0 \times SE(N_{\text{eff, DM}}) \quad (p < 0.05)$

### Criterion 3: Dual Placebo Permutation Distribution ($B = 1,000$)
* **Placebo A (IID Permutation)**: Shuffled compression timestamps to verify pipeline alignment.
* **Placebo B (Block Permutation — Primary)**: Block-shuffled compression series preserving temporal autocorrelation clusters.
* **Requirement**: The empirical block placebo distribution $\{\Delta \text{QLIKE}_{\text{block}}^{(b)}\}_{b=1}^{1000}$ must center at zero ($\bar{\Delta} \approx 0$), with $\Delta \text{QLIKE}_{\text{actual}}$ falling in the extreme upper 95th percentile ($p_{\text{perm}} < 0.05$).

### Criterion 4: Robustness Benchmark Clearance ($M_6 \text{ vs. } M_{2\text{-R}}$)
* $M_6$ must maintain positive incremental out-of-sample performance over the contemporary HAR-RS-DOW benchmark.

### Criterion 5: Economic Opportunity Screen (Prerequisite for Future Derivatives Research)
* Conditional on $\text{Compression}_t = 1$:
  $$E[\text{rv7d\_var\_ann}_t \mid \text{Compression}_t = 1] - \text{iv7d\_var\_ann}_t > \text{Friction Floor} \quad (50\text{ bps variance equivalent})$$
  *(Explicit Invariant: Passing Criterion 5 is an economic variance spread screen, not executable option P&L).*

---

## 6. Autocorrelation Invariant & Dual $N_{\text{eff}}$ Metrics

Due to the 168-hour forecast overlap:
1. **$N_{\text{eff, target}}$**: Autocorrelation-adjusted sample size of the target `rv7d_var_ann`.
2. **$N_{\text{eff, DM}}$**: Autocorrelation-adjusted sample size of the paired loss differential series $d_t = L_{M5, t} - L_{M6, t}$ with ex-ante bandwidth $L = 168$.
* Both values will be computed directly on the evaluation residual structure and frozen in the experiment manifest before reporting.

---

## 7. Standard 10-Step Implementation Sequence

```
Step 0: Freeze data specifications (h=168h, ATM delta, log-link, QLIKE, L=168) [LOCKED]
  │
Step 1: Ingest point-in-time Deribit IV_7d ATM series & compute maturity error |T - 7d|
  │
Step 2: Execute Pre-Flight Zero-Imputation IV Data Gate (Coverage, Staleness, Lookahead)
  │
Step 3: Reconstruct rv7d_var_ann target independently from authenticated OHLCV
  │
Step 4: Compute 168h residual autocorrelation & lock N_eff,target and N_eff,DM
  │
Step 5: Run Purged Walk-Forward Cross-Validation across M0–M6
  │
Step 6: Execute B=1,000 Block Permutation Distribution Test (Placebo B)
  │
Step 7: Run Robustness Benchmark (M6 vs. M2-R HAR-RS-DOW)
  │
Step 8: Measure Compression vs. IV Market Pricing Correlation (Corr(Compression, IV))
  │
Step 9: Output Full Comparison Table & Per-Fold Compression Coefficient Stability Panel
  │
Step 10: If Criteria 1–4 Clear -> Execute Economic Opportunity Screen (H3)
```
