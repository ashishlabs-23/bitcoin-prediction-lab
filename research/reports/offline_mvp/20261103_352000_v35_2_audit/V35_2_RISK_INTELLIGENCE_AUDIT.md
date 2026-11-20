# BTCognitive V35.2 — Forensic Risk Intelligence & C2 Conformal Calibration Audit
**Document ID:** `V35_2_RISK_INTELLIGENCE_AUDIT.md`  
**Milestone:** V35.2 Comprehensive Research Audit  
**Author:** AGENT 5 (Risk Intelligence & C2 Conformal Research Specialist)  
**Operating Posture:** Strictly `OFFLINE_RESEARCH_ONLY` | Live Trading `DISABLED`  
**Governing Status:** Verified Read-Only Forensic Empirical Audit  

---

## Executive Summary & Core Verdict

Pursuant to the Milestone V35.2 directive, Agent 5 has executed an exhaustive, read-only forensic audit across all risk-related features, excursion models, and uncertainty quantification engines in BTCognitive.

### Key Audit Verdicts:
1. **Governed C2 Status:** `C2_CALIBRATION_UNAVAILABLE` / `C2_CALIBRATION_FAILED`.
2. **Empirical Coverage Reality:** Against a nominal 90.0% target ($\alpha = 0.10$), strictly causal point-in-time C2 coverage is **84.89%** on the full 5,671-hour holdout (a 5.11 percentage point deficit) and collapses to **78.02%** on the 1,943-hour multi-regime holdout. In the top decile of volatility (extreme regime), coverage crashes to **64.79%**.
3. **The 168-Hour Delayed Feedback Barrier:** Online adaptive conformal methods (ACI, FACI, EnbPI) **fail** under the 7-day (168-hour) causal maturity latency. When volatility explodes, non-conformity errors cannot be observed until 168 hours later. As a result, ACI coverage drops to **80.44%**, FACI drops to **76.18%**, and EnbPI achieves **84.36%**—none resolving undercoverage during regime shocks.
4. **Codebase Vulnerabilities Identified & Quarantined:**
   - **Fabricated Excursion Multipliers:** In `research/risk_envelope.py` (lines 27–28), downside excursion (MAE) is artificially synthesized by multiplying upside excursion (MFE) by fixed constants (`p50_mfe * 1.32` and `p90_mfe * 1.90`).
   - **Fabricated Validation Claims:** In `research/risk_envelope.py` (line 46), the table hardcodes `"HIGH (Conformal 91.3% Validated)"` and `"90% of observed prices stay within this projected envelope"`, directly contradicting empirical failure.
   - **Observatory Initialization Fallacy:** In `engine/observatory.py` (lines 683, 694–696), when zero forecasts have matured, the system claims `CalibrationHealthStatus.STABLE` and fabricates `coverage_30d_pct = 100.0%` by default.
   - **Permissive Engine Defaults:** In `routes_arena.py`, `strategy_selection.py`, `smart_entry_engine.py`, and `counterfactual_contract_engine.py`, function arguments default to `c2_health = "CALIBRATED"`, leading `routes_arena.py` to evaluate `"risk_check": "AUTHORIZED"`.
   - **In-Sample Calibration in Excursions:** In `research/purged_excursion_validation.py` (lines 136–140), conformity quantiles are calculated on in-sample training residuals, and joint coverage across 5 folds averages only **80.29%** with a **negative Spearman rank correlation** ($\text{IC} = -0.2378$ to $+0.0192$).

---

## 1. Deep-Dive Inspection: C2 Conformal Calibration Framework

### 1.1 Mathematical Formulation of Baseline C2
- **Target Variable:** 7-day forward annualized realized variance:
  $$y_t = \text{rv7d\_var\_ann}_t$$
- **Base Estimator:** HAR-RS-DOW-v1.0 (heterogeneous autoregressive model with realized semi-variances and day-of-week seasonality):
  $$\hat{v}_t = \exp\left(\mathbf{x}_t^\top \hat{\boldsymbol{\beta}}\right)$$
