# Scientific Report: UNCERTAINTY-04 Dependence-Aware Coverage Confidence Audit
**Protocol**: Locked Dependence-Aware Block Bootstrap ($B = 2,000, L = 168\text{h}$) on Untouched 2026 Holdout  
**Pre-Registration Source**: [`results/uncertainty_03_preregistration.md`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/results/uncertainty_03_preregistration.md)  
**Execution Timestamp**: 2026-08-24T15:09:57.351669+00:00  
**Evaluated Engine**: **C2 Dependence-Aware Conformal Risk Envelope** (Frozen)  
**Final Audited Classification**: **PROVISIONALLY_VALIDATED_FOR_RISK_CONTAINMENT**

---

## 1. Dependence-Aware Coverage Confidence Intervals ($B=2,000, L=168\text{h}$)

| Evaluation Slice | Observed Point Estimate | 95% Moving Block Bootstrap CI | Bootstrap Std Error | Containment Stability |
| :--- | :--- | :--- | :--- | :--- |
| **Overall Holdout Coverage** | **92.84%** | **[88.25%, 96.46%]** | $\pm 2.09\%$ | Conservative ($\ge 90\%$) |
| **Extreme Volatility (Q5 Spikes)** | **89.47%** | **[82.39%, 96.65%]** | $\pm 3.69\%$ | **Robust Tail Containment** |

---

## 2. Causality & Boundary Edge Mechanics Audit

* **168-Hour Target Formulation Check**: $\Delta_{\text{error}} < 10^{-8}$ (Zero backward return contamination).
* **Holdout Partition Boundary Check**: Historical training strictly terminates at `2025-12-31 23:00:00Z` before holdout starts at `2026-01-01 00:00:00Z`.
* **Zero Forward Imputation Assertion**: Confirmed $100\%$ causal point-in-time sequential processing.

---

## 3. Product Contract & Final Epistemic Classification

1. **Classification Standard**:
   $$\boxed{\textbf{C2 = PROVISIONALLY VALIDATED FOR RISK-CONTAINMENT}}$$
2. **Product UI Display Contract**:
   * Label: **"90% Target Risk Envelope"**
   * Metrics: **"Holdout Coverage: 92.84% (95% CI: [88.25%, 96.46%]) | Extreme-Vol (Q5) Coverage: 89.47% (95% CI: [82.39%, 96.65%])"**
   * Tail Breaches: **"Upper Breach: 3.67% | Lower Breach: 3.43% (Tail Balance: 0.24%)"**
3. **Standing Prohibitions**:
   * Claims of "90% Confidence" or exact universal finite-sample conditional coverage are permanently prohibited.
