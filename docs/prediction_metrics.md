# 📐 Canonical Prediction & Calibration Metrics Specification

This document establishes the **single source of truth** for all mathematical and statistical metric definitions used across BTCognitive APIs, dashboards, reports, and governance evaluations.

---

## 1. Probabilistic Range & Excursion Metrics (Primary Validated Product)

### Maximum Favorable Excursion Error ($\text{MAE}_{\text{MFE}}$)
$$\text{MAE}_{\text{MFE}} = \frac{1}{N} \sum_{i=1}^N \left| \text{Actual MFE}_i - \text{Predicted MFE}_{P50, i} \right|$$
Measures point-forecast accuracy of the predicted upward potential excursion over a 24-hour forward horizon.

### Maximum Adverse Excursion Error ($\text{MAE}_{\text{MAE}}$)
$$\text{MAE}_{\text{MAE}} = \frac{1}{N} \sum_{i=1}^N \left| \text{Actual MAE}_i - \text{Predicted MAE}_{P50, i} \right|$$
Measures point-forecast accuracy of the predicted downward maximum drawdown risk over 24 hours.

### Single-Sided $P_{90}$ Coverage
$$\text{Coverage}_{P90} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\text{Actual Excursion}_i \le \text{Predicted Bound}_{P90, i})$$
Nominal design target is **$90.0\%$**. Empirical validation on 31 independent blocks achieves **$93.5\%$** for MFE and **$96.8\%$** for MAE.

### Joint Full-Path Containment
$$\text{Joint Path Containment} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\text{Max High}_{i} \le \text{Upper}_{P90, i} \land \text{Min Low}_{i} \ge \text{Lower}_{P90, i})$$
Evaluates whether the entirety of the 24-hour intra-horizon price trajectory remained within predicted boundaries. Theoretical target limit: $0.90 \times 0.90 = 81.0\%$ (Nominal target: **$78.87\%$**). Empirical result: **$90.32\%$**.

### Winkler Interval Score ($S_\alpha$)
$$S_\alpha(L, U, y) = (U - L) + \frac{2}{\alpha}(L - y)\mathbb{I}(y < L) + \frac{2}{\alpha}(y - U)\mathbb{I}(y > U)$$
Penalizes wide intervals while severely penalizing interval breaches. Evaluated at $\alpha = 0.10$.

### Interval Sharpness
$$\text{Mean Range Width} = \frac{1}{N} \sum_{i=1}^N \frac{\text{Upper}_{P90, i} - \text{Lower}_{P90, i}}{P_{t, i}} \times 100\%$$
Target: $\le 8.0\%$ (Empirical result: **$5.92\%$**).

---

## 2. Statistical Independence & Effective Sample Size ($N_{\text{eff}}$)

When 24h forecasts are produced on hourly bars, serial correlation of overlapping residuals violates IID assumptions ($\rho_1 = 0.8966$).
$$N_{\text{eff}} = N \times \frac{1 - \rho_1}{1 + \rho_1}$$
All formal hypothesis tests and promotion gates require **stride-24 non-overlapping independent evaluation blocks**.

---

## 3. Directional Classification Metrics (Secondary Experimental Overlay)

### Directional Accuracy
$$\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}$$
Observed on 24h Bitcoin out-of-sample data: $\approx 51.8\%$ (Statistically indistinguishable from random walk; labeled **`EXPERIMENTAL / NO_MEASURABLE_EDGE`**).

### Balanced Accuracy
$$\text{Balanced Accuracy} = \frac{1}{2} \left( \frac{TP}{TP + FN} + \frac{TN}{TN + FP} \right)$$

### Matthews Correlation Coefficient (MCC)
$$\text{MCC} = \frac{TP \times TN - FP \times FN}{\sqrt{(TP + FP)(TP + FN)(TN + FP)(TN + FN)}}$$
Observed: $+0.021$ (No directional trading edge).