- **Standardized Non-Conformity Scores:**
  $$s_{t, \text{upper}} = \max\left(0, \; \frac{y_t - \hat{v}_t}{\hat{\sigma}_t}\right), \qquad s_{t, \text{lower}} = \max\left(0, \; \frac{\hat{v}_t - y_t}{\hat{\sigma}_t}\right)$$
  where $\hat{\sigma}_t$ is an exponentially weighted moving (EWM) standard deviation (span = 720h, min_periods = 72h).
- **Conformity Quantile Calculation:**
  Scores are drawn from trailing history using 24h thinning (stride = 24) over the trailing 1,000 bars. With calibration set size $M$, rank index:
  $$k_{\text{conf}} = \left\lceil (M + 1)\left(1 - \frac{\alpha}{2}\right) \right\rceil$$
- **Interval Bounds:**
  $$L_t = \max\left(10^{-6}, \; \hat{v}_t - q_{\text{lower}} \cdot \hat{\sigma}_t\right), \qquad U_t = \hat{v}_t + q_{\text{upper}} \cdot \hat{\sigma}_t$$

### 1.2 The Forensic Defect: Lookahead Leakage vs. Causal Delayed Evaluation
- **Legacy Defect (Audited in Stage 12):**
  In earlier implementations (`research/stage12_causal_conformal_engine.py`), the full holdout residual series was concatenated with training residuals before computing the rolling EWM standard deviation. At step $t_{\text{glob}}$, $\hat{\sigma}_{t_{\text{glob}}}$ used contemporaneous residuals, leaking future realized variance. This inflated apparent coverage to **92.36%**.
- **Strictly Causal Real-Time Enforcement:**
  Because the target outcome spans $[t, t + 168\text{h}]$, the realization $y_t$ cannot be known until step $t + 168$. Thus, at issuance time $t$, the calibration pool and EWM scale factor $\hat{\sigma}_t$ must be restricted strictly to origins $t' \le t - 168\text{h}$.
- **Result:** Under strictly causal evaluation, empirical coverage drops to **84.89%** ($4,814 / 5,671$), exposing the structural adaptation lag during volatility bursts.

---

## 2. Historical Excursion Measures (MFE & MAE) & Tail Risk Audit

### 2.1 Formal Target Definitions
- **Maximum Favorable Excursion (MFE):**
  $$\text{MFE}_t = \frac{\max_{k \in [1, 24]} \text{High}_{t+k} - \text{Close}_t}{\text{Close}_t}$$
- **Maximum Adverse Excursion (MAE):**
  $$\text{MAE}_t = \frac{\text{Close}_t - \min_{k \in [1, 24]} \text{Low}_{t+k}}{\text{Close}_t}$$

### 2.2 Forensic Audit Findings in Excursion Codebase
1. **Synthetic Fabrication in `research/risk_envelope.py`:**
   ```python
   # Lines 27-28 in risk_envelope.py
   mae_p50 = float(np.mean(df_mfe_forecasts["p50_mfe"] * 1.32)) * 100.0
   mae_p90 = float(np.mean(df_mfe_forecasts["p90_mfe"] * 1.90)) * 100.0
   ```
   **Finding:** Downside excursion risk (MAE) is not predicted by a trained model in `risk_envelope.py`; it is fabricated by multiplying upside MFE by `1.32` and `1.90`.
2. **Hardcoded Unverified Claims in `risk_envelope.py`:**
   ```python
   # Line 46 in risk_envelope.py
   "State / Value": "HIGH (Conformal 91.3% Validated)",
   "Interpretation": "90% of observed prices stay within this projected envelope."
   ```
   **Finding:** This table entry hardcodes a validation claim ("91.3% Validated") that has never been confirmed under purged out-of-sample testing.
3. **Flawed Calibration in `research/purged_excursion_validation.py`:**
   ```python
   # Lines 137-140 in purged_excursion_validation.py
   mfe_residuals = np.abs(y_mfe_train - pipe_mfe.predict(X_train))
   mae_residuals = np.abs(y_mae_train - pipe_mae.predict(X_train))
   q90_mfe = np.quantile(mfe_residuals, 0.90)
   q90_mae = np.quantile(mae_residuals, 0.90)
   ```
   **Finding:** Conformity quantiles are estimated on in-sample training residuals rather than a holdout calibration set, violating conformal exchangeability and sample-splitting principles.
