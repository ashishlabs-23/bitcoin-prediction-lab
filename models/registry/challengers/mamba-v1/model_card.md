# 🐍 Model Card: Mamba Selective State-Space Range Challenger (v1.0.0)

## 1. Model Overview

* **Model Identifier:** `v1.0.0-challenger-mamba`
* **Architecture Family:** Selective State-Space Model (Mamba S6) with Causal 1D Convolution and Monotonic Positive Increment Quantile Heads.
* **Target Concept:** 24-hour Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE) Quantiles ($P_{10}, P_{25}, P_{50}, P_{75}, P_{90}$).
* **Primary Role:** Research Challenger against Production Ridge Baseline (`v3.0.0-excursion-ridge-conformal`).
* **Governance Status:** **`RESEARCH_CHALLENGER`** (Rejected for Production Promotion; Production Ridge Retained).

---

## 2. Architecture & Input Schema

* **Input Dimension:** 5 continuous factors (`vol_24h`, `rsi_14`, `atr_14`, `funding_rate`, `mvrv_zscore`).
* **Sequence Lookback Window:** 120h, 240h, 480h (Controlled Temporal Memory Trials).
* **Model Dimension ($d_{\text{model}}$):** 32
* **State Dimension ($d_{\text{state}}$):** 16
* **Number of Layers:** 2 Causal SSM Blocks with Residual Connections & LayerNorm.
* **Parameter Count:** $\approx 14,880$ trainable parameters.
* **Loss Function:** Combined Multi-Quantile Pinball Loss ($L_{\text{MFE}} + L_{\text{MAE}}$).

---

## 3. Empirical Validation Results (31 Independent 24h Blocks, 744 Hours)

| Metric | Production Ridge (`v3.0.0`) | Mamba Challenger (`240h`) | Promotion Verdict |
| :--- | :---: | :---: | :---: |
| **MFE Point Error (MAE)** | **`0.4120%`** | `0.4280%` | **FAIL (Ridge Superior)** |
| **MAE Point Error (MAE)** | **`0.5812%`** | `0.5880%` | **FAIL (Ridge Superior)** |
| **MFE P90 Coverage** | `93.5%` | `90.3%` | **PASS (Target $\ge 90.0\%$)** |
| **Joint Path Containment** | **`90.32%`** | `87.10%` | **PASS (Target $\ge 78.87\%$)** |
| **Mean Range Width** | **`5.92%`** | `6.05%` | **FAIL (Mamba Wider)** |
| **Winkler Score ($S_{0.10}$)** | **`624.32`** | `649.80` | **FAIL (Ridge Sharper)** |
| **Paired Permutation $p$-value** | Reference | $p = 0.3120$ | **FAIL (Not Significant)** |

---

## 4. Key Limitations & Governance Decision

1. **No Temporal Memory Advantage:** Testing context lengths across 120h, 240h, and 480h confirmed that longer temporal lookbacks do not yield lower MFE/MAE prediction error compared to compact regularized point-in-time features.
2. **Wider Intervals:** Mamba produced slightly wider confidence intervals (`6.05%` vs `5.92%`), leading to higher Winkler interval penalties.
3. **Decision:** **`RETAIN_PRODUCTION_RIDGE`**. Mamba remains archived as a research challenger and will not be promoted to production.
