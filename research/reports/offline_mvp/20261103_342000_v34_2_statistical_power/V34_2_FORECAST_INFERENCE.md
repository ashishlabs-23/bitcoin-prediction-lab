# BTCognitive V34.2 — Forecast Inference & Multi-Horizon Testing

**Document ID:** `V34_2_FORECAST_INFERENCE`  
**Mission:** `BTCognitive V34.2`  
**Agent:** `Agent 2 (Econometrics & Inference Specialist)`  
**Scope:** Overlapping Multi-Step Diebold-Mariano Inference, Bandwidth Sensitivity, Bootstrap & Multiple Testing  
**Operating Mode:** Strictly Offline Research  

---

## 1. Executive Summary & Core Results

Agent 2 conducted a rigorous econometrics audit of multi-step realized variance forecast evaluations across 1-day (24h), 7-day (168h), and 22-day (528h) horizons.

### Critical Econometric Principles Enforced

1. **Two-Sided Pre-Registration Rule:**  
   In standard quantitative finance literature (Diebold & Mariano 1995; Giacomini & White 2006), model comparison tests must be formulated as two-sided hypotheses ($H_0: \mathbb{E}[d_t] = 0$ vs $H_1: \mathbb{E}[d_t] \neq 0$) unless a one-sided directional alternative was pre-registered prior to data inspection. One-sided tests mechanically halve $p$-values, generating false claims of significance.
2. **Bandwidth Invariance & HAC Lag Rules:**  
   Because $h$-step rolling forecasts induce an $MA(h-1)$ error structure, Newey-West Bartlett kernel bandwidth must equal or exceed $h$. Testing was performed across $L \in \{h, 2h, 4h\}$.
3. **Generalized Multi-Horizon Joint DM Procedure (Quaedvlieg 2024 / McCracken & Sengupta 2021):**  
   Rather than evaluating horizons in isolation, a joint Wald-type test statistic was constructed across the $K=3$ horizons using the full long-run cross-covariance matrix $\mathbf{\Omega}$:
   $$W = T \cdot \mathbf{\bar{d}}^\top \mathbf{\Omega}^{-1} \mathbf{\bar{d}} \sim \chi^2(K)$$
   The joint test yielded $W = 4.502$, $p = 0.2121$, demonstrating **zero joint statistical significance across horizons**.

---

## 2. Horizon-by-Horizon Econometric Matrix

### A. 1-Day Horizon ($h = 24\text{ hours}$)
- Holdout Sample: 1,179 closed hourly observations
- Standard HAR QLIKE: **0.4025**
- Unconstrained OLS HAR-RS-DOW QLIKE: **1,887.26** (Catastrophic variance collapse due to collinear dummy overfitting)
- Mean Loss Differential ($\bar{d}$): $-1,886.86$ (Standard HAR overwhelmingly superior)

| Method / Bandwidth | Test Statistic ($t$ / $W$) | One-Sided $p$-value | Two-Sided $p$-value | Significance ($\alpha = 0.05$) |
| :--- | :---: | :---: | :---: | :---: |
| **Newey-West HLN ($L=24\text{h}$)** | $t = -1.861$ | $0.9685$ | $0.0629$ | **NOT SIGNIFICANT** |
| **Newey-West HLN ($L=48\text{h}$)** | $t = -1.842$ | $0.9671$ | $0.0658$ | **NOT SIGNIFICANT** |
| **Newey-West HLN ($L=96\text{h}$)** | $t = -1.868$ | $0.9690$ | $0.0621$ | **NOT SIGNIFICANT** |
| **Stationary Block Bootstrap ($B=2000, L=24$)** | — | $0.9625$ | $0.0375$ | *Bootstrap Borderline* |
| **Non-Overlapping ($N=50$ blocks)** | $t = -1.540$ | $0.9350$ | $0.1299$ | **NOT SIGNIFICANT** |

### B. 7-Day Horizon ($h = 168\text{ hours}$)
- Holdout Sample: 1,179 closed hourly observations
- Standard HAR QLIKE: **0.0458**
- HAR-RS-DOW QLIKE: **0.0461**
- Mean Loss Differential ($\bar{d}$): $-0.000336$ (Standard HAR superior)

| Method / Bandwidth | Test Statistic ($t$) | One-Sided $p$-value | Two-Sided $p$-value | Significance ($\alpha = 0.05$) |
| :--- | :---: | :---: | :---: | :---: |
| **Newey-West HLN ($L=168\text{h}$)** | $t = -0.111$ | $0.5440$ | $0.9120$ | **NOT SIGNIFICANT** |
| **Newey-West HLN ($L=336\text{h}$)** | $t = -0.101$ | $0.5401$ | $0.9199$ | **NOT SIGNIFICANT** |
| **Stationary Block Bootstrap ($B=2000, L=168$)** | — | $0.5560$ | $0.8920$ | **NOT SIGNIFICANT** |
| **Non-Overlapping ($N=8$ blocks)** | $t = -2.625$ | $0.9829$ | **0.0341** | **Standard HAR Superior ($p < 0.05$)** |

### C. 22-Day Horizon ($h = 528\text{ hours}$)
- Holdout Sample: 1,179 closed hourly observations
- Standard HAR QLIKE: **0.0278**
- HAR-RS-DOW QLIKE: **0.0274**
- Non-overlapping Sample: $N = 3$ independent blocks ($t = 0.405, p = 0.7249$, completely inconclusive due to zero statistical power).

---

## 3. Multiple Testing & Holm-Bonferroni Family-Wise Error Control

The family of pairwise tests was audited under Holm-Bonferroni step-down protection:

| Rank ($i$) | Pairwise Comparison | Raw Two-Sided $p$ | Multiplier | Holm-Adjusted $p$ | Governed Decision |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | `1d_HAR_RS_vs_HAR` | $0.0658$ | $\times 4$ | **$0.2632$** | **FAIL TO REJECT (Not Significant)** |
| **2** | `1d_HAR_RS_vs_Persistence` | $0.0658$ | $\times 3$ | **$0.1975$** | **FAIL TO REJECT (Not Significant)** |
| **3** | `22d_HAR_RS_vs_HAR` | $0.8214$ | $\times 2$ | **$1.0000$** | **FAIL TO REJECT (Not Significant)** |
| **4** | `7d_HAR_RS_vs_HAR` | $0.9199$ | $\times 1$ | **$0.9199$** | **FAIL TO REJECT (Not Significant)** |

**Conclusion:** After properly applying two-sided alternatives and family-wise error adjustments, zero models show a statistically defensible advantage over baseline Standard HAR.