4. **Unadjusted Joint Coverage:**
   The code computes joint containment `np.mean(mfe_contained & mae_contained)` and labels it `p90_joint_coverage`. Without a Bonferroni correction ($\alpha/2 = 0.05$ per boundary) or copula modeling, joint coverage across 5 purged folds drops to **80.29%** (Fold 1: 79.10%, Fold 2: 89.75%, Fold 3: 80.94%, Fold 4: 71.93%, Fold 5: 79.71%).
5. **Predictive Failure of MFE Models:**
   Out-of-sample Spearman IC for MFE is negative in 4 out of 5 folds (Fold 1: -0.2378, Fold 2: -0.0549, Fold 3: -0.2079, Fold 4: -0.0409, Fold 5: +0.0192). The regression models fail to provide directional predictive rank power.

---

## 3. Methodological Comparison: Research-Only Alternatives & The Delayed-Label Barrier

To assess whether alternative conformal architectures resolve the undercoverage gap, we benchmarked the 5 architectures evaluated in `research/c2_adaptive_calibration.py` on the 5,671-hour holdout:

| Architecture | Evaluation Protocol | Marginal Coverage (%) | Extreme Regime Coverage (%) | Mean Winkler Score | Mean Interval Width | Epistemic Assessment |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Baseline C2 (Control)** | Split-conformal + 168h delay | **84.89%** | **64.79%** | 1.0444 | 0.4389 | Retains baseline stability; undercovers by 5.11 pp |
| **Candidate 1 (Rolling W=720h)** | Sliding window of matured residuals | **83.23%** | **61.80%** | 1.0092 | 0.3864 | Degrades coverage; overreacts to recent tranquil windows |
| **Candidate 2 (ACI $\gamma=0.002$)** | Gibbs & Candès (2021) online ACI | **80.44%** | **63.91%** | 1.0486 | 0.4234 | **Severe degradation**; 168h feedback latency causes destabilization |
| **Candidate 3 (FACI Multi-Expert)** | Gibbs & Candès (2024) hedge aggregation | **76.18%** | **54.58%** | 1.0326 | 0.3790 | **Catastrophic failure** in extreme regime (-35.42 pp) |
| **Candidate 4 (EnbPI W=1440h)** | Xu & Xie (2021) residual quantiles | **84.36%** | **59.68%** | 0.8740 | 0.3606 | Sharpest interval width, but fails to reach 90% |

### Theoretical Grounding: Zhai, Cheng and Wu (2026, arXiv:2609.33868)
The paper *"Conformal Coverage of Time Series: Validity and Inference"* (Percy S. Zhai, Maggie Cheng, Wei Biao Wu) directly formalizes the mathematical reason why these alternatives fail:
1. **Functional Dependence Measure (FDM) vs. Mixing:** Time series with heavy tails and volatility clustering do not satisfy traditional mixing assumptions. Under Wu's FDM, split-conformal coverage variance is dominated by the long-run variance of the binary coverage indicator process:
   $$\sigma_{\infty}^2 = \sum_{k=-\infty}^\infty \text{Cov}(e_t, e_{t+k}) = \text{Var}(e_t) \left(1 + 2 \sum_{k=1}^\infty \rho_k\right)$$
2. **Bahadur Representation & Asymptotic Variance:** Zhai et al. establish a Bahadur representation for realized conformal coverage. Because coverage breaches cluster during multi-day volatility surges, the asymptotic variance of $\hat{C}_n$ is expanded by a factor of $(1 + 2\sum \rho_k)$.
3. **Long-Memory Limiting Laws:** When volatility exhibits long memory (fractional integration), the limiting distribution of empirical coverage is non-Gaussian.
4. **The Delayed-Feedback Impossibility:** Online adaptive schemes (ACI/FACI) rely on martingale property assumptions:
   $$\mathbb{E}[\text{err}_t \mid \mathcal{F}_{t-1}] = \alpha_t$$
   Under $h$-step ahead forecasting with $h = 168$, the filtration available at time $t$ is $\mathcal{F}_{t-h}$. The sequence of errors $\text{err}_t$ contains 168 unobserved steps. When an extreme shock hits at time $t_0$, the adaptive threshold cannot widen until $t_0 + 168$. All intervals issued between $t_0$ and $t_0 + 168$ breach simultaneously.

---

## 4. Rigorous Statistical Evaluation

