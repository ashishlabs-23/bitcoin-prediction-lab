# 🔬 Paper-Trading Trade Log Diagnostic Report

## Executive Summary
This diagnostic pass evaluates where the trading system succeeds and fails across 1,000 paper-trading entries to make architectural selection purely mechanical.

## Test A: Horizon Decomposition

| Horizon | Trade Count (n) | Directional Accuracy % | Win Rate % | Avg Net Return per Trade % | Total PnL ($) |
| --- | --- | --- | --- | --- | --- |
| 15m | 1000 | 48.8 | 26.6 | -0.1553 | -15.5337 |
| 1h | 1000 | 49.2 | 27.0 | -0.1353 | -13.5328 |
| 1m | 1000 | 50.9 | 27.9 | -0.1401 | -14.0095 |
| 24h | 1000 | 51.3 | 46.8 | -0.157 | -15.7041 |
| 4h | 1000 | 49.4 | 34.3 | -0.177 | -17.7009 |

## Test B: Confidence Calibration

| Confidence Bucket | Trade Count (n) | Avg Predicted Confidence % | Actual Directional Accuracy % | Calibration Gap % | Win Rate % | Avg Net Return % |
| --- | --- | --- | --- | --- | --- | --- |
| (0.0, 0.5] | 573 | 50.0 | 48.87 | -1.13 | 31.06 | -0.1656 |
| (0.5, 0.6] | 4367 | 56.52 | 50.13 | -6.4 | 32.79 | -0.1487 |
| (0.6, 0.7] | 60 | 60.68 | 45.0 | -15.68 | 26.67 | -0.3455 |

## Test C: Error Clustering in Time & Macro Events

| Worst 10% Loss Days Count | Loss-Day News Event Overlap % | Normal Days News Event Rate % | Event Risk Multiplier |
| --- | --- | --- | --- |
| 4.0 | 16.67 | 11.06 | 1.51 |

## Test D: PnL Attribution vs Directional Accuracy

| Directional Accuracy % | Trade Win Rate % | Avg Win Size % | Avg Loss Size % | Payoff Ratio (|Win/Loss|) | Profit Factor | Net Expectancy per Trade ($10 base) |
| --- | --- | --- | --- | --- | --- | --- |
| 49.92 | 32.52 | 0.4954 | -0.4654 | 1.0644 | 0.513 | -0.0153 |

## Mechanical Architecture Verdict

- **Directional Accuracy**: `49.92%`
- **Payoff Ratio (|Win/Loss|)**: `1.0644`
- **Loss-Day Event Overlap**: `16.67%`
- **Diagnosis**: `Selective Horizon Router + Magnitude/Volatility Regression + Event Circuit Breaker`
