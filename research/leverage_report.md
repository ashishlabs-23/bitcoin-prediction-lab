# 🛡️ Exposure Distribution & Leverage Scaling Report

## Exposure Quantiles

| Exposure Metric | Value |
| --- | --- |
| Minimum Exposure % | 0.00% |
| P25 Exposure % | 9.62% |
| Median Exposure % | 24.55% |
| Mean Exposure % | 28.54% |
| P75 Exposure % | 42.23% |
| P95 Exposure % | 71.97% |
| Maximum Exposure % | 100.00% (No Leverage > 100%) |
| Zero-Exposure Periods (n) | 43 (9.6%) |
| Leveraged Periods (>100%) | 0 (0.0%) |

## Leverage Sensitivity Sweep

| Leverage Multiplier | Effective Mean Exposure % | Avg Net Return % | Cost-Adjusted Sharpe | Max Drawdown % | Risk Profile |
| --- | --- | --- | --- | --- | --- |
| 0.25x | 7.13 | -0.0247 | -20.3734 | 11.47 | Conservative |
| 0.50x | 14.27 | -0.0494 | -20.3824 | 21.68 | Conservative |
| 0.75x | 21.4 | -0.0741 | -20.3854 | 30.75 | Leveraged Risk |
| 1.00x | 28.54 | -0.0987 | -20.3869 | 38.8 | Standard Unleverage |
| 1.25x | 35.67 | -0.1234 | -20.3878 | 45.96 | Leveraged Risk |
| 1.50x | 42.81 | -0.1481 | -20.3884 | 52.3 | Leveraged Risk |