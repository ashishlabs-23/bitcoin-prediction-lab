# 🔬 Funding Rate Signal Confirmation & Point-in-Time Audit Report

## Point-in-Time Signal Construction Audit

| Audit Check | Specification | Status |
| --- | --- | --- |
| Funding Source | Perpetual Swap Hourly Funding Stream | PASS |
| Observation Timestamp | Hourly Candle Close (t) | PASS |
| Publication Buffer | Strict 5-second exchange publish lag | PASS |
| Rolling Window | 168 hours (7 days, shift(1) past-only) | PASS |
| Threshold Standardizer | Strictly backward-looking expanding/rolling std | PASS |
| Lookahead Correlation Test | Pearson corr with fwd returns: -0.1329 | PASS (No Leakage) |

## Directional Asymmetry Analysis

| Funding Shock Regime | Sample Count (n) | Mean Asset Return % | Mean Trade Gross Return % | Mean Trade Net Return % | Hit Rate % | Profit Factor | Cost-Adjusted Sharpe | Net Expectancy ($10 base) | Mechanics |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Positive Funding (> +2.0 sigma) -> SHORT | 72 | 0.3902 | -0.3902 | -0.5302 | 44.44 | 0.4319 | -9.7966 | -0.053 | Negative after friction |
| Negative Funding (< -2.0 sigma) -> LONG | 106 | -0.5944 | -0.5944 | -0.7344 | 30.19 | 0.3568 | -13.928 | -0.0734 | Negative after friction |

## Threshold Ladder Analysis

| Threshold Z-Score (sigma) | Active Sample Count (n) | Market Coverage % | Win Rate % | Avg Gross Return % | Avg Net Return % | Profit Factor | Cost-Adjusted Sharpe | Net Expectancy ($10 base) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 1225.0 | 40.83 | 44.49 | -0.0652 | -0.2052 | 0.9106 | -13.4121 | -0.0205 |
| 1.5 | 581.0 | 19.37 | 38.55 | -0.3027 | -0.4427 | 0.6386 | -21.1085 | -0.0443 |
| 2.0 | 178.0 | 5.93 | 35.96 | -0.5118 | -0.6518 | 0.4719 | -17.0009 | -0.0652 |
| 2.5 | 27.0 | 0.9 | 44.44 | -0.7194 | -0.8594 | 0.4164 | -6.5983 | -0.0859 |
| 3.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Holding Horizon Decomposition

| Holding Horizon (hours) | Active Sample Count (n) | Directional Win Rate % | Avg Gross Return % | Avg Net Return % | Cost-Adjusted Sharpe | Net Expectancy ($10 base) |
| --- | --- | --- | --- | --- | --- | --- |
| 1h | 178 | 26.4 | -0.0711 | -0.2111 | -32.1927 | -0.0211 |
| 4h | 178 | 26.4 | -0.2098 | -0.3498 | -15.3523 | -0.035 |
| 8h | 178 | 28.09 | -0.37 | -0.51 | -10.8516 | -0.051 |
| 12h | 178 | 30.9 | -0.4834 | -0.6234 | -9.9613 | -0.0623 |
| 24h | 178 | 35.96 | -0.5118 | -0.6518 | -4.9077 | -0.0652 |
| 48h | 178 | 25.84 | -1.0987 | -1.2387 | -4.9667 | -0.1239 |

## Volatility Proxy & Residualization Controls

| Control Group | Sample Count (n) | Win Rate % | Avg Gross Return % | Avg Net Return % | Cost-Adjusted Sharpe | Net Expectancy ($10 base) |
| --- | --- | --- | --- | --- | --- | --- |
| A. Funding Spike Only | 178 | 35.96 | -0.5118 | -0.6518 | -17.0009 | -0.0652 |
| B. High Volatility Only | 1020 | 45.49 | -0.0845 | -0.2245 | -12.6144 | -0.0224 |
| C. Funding Spike + High Volatility | 89 | 30.34 | -1.1891 | -1.3291 | -22.5614 | -0.1329 |
| D. Funding Spike + Normal Volatility | 89 | 41.57 | 0.1656 | 0.0256 | 0.6493 | 0.0026 |
| E. Funding Spike + No Return Shock | 169 | 34.91 | -0.6047 | -0.7447 | -19.3514 | -0.0745 |
| F. Funding Residualized against Vol & Return Shock | 3000 | 44.83 | -0.0694 | -0.2094 | 0.3661 | -0.0021 |