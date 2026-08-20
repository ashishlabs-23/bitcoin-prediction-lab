# 🎯 BTCognitive: Forecast Calibration & Outcome Monitoring Protocol

## 1. Closed Forecast Outcome Resolution
For every completed 24-hour prediction window:
1. Extract actual forward 24-hour candles ($\text{High}_{24\text{h}}$, $\text{Low}_{24\text{h}}$, $\text{Close}_{24\text{h}}$).
2. Measure realized excursions:
   $$\text{Actual MFE} = \max\left(0, \frac{\text{High}_{24\text{h}}}{P_t} - 1\right)$$
   $$\text{Actual MAE} = \max\left(0, 1 - \frac{\text{Low}_{24\text{h}}}{P_t}\right)$$
3. Verify empirical containment:
   - **Upper Range Covered**: $\text{High}_{24\text{h}} \le \text{Upper}_{90}$ (Target: $\ge 90\%$)
   - **Lower Range Covered**: $\text{Low}_{24\text{h}} \ge \text{Lower}_{90}$ (Target: $\ge 90\%$)
   - **Full Price Path Contained**: $\text{High}_{24\text{h}} \le \text{Upper}_{90} \land \text{Low}_{24\text{h}} \ge \text{Lower}_{90}$ (Target: $\ge 78.8\%$)

---

## 2. Statistical Drift & Alert Thresholds

| Metric | Nominal Target | Warning Threshold (`CALIBRATION_WARNING`) | Critical Threshold (`DRIFT_CRITICAL`) | Action |
| :--- | :---: | :---: | :---: | :--- |
| **P90 Upper Coverage** | $90.0\%$ | $< 85.0\%$ | $< 80.0\%$ | Trigger Research Review |
| **P90 Lower Coverage** | $90.0\%$ | $< 85.0\%$ | $< 80.0\%$ | Trigger Research Review |
| **Full Path Containment** | $78.8\%$ | $< 73.0\%$ | $< 65.0\%$ | Trigger Research Review |
| **Mean Interval Width** | $1.35\%$ | $> 2.50\%$ | $> 3.50\%$ | Flag Volatility Regime Shift |

* **Research Review Policy**: When `CALIBRATION_WARNING` fires, automatic retraining is **NOT** triggered. Instead, the model monitor registers a research ticket to audit market regime shifts.
