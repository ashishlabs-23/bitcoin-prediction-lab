# 📐 Probability Calibration & Reliability Report

## Probability Quality Metrics

| Model Variant | Brier Score | Expected Calibration Error (ECE) |
| --- | --- | --- |
| Uncalibrated Logistic Regression | 0.25 | 0.0484 |
| Platt-Calibrated Logistic Regression | 0.2503 | 0.0474 |

## Calibration Methodology
- Base models are trained on Sub-Train partitions.
- Platt sigmoid scaling is calibrated strictly on Validation partitions.
- Evaluated out-of-sample on untouched Test folds with Expected Calibration Error (ECE) measurement.
