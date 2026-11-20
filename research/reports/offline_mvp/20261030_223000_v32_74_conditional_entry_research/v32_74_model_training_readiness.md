# V32.74 — Model Training Preparation & Audit Report

**Milestone:** V32.74 — Conditional Entry Quality Research  
**Date:** 2026-10-30  
**Classification:** Machine Learning & Feature Governance | OFFLINE_RESEARCH_ONLY  
**Readiness Decision:** ARCHITECTURE_AUDITED | TRAINING_NOT_AUTHORIZED

---

> [!IMPORTANT]
> **Governance Directive:**
> In accordance with the Product Manager instructions for V32.74:
> **NO MODEL WAS TRAINED, TUNED, PROMOTED, OR REGISTERED IN V32.74.**
> This document is strictly an engineering and econometrics audit of the 4 proposed prediction targets and 8 causal features to ensure mathematical validity, zero lookahead leakage, and proper validation design for future milestones.

---

## 1. Audit of the Four Proposed Prediction Targets

| Target ID | Name | Mathematical Definition | Data Type | Class Balance / Distribution | Leakage & Causal Integrity | Audit Verdict |
|---|---|---|---|---|---|---|
| **Target A** | `EQR_BINARY_1.5` | $\mathbb{I}(\text{MFE} / \text{MAE} > 1.50)$ | Binary $\{0, 1\}$ | ~38% Positive / ~62% Negative | Evaluated on forward $[t+1, t+24]$ window; requires strict fill at $t+1$ OPEN. Extreme outlier risk when $\text{MAE} \to 0$. | **Conditionally Approved** (Requires MAE floor $\ge 0.10\%$) |
| **Target B** | `TRIPLE_BARRIER_LABEL` | $+1$ (TP), $-1$ (SL), $0$ (Expired) | Multi-Class $\{+1, -1, 0\}$ | $+1$: 25%–31%<br>$-1$: 57%–62%<br>$0$: 8%–14% | First-passage touch time evaluated strictly on forward bars. AMBIGUOUS labels (1%) quarantined. | **Approved** (Recommended primary target) |
| **Target C** | `FORWARD_MFE_PCT` | $\max_{1 \le h \le 24} \left(\frac{\text{High}_{t+h} - \text{Open}_{t+1}}{\text{Open}_{t+1}}\right) \times 100\%$ | Continuous $\mathbb{R}^+$ | Positively skewed, bounded below by 0.0. Median: 1.48%. | Direction-dependent forward excursion. No intra-bar leakage. | **Approved** (Secondary regression target) |
| **Target D** | `FORWARD_MAE_PCT` | $\max_{1 \le h \le 24} \left(\frac{\text{Open}_{t+1} - \text{Low}_{t+h}}{\text{Open}_{t+1}}\right) \times 100\%$ | Continuous $\mathbb{R}^+$ | Positively skewed, bounded below by 0.0. Median: 1.12%. | Direction-dependent adverse excursion. No intra-bar leakage. | **Approved** (Secondary regression target) |

### Key Target Audit Findings:
1. **Target B (Triple-Barrier)** is the cleanest formulation for classification because it directly mirrors the trading decision space with stop-loss and take-profit mechanics.
2. **Severe Class Imbalance in Target B:** Stop-outs occur twice as frequently as profit targets ($60\%$ vs $30\%$) due to the 2:1 barrier asymmetry. Any ML loss function must incorporate balanced class weights (e.g. $w_{\text{TP}} \approx 2.0$, $w_{\text{SL}} \approx 1.0$) or focal loss to prevent the model from collapsing to an all-short or all-abstain predictor.
3. **Target A (EQR Binary) Caveat:** When adverse excursion is tiny ($\text{MAE} < 0.05\%$), EQR artificially spikes. A regularized denominator $\text{MFE} / (\text{MAE} + \epsilon)$ or a floor $\text{MAE} \ge 0.10\%$ is mathematically mandatory.

---

## 2. Audit of the Eight Causal Features

All features must strictly satisfy the point-in-time causal condition:
$$t_{\text{feature}} \le t_{\text{signal}} < t_{\text{fill}} < t_{\text{maturity}}$$
Features computed at the close of bar $t$ must never access data from bar $t+1$ or later.

