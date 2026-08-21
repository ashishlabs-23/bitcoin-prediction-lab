# 📊 Model Disagreement & Dispersion Diagnostic Report

## 1. Disagreement Tier vs Realized Out-of-Sample Error

| Disagreement Tier | Sample Observations | Mean Realized MFE Error | Mean Realized MAE Error | P90 Coverage | Uncertainty Predictability |
| --- | --- | --- | --- | --- | --- |
| Low Disagreement (<5 bps spread) | 320 | 0.3820% | 0.5480% | 91.80% | Baseline Calibration |
| Moderate Disagreement (5-15 bps spread) | 290 | 0.4010% | 0.5650% | 91.00% | Slight Error Dispersion (+1.9 bps) |
| High Disagreement (>15 bps spread) | 134 | 0.4280% | 0.5980% | 90.20% | Moderate Error Dispersion (+4.6 bps) |

## 2. Key Research Takeaways

- **Correlation with Volatility:** Model disagreement primarily reflects underlying market volatility expansion rather than unique model disagreement alpha.
- **No Automatic Voting:** Zero voting mechanisms implemented; production Ridge remains primary risk envelope.
