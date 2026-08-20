# 🔍 Conditional Predictability & Market Subspace Report

## Executive Summary
Evaluates whether directional predictive information emerges when conditioning on specific market states (volatility regimes, trend strength, order flow imbalance, funding rates).

## Conditional Subspace Results Table

| Condition / Market Subspace | Test Sample Count (n) | OOS AUC | Balanced Acc | MCC | Spearman IC | Win Rate % | Profit Factor | Cost-Adjusted Sharpe | Net Expectancy ($10 base) | Statistical Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Low Volatility Subspace | 356 | 0.5074 | 0.3176 | 0.038 | 0.0383 | 44.66 | 1.1447 | -19.8079 | -0.0112 | Evaluated (n >= 50) |
| 2. Normal Volatility Subspace | 109 | 0.5 | 0.5467 | 0.1945 | 0.0583 | 57.8 | 1.7094 | -1.3402 | -0.0008 | Evaluated (n >= 50) |
| 3. High Volatility Subspace | 29 | 0.5 | 0.3333 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | Insufficient Sample (n < 50) |
| 4. Strong Trend State | 80 | 0.5384 | 0.3853 | 0.2126 | 0.393 | 52.5 | 1.7609 | -0.5656 | -0.0003 | Evaluated (n >= 50) |
| 5. Extreme Order Flow Imbalance | 141 | 0.5143 | 0.3038 | 0.0584 | 0.0565 | 39.72 | 1.1538 | -19.1033 | -0.011 | Evaluated (n >= 50) |
| 6. Elevated Funding Rate | 220 | 0.4846 | 0.3229 | -0.0287 | -0.1053 | 51.82 | 1.5735 | -5.8422 | -0.0034 | Evaluated (n >= 50) |