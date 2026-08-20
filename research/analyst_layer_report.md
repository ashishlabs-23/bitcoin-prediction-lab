# 🤖 Deterministic Analyst Layer Research Report

## Executive Summary
Evaluates the deterministic Analyst Layer (Technical, Order Flow, Derivatives, Sentiment) as a structured factor transformation mechanism (Zero LLM reliance).

## Baseline vs Analyst Layer Performance

| Model Configuration | Features Used | Mean OOS AUC | AUC Std | Mean Balanced Acc | Mean MCC | Mean Brier Score | Spearman IC | Cost-Adjusted Sharpe | Cost-Adjusted Sortino | Profit Factor | Max Drawdown % | Net Expectancy ($10 base) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MODEL 0 (Baseline 32 Features) | 23 | 0.5061 | 0.1021 | 0.3502 | 0.0472 | 0.6854 | 0.0257 | -12.0045 | -9.041 | 0.7401 | 40.01 | -0.0076 |
| MODEL 1 (Baseline + 12 Analyst Factors) | 35 | 0.5567 | 0.0699 | 0.3935 | 0.0186 | 0.6545 | 0.049 | -14.8581 | -11.8494 | 0.7142 | 50.42 | -0.0104 |