### 4.1 Marginal Coverage Across Evaluation Windows
- **Full 2026 Chronological Holdout (5,671 hours / 236.3 days):**
  - Observed Coverage: **84.89%** ($4,814 / 5,671$)
  - Undercoverage Gap: **-5.11 percentage points**
- **1,943-Hour Multi-Regime Holdout (V34.1 / V34.4 Verified):**
  - Observed Coverage: **78.02%** ($1,516 / 1,943$)
  - Undercoverage Gap: **-11.98 percentage points**
- **590-Hour Calm Sub-Slice (V34.2 Forensic Audit):**
  - Observed Coverage: **93.90%** (Artifact of post-hoc selection over tranquil regime)

### 4.2 Finite-Sample Coverage Confidence Intervals
Evaluating coverage uncertainty under different statistical assumptions:

| Confidence Interval Method | 5,671-Hour Holdout (Observed 84.89%) | 1,943-Hour Holdout (Observed 78.02%) | Epistemic Validity Under Time Series |
| :--- | :---: | :---: | :--- |
| **Clopper-Pearson (Exact Binomial)** | $[83.93\%, \; 85.81\%]$ | $[76.12\%, \; 79.84\%]$ | **INVALID:** Assumes i.i.d. Bernoulli trials; grossly understates variance |
| **Wilson Score Interval** | $[83.94\%, \; 85.81\%]$ | $[76.14\%, \; 79.82\%]$ | **INVALID:** Assumes i.i.d. Bernoulli trials; fails under autocorrelation |
| **Stationary Block Bootstrap ($L=84\text{h}$)** | $[76.99\%, \; 91.36\%]$ | $[60.12\%, \; 94.21\%]$ | Partially captures weekly persistence |
| **Stationary Block Bootstrap ($L=168\text{h}$, Primary)** | **$[74.63\%, \; 93.09\%]$** | **$[55.84\%, \; 96.45\%]$** | **AUTHORITATIVE:** Matches full 7-day forecast horizon overlap |
| **Stationary Block Bootstrap ($L=336\text{h}$)** | $[74.34\%, \; 94.37\%]$ | $[54.10\%, \; 97.20\%]$ | Captures multi-week persistence and regime shifts |

### 4.3 Effective Sample Size ($N_{\text{eff}}$) Under Serial Autocorrelation
The empirical autocorrelation of coverage breaches $e_t = \mathbb{I}\{y_t \notin [L_t, U_t]\}$:
- Lag 1h: $\rho_1 = \mathbf{0.8817}$
- Lag 2h: $\rho_2 = \mathbf{0.7633}$
- Lag 6h: $\rho_6 = \mathbf{0.4968}$
- Lag 12h: $\rho_{12} = \mathbf{0.2594}$
- Lag 24h: $\rho_{24} = -0.0031$
- Lag 72h: $\rho_{72} = \mathbf{0.2218}$ (cluster rebound)
- Lag 168h: $\rho_{168} = -0.0211$ (full horizon decay)

Applying the spectral variance formula $N_{\text{eff}} = \frac{N}{1 + 2 \sum_{k=1}^K \rho_k}$:
- On the 1,943-hour window: **$N_{\text{eff}} = 17.2$** independent observations!
- On the 5,671-hour window: **$N_{\text{eff}} = 33.75$** non-overlapping weekly blocks!
- **Statistical Implication:** Treating 5,671 hourly observations as independent inflates apparent sample size by **168x**. With $N_{\text{eff}} \approx 34$, the 95% confidence interval spans nearly 19 percentage points ($[74.6\%, 93.1\%]$).

### 4.4 Regime-Conditional Coverage Breakdown (5,671 Holdout Bars)
- **LOW Regime** ($y < 0.1020$, $N=1,418$): **83.00%** (lower bound boundary collisions)
- **MEDIUM Regime** ($0.1020 \le y < 0.2420$, $N=2,835$): **89.81%** (near nominal 90%)
- **HIGH Regime** ($0.2420 \le y < 0.3886$, $N=850$): **85.06%**
- **EXTREME Regime** ($y \ge 0.3886$, $N=568$): **64.79%** (severe breakdown, 200 breaches)
- **Violation Clustering:** 37 distinct undercoverage episodes, with a mean duration of **23.16 consecutive hours** and a maximum breach duration of **251 consecutive hours** (10.5 days).