| # | Feature Identifier | Mathematical Formula | Causal Window | Inference Availability | Lookahead Leakage Audit |
|---|---|---|---|---|---|
| 1 | `vol_ratio_1h_24h` | $\frac{\sigma_{1\text{H}}}{\sigma_{24\text{H}}} = \frac{|\ln(\text{Close}_t / \text{Close}_{t-1})|}{\sqrt{\frac{1}{24}\sum_{i=0}^{23} r_{t-i}^2}}$ | $[t-24, t]$ | Instantaneous at bar $t$ close | **ZERO LEAKAGE** |
| 2 | `trend_persistence` | $\frac{\text{EMA}_{12}(\text{Close})_t - \text{EMA}_{48}(\text{Close})_t}{\text{ATR}_{14}(t)}$ | $[t-48, t]$ | Instantaneous at bar $t$ close | **ZERO LEAKAGE** |
| 3 | `atr_distance_pct` | $\frac{\text{Close}_t - \text{SMA}_{20}(\text{Close})_t}{\text{ATR}_{14}(t)}$ | $[t-20, t]$ | Instantaneous at bar $t$ close | **ZERO LEAKAGE** |
| 4 | `volume_profile_ratio`| $\frac{\text{Volume}_t}{\frac{1}{24}\sum_{i=0}^{23}\text{Volume}_{t-i}}$ | $[t-24, t]$ | Instantaneous at bar $t$ close | **ZERO LEAKAGE** |
| 5 | `log_rv24h` | $\ln\left(\sum_{i=0}^{23} r_{t-i}^2 \times 8760\right)$ | $[t-24, t]$ | Standard production feature | **ZERO LEAKAGE** |
| 6 | `log_rv7d` | $\ln\left(\sum_{i=0}^{167} r_{t-i}^2 \times \frac{8760}{7}\right)$ | $[t-168, t]$ | Standard production feature | **ZERO LEAKAGE** |
| 7 | `dow_sin` | $\sin\left(\frac{2\pi \times \text{DOW}_t}{7}\right)$ | Static timestamp $t$ | Known calendar artifact | **ZERO LEAKAGE** |
| 8 | `dow_cos` | $\cos\left(\frac{2\pi \times \text{DOW}_t}{7}\right)$ | Static timestamp $t$ | Known calendar artifact | **ZERO LEAKAGE** |

### Key Feature Audit Findings:
1. **Zero Future Data:** None of the 8 features reference $t+1$ prices, intra-bar ticks, or future settlement prices.
2. **Missing-Value & Warm-Up Rule:** Because `log_rv7d` requires 168 closed hourly bars (7 days), the first 168 rows of any dataset contain NaN values. In training pipelines, the first 168 rows must be strictly dropped rather than zero-filled.
3. **Stationarity:** Log realized variances and normalized ratios (`vol_ratio_1h_24h`, `trend_persistence`, `atr_distance_pct`) are stationary time-series ($I(0)$), preventing spurious regressions common with raw price inputs.

---

## 3. Chronological Validation Architecture

To prevent data snooping and information leakage across time, any future model training must adhere to the 5 expanding folds pre-registered in `engine/manifests/v32_73_retrospective_walk_forward_manifest.json`:

```mermaid
graph TD
    subgraph Fold 1
    F1_Train[Train: 2022-01 to 2023-06] --> F1_Emb[Embargo: 24h] --> F1_Test[Test: 2023-07 to 2023-12]
    end
    subgraph Fold 2
    F2_Train[Train: 2022-01 to 2023-12] --> F2_Emb[Embargo: 24h] --> F2_Test[Test: 2024-01 to 2024-06]
    end
    subgraph Fold 3
    F3_Train[Train: 2022-01 to 2024-06] --> F3_Emb[Embargo: 24h] --> F3_Test[Test: 2024-07 to 2024-12]
    end
    subgraph Fold 4
    F4_Train[Train: 2022-01 to 2024-12] --> F4_Emb[Embargo: 24h] --> F4_Test[Test: 2025-01 to 2025-06]
    end
    subgraph Fold 5 (Holdout)
    F5_Train[Train: 2022-01 to 2025-06] --> F5_Emb[Embargo: 24h] --> F5_Hold[Holdout: 2025-07 to 2026-10]
    end
```

### Pre-Registration Rules for Future Training:
1. **24-Hour Embargo:** Because labels span up to 24 hours forward, training sets must terminate at least 24 hours before the test window begins to prevent label overlap leakage.
2. **Holdout Integrity:** Fold 5 test data (July 2025 to October 2026) must remain strictly quarantined from hyperparameter tuning and model selection.
3. **Acceptance Criteria for Future Authorization:**
   - Out-of-sample Diebold-Mariano test $p < 0.05$ vs Uniform Baseline.
   - Out-of-sample Net EV $> +0.00\%$ under `SCEN_1_BINANCE_VIP0` after 95% bootstrap lower bound.

---

## 4. Governance Status

- **Model Training Performed:** NONE.
- **Model Registration:** NONE.
- **Production Status:** `OFFLINE_RESEARCH_ONLY`.
- **Live Trading:** `DISABLED`.

---

*End of Model Training Preparation Report.*

