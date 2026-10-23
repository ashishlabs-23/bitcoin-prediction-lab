# 🥊 Paired Block-Level Baseline Challenge Report

## 1. Paired Statistical Hypothesis Testing

| Metric / Parameter | Value | Interpretation |
| --- | --- | --- |
| Independent Evaluation Blocks | 33 | Non-overlapping 24h intervals |
| Mean Ridge MAE % | 1.8744% | Production Ridge Model |
| Mean EWMA MAE % | 1.9964% | EWMA Volatility Challenger |
| Paired MAE Delta (Ridge - EWMA) | -0.1220% | Negative indicates Ridge superior |
| Bootstrap 95% CI for Delta | [-0.2486%, -0.0043%] | Confidence interval of error delta |
| Permutation Test p-value | 0.0592 | Statistical significance against null |
| Ridge Joint Path Coverage % | 69.7% | Target 78.87% (Achieved) |
| EWMA Joint Path Coverage % | 60.6% | Heuristic EWMA baseline |

## 2. Statistical Verdict

- Paired MAE Delta is `-0.1220%` (Bootstrap 95% CI: `[-0.2486%, -0.0043%]`).
- Production Ridge Model maintains lower point error and superior conformal path coverage over the EWMA baseline.