---

## 5. Governance Guardrail Enforcement & Code Remediation Action Plan

### 5.1 Enforced Governance Status
Pursuant to Phase 5 and Phase 7 Operating Protocols:
1. **Model Governance Verdict:** `C2_CALIBRATION_UNAVAILABLE` / `OFFLINE_RESEARCH_ONLY`.
2. **Production Gate Status:** `GATED` / `LIVE_TRADING_DISABLED`.
3. **External Transfer Ban:** Absolutely no uncalibrated cross-exchange transfer (e.g. applying Deribit option implied volatilities or Binance perpetual metrics to spot without pre-registered calibration).
4. **Envelope Display Rule:** UI and API routes must never display C2 risk envelopes as validated 90% prediction guarantees.

### 5.2 Specific Code Remediation Items Identified for Main Orchestrator

| File | Line(s) | Current Problematic Code | Mandated Remediation |
| :--- | :--- | :--- | :--- |
| `BTCognitive/research/risk_envelope.py` | 27–28 | `mae_p50 = float(np.mean(df_mfe_forecasts["p50_mfe"] * 1.32)) * 100.0` | **DELETE:** Remove synthetic scalar multiplication; mark MAE as unmodeled or calibrate via empirical quantiles. |
| `BTCognitive/research/risk_envelope.py` | 46 | `"HIGH (Conformal 91.3% Validated)"` | **REPLACE:** Change to `"UNAVAILABLE (C2 Conformal Undercoverage 84.89% - Research Only)"`. |
| `BTCognitive/api/routes_arena.py` | 1164 | `"c2_health": "CALIBRATED"` | **REPLACE:** Change fallback to `"c2_health": "C2_CALIBRATION_UNAVAILABLE"`. |
| `BTCognitive/api/routes_arena.py` | 1400 | `"risk_check": "AUTHORIZED" if c2_health == "CALIBRATED" else "GATED"` | **VERIFY:** Ensure `c2_health` is never defaulted to `"CALIBRATED"`. |
| `BTCognitive/engine/observatory.py` | 683, 694–696 | `status = CalibrationHealthStatus.STABLE; coverage = 100.0` | **REPLACE:** Change initialization when `valid_resolved == 0` to `CalibrationHealthStatus.UNINITIALIZED` and `coverage = None`. |
| `BTCognitive/engine/strategy_selection.py` | 97, 421, 485 | `c2_health: str = "CALIBRATED"` (default argument) | **REPLACE:** Change default argument to `c2_health: str = "C2_CALIBRATION_UNAVAILABLE"`. |
| `BTCognitive/engine/smart_entry_engine.py` | 255 | `c2_health: str = "CALIBRATED"` (default argument) | **REPLACE:** Change default argument to `c2_health: str = "C2_CALIBRATION_UNAVAILABLE"`. |
| `BTCognitive/engine/counterfactual_contract_engine.py` | 105, 118 | `snap.get("calibration_health", "CALIBRATED")` | **REPLACE:** Change fallback default to `"C2_CALIBRATION_UNAVAILABLE"`. |
| `BTCognitive/research/purged_excursion_validation.py` | 136–140 | In-sample residuals for conformity quantiles | **REPLACE:** Use split-conformal out-of-fold residuals with Bonferroni correction for joint envelope. |

---

## 6. Conclusion & Recommendation to Lead Orchestrator

1. **Epistemic Integrity Upheld:** The apparent "90% Conformal Validation" claimed in early drafts was an artifact of lookahead leakage (92.36%), post-hoc sub-slice selection (93.90%), or synthetic multipliers (`1.32x`, `1.90x`). Under strict causal, point-in-time delayed evaluation, empirical coverage is **84.89%** overall and **64.79%** in extreme market conditions.
2. **Mathematical Irreducibility of Delayed Feedback:** No online adaptive algorithm (ACI, FACI, EnbPI) can overcome the 168-hour feedback barrier without exogenous leading indicators.
3. **Final Recommendation:** Lock C2 in `C2_CALIBRATION_UNAVAILABLE` across all API endpoints and engine contracts. Maintain the research boundary strictly at `OFFLINE_RESEARCH_ONLY`.

