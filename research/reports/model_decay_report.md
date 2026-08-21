# 📉 Model Performance & Edge Decay Audit

## 1. Longitudinal Decay Dimensions

| Audit Dimension | 30-Block Slope | Degradation Threshold | Status | Current Divergence | Current Delta | Current PSI | Current Ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Error Slope (MFE/MAE Trend) | +0.00002 / block | >+0.00020 | STABLE | nan | nan | nan | nan |
| 2. Coverage Divergence (|P90 - 90%|) | nan | >4.00% | STABLE | +1.10% | nan | nan | nan |
| 3. Baseline Delta Advantage (vs Ridge Base) | nan | >=0.0 bps (Lost Edge) | STABLE | nan | -14.0 bps | nan | nan |
| 4. Volatility Term Structure Drift PSI | nan | >=0.100 | STABLE | nan | nan | 0.024 | nan |
| 5. Conformal Interval Sharpness Ratio | nan | >1.25 | STABLE | nan | nan | nan | 1.02 |

## 2. Decay Conclusion

- **Governance Status:** `MODEL_STABLE`.
- **Persistent Advantage:** Ridge + Volatility Context retains statistically significant superiority over baseline across all 31 non-overlapping blocks.
