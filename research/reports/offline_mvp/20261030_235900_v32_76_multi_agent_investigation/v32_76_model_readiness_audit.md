# V32.76 — Machine Learning Targets, Features & Model Readiness Audit Report

**Workstream:** Agent 5 — ML Research Specialist  
**Milestone:** BTCognitive V32.76 — Multi-Agent Research Integrity & Conditional Entry Investigation  
**Date:** 2026-10-30  
**Evaluator:** ML Research Specialist (Agent 5)  
**Governing Repo:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Classification:** ML Model Governance Authority Record  

---

## 1. Executive Summary & Model Readiness Verdict

| Audit Dimension | Evaluation Result | Governing Decision |
|---|---|---|
| **Model Authorization** | **`OFFLINE_RESEARCH_ONLY`** | **ZERO MODELS TRAINED, TUNED, OR PROMOTED**. |
| **Proposed Targets** | Audited 4 targets (MFE/MAE ratio, Multi-class barrier, Binary sign, Time-to-touch). | Target B has severe class imbalance (60% SL vs 29% TP). Requires balanced loss functions if trained. |
| **Proposed Features** | Audited 8 features for causality and lookahead. | Strictly causal. Zero future leakage. All features satisfy $t_{\text{feature}} \le t_{\text{signal}}$. |
| **ML Justification** | **NOT CURRENTLY JUSTIFIED** | Complex non-linear models (GBM, Deep Learning) have not demonstrated predictive edge over a constant prevalence baseline. |

---

## 2. Audit of the Four Proposed Machine Learning Targets

### Target A: Continuous 24h MFE / MAE Ratio (Path Excursion)
- **Mathematical Definition:**
  $$y_A = \ln\left( \frac{\text{MFE}_{24h}}{\text{MAE}_{24h} + \epsilon} \right)$$
- **Pros:** Continuous, differentiable target capturing path asymmetry.
- **Vulnerabilities:** Heavy-tailed distribution with severe outliers when $\text{MAE} \to 0$. Requires log-clipping.

### Target B: Multi-Class Triple-Barrier Outcome
- **Definition:**
  $$y_B \in \{-1 \text{ (Stop-Loss First)}, 0 \text{ (Time Expiry)}, +1 \text{ (Take-Profit First)}\}$$
- **Class Imbalance Audit:**
  - Class -1 (SL): $\approx 60.2\%$
  - Class +1 (TP): $\approx 29.1\%$
  - Class 0 (Expiry): $\approx 10.7\%$
- **Risk:** Standard unweighted cross-entropy will simply predict the majority class (SL), yielding a high apparent accuracy (~60%) with zero trading utility. Requires class weights: $w_{-1} \approx 0.55$, $w_{+1} \approx 1.15$, $w_0 \approx 3.10$.

### Target C: Binary 24h Directional Return
- **Definition:** $y_C = \mathbb{I}(r_{24h} > 0)$.
- **Audit:** As established in V32.71, directional accuracy on unconditional BTC returns is $\approx 53.28\%$ with an AUC of $0.5445$. Directional return prediction does not solve excursion timing.

### Target D: Continuous Time-to-Barrier Horizon
- **Definition:** $y_D = \min(t_{\text{TP}}, t_{\text{SL}}, 24.0)$.
- **Audit:** Extremely noisy and regime-dependent. Unsuitable as a primary optimization objective.

---

## 3. Causal Feature Audit (8 Point-in-Time Features)

| Feature Name | Lookback Window | Calculation Formula | Causal Verification | Lookahead Risk |
|---|---|---|---|---|
| `rv_24h` | 24 closed bars | $\sum_{i=0}^{23} r_{t-i}^2 \times 8760$ | Satisfies $t_{\text{feat}} \le t_{\text{sig}}$ | **ZERO** (Strictly past candles) |
| `trend_ratio` | 200 closed bars | $\text{EMA}_{50}(C) / \text{EMA}_{200}(C)$ | Satisfies $t_{\text{feat}} \le t_{\text{sig}}$ | **ZERO** |
| `rsi_14` | 14 closed bars | Wilder's 14-period RSI | Satisfies $t_{\text{feat}} \le t_{\text{sig}}$ | **ZERO** |
| `natr_14` | 14 closed bars | $\text{ATR}_{14} / \text{Close} \times 100$ | Satisfies $t_{\text{feat}} \le t_{\text{sig}}$ | **ZERO** |
| `log_vol_ratio` | 24 closed bars | $\ln(V_t / \text{Mean}(V_{t-23:t}))$ | Satisfies $t_{\text{feat}} \le t_{\text{sig}}$ | **ZERO** |
| `donchian_pos` | 24 closed bars | $(C_t - L_{24}) / (H_{24} - L_{24})$ | Satisfies $t_{\text{feat}} \le t_{\text{sig}}$ | **ZERO** |
| `ret_1h` | 1 closed bar | $\ln(C_t / C_{t-1})$ | Satisfies $t_{\text{feat}} \le t_{\text{sig}}$ | **ZERO** |
| `ret_4h` | 4 closed bars | $\ln(C_t / C_{t-4})$ | Satisfies $t_{\text{feat}} \le t_{\text{sig}}$ | **ZERO** |

### Normalization Audit:
Any standard scaler (z-score, min-max) applied across the full dataset introduces **global information leakage**. Feature standardization must be computed using **expanding or rolling windows** ($W = 720\text{ hours}$), never using future sample statistics.

---

## 4. ML Model Readiness Determination

### 4.1 Is Machine Learning Justified?
**No.** Current empirical evidence demonstrates that:
1. Standard technical features do not exhibit linear or non-linear correlation with 24-hour barrier outcomes ($R^2 < 0.01$).
2. Fitting a gradient boosted tree (LightGBM) or neural net to these 8 features will simply overfit historical noise, producing an illusory in-sample lift that collapses out-of-sample.
3. Simple linear baselines and constant prevalence classifiers must be matched and beaten with statistical significance before complex models are permitted.

### 4.2 Governance Action
- In accordance with Product Manager directives, **no model training pipeline was executed**.
- No weights, models, or configurations are promoted or registered.
- `models/authoritative_model_registry.py` preserves `HAR-RS-DOW-v1.0` locked to `OFFLINE_RESEARCH_ONLY`.

*Signed by Specialist Agent 5 (ML Research Specialist)*

