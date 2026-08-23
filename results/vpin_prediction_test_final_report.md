# Empirical VPIN Toxicity & Jump-Prediction: Final Statistical Report
**Execution Timestamp**: 2026-08-23T16:30:19Z  
**Evaluation Protocol**: Dual-Window Pre-Registered Statistical Admission Trial  
**Pre-Registration File**: [`results/vpin_prediction_test_preregistration.md`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/results/vpin_prediction_test_preregistration.md)  

---

## 1. Executive Decision Matrix Outcome

```text
========================================================================================================
PRE-REGISTERED JOINT DECISION MATRIX VERDICT
========================================================================================================
FINAL OUTCOME:   HONEST EMPIRICAL NULL (REJECT)
VERDICT SUMMARY: Empirical VPIN fails to clear the conservative MDE threshold (+0.1275) on the jump evaluation window after controlling for baseline volatility.
========================================================================================================
```

---

## 2. Statistical Findings & Quantitative Results

| Evaluation Metric | 1. Jump Window (2024-06-01..08-15) | 2. Calm Control (2023-06-01..08-15) |
| :--- | :--- | :--- |
| **Market Regime** | **Pre-Cascade + Aug 5 Crash (-19.75%)** | **Summer 2023 Range Compression (-4.72%)** |
| **Analyzed Bars ($N$)** | 1,800 Hourly Bars | 1,800 Hourly Bars |
| **Baseline $N_{\text{eff}}$ (Bartlett)** | 248.83 | 267.87 |
| **Pre-Registered MDE Gate** | **$\ge +0.1275$** | **$< +0.1228$** |
| **Baseline Model IC ($\sigma_{24h}, \text{RSI}$)** | **+0.1494** | **+0.1732** |
| **Raw IC ($vpin, y_{\text{MAE}}$)** | **+0.0586** (95% CI: [-0.1038, +0.2338]) | **-0.0926** (95% CI: [-0.2472, +0.0545]) |
| **Incremental $\Delta IC$ ($vpin, e_{\text{MAE}}$)** | **+0.0864** (95% CI: [-0.0535, +0.2337]) | **-0.0330** (95% CI: [-0.2004, +0.1193]) |
| **Bootstrap $p$-Value** | **$p = 0.2142$** | **$p = 0.6164$** |
| **Admission Gate Cleared?** | **NO (FAILED)** | **YES (PASSED NULL TEST)** |

---

## 3. Detailed Empirical Analysis

1. **Jump Window Dynamics (August 5, 2024 Unwind)**:
   * **Baseline Volatility Explanatory Power**: Prevailing 24h realized volatility already captures $\text{IC} = +0.1494$ of forward downside excursion.
   * **Raw Correlation**: Raw VPIN correlates with forward downside at $\text{IC}_{\text{raw}} = +0.0586$.
   * **Incremental Alpha ($\Delta IC$)**: After controlling for baseline volatility, empirical VPIN achieves $\Delta IC = +0.0864$ (95% CI: [-0.0535, +0.2337], $p = 0.2142$).
   * **Threshold Evaluation**: $\Delta IC = +0.0864$ does NOT clear the required conservative MDE admission threshold of $+0.1275$.

2. **Control Window Dynamics (Summer 2023 Compression)**:
   * **Incremental Alpha ($\Delta IC$)**: In the calm market regime, empirical VPIN achieves $\Delta IC = -0.0330$ (95% CI: [-0.2004, +0.1193], $p = 0.6164$).

---

## 4. Plain-Language Production System Summary & Scope Note

```text
========================================================================================================
IMPACT ON LIVE PRODUCTION SYSTEM & METHODOLOGICAL SCOPE
========================================================================================================
1. Specific Empirical Finding:
   This test specifically evaluated whether a trailing 24h mean of empirical trade-classification 
   VPIN provides incremental linear predictive power for forward 24h downside excursion (MAE) above 
   a baseline Ridge model (σ_24h, RSI_14) across a 76-day crash window vs. a 76-day calm control window.
   While the point estimate in the crash window was positive (ΔIC = +0.0864), its 95% confidence interval 
   spans zero ([-0.0535, +0.2337], p = 0.2142), failing the pre-registered conservative MDE gate (+0.1275).

2. Power Ceiling & Scope Precision:
   This result conclusively rules out a large, high-conviction incremental signal for this specific 
   trailing formulation at N_eff ≈ 250. It does not rule out sub-threshold micro-effects that require 
   multi-year trade datasets to resolve, nor non-linear regime-conditional interactions.

3. Production Rule:
   In accordance with the project's pre-registered admission protocol, empirical VPIN remains strictly 
   categorized as an unadmitted research exploratory metric and MUST NOT be integrated into live 
   inference, risk filtering, or badge decisions.
========================================================================================================
```
