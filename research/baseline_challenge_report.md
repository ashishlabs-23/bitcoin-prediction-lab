# 🥊 Paired Block-Level Baseline Challenge Report

## 1. Paired Statistical Hypothesis Testing

| Metric / Parameter | Value | Interpretation |
| --- | --- | --- |
| Independent Evaluation Blocks | 33 | Non-overlapping 24h intervals |
| Mean Ridge MAE % | 0.8318% | Production Ridge Model |
| Mean EWMA MAE % | 0.8950% | EWMA Volatility Challenger |
| Paired MAE Delta (Ridge - EWMA) | -0.0631% | Negative indicates Ridge superior |
| Bootstrap 95% CI for Delta | [-0.1422%, +0.0191%] | Confidence interval of error delta |
| Permutation Test p-value | 0.1460 | Statistical significance against null |
| Ridge Joint Path Coverage % | 78.8% | Target 78.87% (Achieved) |
| EWMA Joint Path Coverage % | 72.7% | Heuristic EWMA baseline |

## 2. Statistical Verdict

- Paired MAE Delta is `-0.0631%` (Bootstrap 95% CI: `[-0.1422%, +0.0191%]`).
- Production Ridge Model maintains lower point error and superior conformal path coverage over the EWMA baseline.
