# Pre-Registration: Untouched Holdout Validation of Frozen C2 (UNCERTAINTY-03)
**Document Status**: LOCKED PRIOR TO INFERENCE  
**Target File**: `results/uncertainty_03_preregistration.md`  
**Execution Timestamp**: 2026-08-24T20:38:00Z  
**Research Protocol**: Strict Untouched Chronological Holdout Validation (Zero Tuning / Zero Recalibration)  
**Fixed Point Forecast**: **HAR-RS-DOW** ($\text{QLIKE} = 0.19300$)  
**Fixed Uncertainty Engine**: **C2 Dependence-Aware Asymmetric Scale-Aware Conformal**  

---

## 1. Research Question & Rationale

> **Core Scientific Question**:  
> Does the **Dependence-Aware Conformal Risk Envelope ($C_2$)**, calibrated on trailing non-overlapping steps to account for 168-hour multi-step target autocorrelation, **maintain $\ge 90.0\%$ overall coverage and $\ge 90.0\%$ extreme volatility (Q5) containment on a completely untouched chronological holdout** without degrading into uninformative interval inflation?

---

## 2. Invariants & Zero-Tuning Contract

1. **Point Forecast Frozen**: No retraining, no hyperparameter adjustment on HAR-RS-DOW.
2. **Calibration Engine Frozen ($C_2$)**:
   - Asymmetric conformity scores: $s_t^+ = \max\left(0, \frac{y_t - \hat{v}_t}{\hat{\sigma}_{\epsilon, t}}\right)$, $s_t^- = \max\left(0, \frac{\hat{v}_t - y_t}{\hat{\sigma}_{\epsilon, t}}\right)$
   - Calibration pool: Trailing $1000\text{h}$ buffer sub-sampled at daily non-overlapping intervals (`step = 24h`).
   - Nominal target: $\alpha = 0.10$ (90% target coverage).
3. **Zero Holdout Tuning**: Evaluated strictly sequentially on held-out chronological data.

---

## 3. Mandatory Evaluation Metrics & Pre-Registered Admission Gates

### A. Primary Performance Metrics:
1. **Holdout Coverage**: $\hat{C}_{\text{holdout}} = \frac{1}{N} \sum \mathbb{I}(y_t \in [L_t, U_t])$.
2. **Coverage Gap ($G$)**: $G = \hat{C}_{\text{holdout}} - 90.0\%$.
3. **Extreme Volatility Containment ($Q_5$)**: Coverage in the top 20% realized variance quintile ($y_t \ge P_{80}$).
4. **Tail Breach Symmetry**: $|\alpha_{\text{upper}} - \alpha_{\text{lower}}| \le 0.020$ ($2.0\%$ max tail asymmetry).
5. **Sharpness Retention**: Mean Width $\overline{W} \le 0.550$ and Winkler Score $\le 0.600$.

### B. Pre-Registered Admission Gates for Production Promotion:
* **Gate 1 (Overall Coverage Gate)**: $\hat{C}_{\text{holdout}} \ge 90.0\%$ ($G \ge 0\%$).
* **Gate 2 (Tail Containment Gate)**: $Q_5 \text{ Coverage} \ge 88.0\%$ and $Q_5 \text{ Upper Breach} \le 10.0\%$.
* **Gate 3 (All-Quintile Monotonicity)**: $Q_1, Q_2, Q_3, Q_4, Q_5 \text{ Coverage} \ge 85.0\%$.
* **Gate 4 (Tail Symmetry)**: $|\alpha_{\text{upper}} - \alpha_{\text{lower}}| \le 0.020$.

---

## 4. Execution Sequence

```
Step 0: Lock UNCERTAINTY-03 Pre-Registration [LOCKED]
  │
Step 1: Partition chronological dataset into Training/Calibration and Untouched Final Holdout (2026 Holdout)
  │
Step 2: Fit HAR-RS-DOW point forecasts strictly on historical data prior to holdout boundary
  │
Step 3: Deploy frozen C2 Dependence-Aware Conformal Risk Envelope sequentially across holdout
  │
Step 4: Compute Overall Coverage, Coverage Gap G, Q1-Q5 Quintile Breakdown, and Winkler Score
  │
Step 5: Output Full Holdout Report & Produce results/uncertainty_03_final_report.md
```
