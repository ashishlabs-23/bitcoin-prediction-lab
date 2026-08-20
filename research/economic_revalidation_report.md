# 💰 Economic Execution, Move Conditioning & Circuit Breaker Report

## Fee Schedule Sensitivity

| Fee Schedule (bps) | Trade Count (n) | Win Rate % | Avg Gross Return % | Avg Net Return % | Cost-Adjusted Sharpe | Max Drawdown % | Net Expectancy ($10 base) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.0 | 450.0 | 44.22 | -0.0912 | -0.0912 | -7.6198 | 38.6 | -0.0091 |
| 2.0 | 450.0 | 43.56 | -0.0912 | -0.1112 | -9.2907 | 43.32 | -0.0111 |
| 4.0 | 450.0 | 42.89 | -0.0912 | -0.1312 | -10.9616 | 47.84 | -0.0131 |
| 8.0 | 450.0 | 41.11 | -0.0912 | -0.1712 | -14.3034 | 55.83 | -0.0171 |
| 10.0 | 450.0 | 40.0 | -0.0912 | -0.1912 | -15.9742 | 59.5 | -0.0191 |
| 14.0 | 450.0 | 38.44 | -0.0912 | -0.2312 | -19.316 | 66.17 | -0.0231 |
| 20.0 | 450.0 | 36.22 | -0.0912 | -0.2912 | -24.3286 | 74.18 | -0.0291 |

## Directional Predictability Conditional on Large Moves

| Move Hurdle Threshold (bps) | Event Count (n) | P(Up | Move > Hurdle) % | P(Down | Move > Hurdle) % | Directional Accuracy in Events % | Cost-Adjusted Sharpe | Assessment |
| --- | --- | --- | --- | --- | --- | --- |
| 14.0 | 381 | 54.59 | 45.41 | 45.41 | -19.1422 | Symmetric / Random Direction |
| 25.0 | 338 | 54.73 | 45.27 | 44.97 | -18.9937 | Symmetric / Random Direction |
| 50.0 | 264 | 54.17 | 45.83 | 44.7 | -18.5248 | Symmetric / Random Direction |
| 75.0 | 205 | 53.66 | 46.34 | 44.88 | -17.8052 | Symmetric / Random Direction |
| 100.0 | 142 | 43.66 | 56.34 | 43.66 | -18.2137 | Symmetric / Random Direction |

## Circuit Breaker Risk Control Comparison

| Circuit Breaker Policy | Active Trades (n) | Coverage % | Win Rate % | Avg Net Return % | Cost-Adjusted Sharpe | Max Drawdown % | Tail Loss (5th Pct) % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Unconstrained Baseline Strategy | 450 | 100.0 | 38.44 | -0.2312 | -19.316 | 66.17 | -2.0957 |
| 2. Baseline + Scheduled Macro-Event Abstention | 435 | 96.67 | 38.16 | -0.2327 | -18.8845 | 65.2 | -2.1189 |
| 3. Baseline + Extreme Funding Abstention | 160 | 35.56 | 39.38 | -0.3092 | -20.0836 | 40.93 | -1.7105 |
| 4. Baseline + Volatility Shock Abstention | 449 | 99.78 | 38.31 | -0.2324 | -19.3812 | 66.28 | -2.0958 |
| 5. Baseline + Full Confluent Circuit Breaker | 154 | 34.22 | 39.61 | -0.3154 | -19.7738 | 40.39 | -1.7134 |

**Break-Even Round-Trip Cost**: `-9.12 bps`
