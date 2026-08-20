# 🎯 24-Hour Target Redesign & Out-of-Sample Validation Report

## Executive Summary
Evaluates the redesign of the BTCUSD prediction objective from 1h directional scalping to a 24-hour volatility-adaptive Triple Barrier event model with point-in-time intrabar High/Low detection.

## Target Comparison Table

| Target Family | Total Samples | BUY Count | SELL Count | HOLD Count | BUY Pct | SELL Pct | HOLD Pct | Majority Baseline | Overlap Rate | Mean Abs Future Move % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Target A (24h Fixed Direction) | 3000 | 1366 | 1335 | 299 | 45.53 | 44.5 | 9.97 | 0.4553 | 0.9923 | 1.352 |
| Target B (24h 2.0x TB Intrabar) | 2944 | 1426 | 1409 | 109 | 48.44 | 47.86 | 3.7 | 0.4844 | 0.8393 | 0.7414 |
| Target C (24h 1.5x TB Intrabar) | 2925 | 1441 | 1457 | 27 | 49.26 | 49.81 | 0.92 | 0.4981 | 0.7206 | 0.596 |

## Statistical Significance & Permutation Null Test

- **Observed Out-of-Sample AUC**: `0.5159`
- **Bootstrap 95% Confidence Interval**: `[0.4690, 0.5715]` (Excludes 0.50: **False**)
- **Permutation Test p-value**: `0.4180` (Null rejected at p<0.05: **False**)

## Economic Event Simulation (14 bps round-trip fee+slippage)

| Total Active Trades | Win Rate % | Profit Factor | Avg Gross Return per Trade % | Avg Round-Trip Cost % | Avg Net Return per Trade % | Avg Holding Hours | Cost-Adjusted Sharpe | Cost-Adjusted Sortino | Max Drawdown % | Expectancy per Trade ($10 base) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 467.0 | 52.46 | 1.2991 | 0.0626 | 0.14 | -0.0774 | 6.14 | -12.2724 | -10.2033 | 33.53 | -0.0077 |