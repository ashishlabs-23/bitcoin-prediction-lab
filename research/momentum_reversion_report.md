# 🔄 Momentum vs Mean-Reversion Decomposition Report

## Executive Summary
Disentangles whether BTCUSD predictable structure is predominantly momentum continuation, mean-reversion, or regime-dependent.

## Model Performance Table

| Hypothesis Model | Features Used | Mean OOS AUC | AUC Std | Mean Balanced Acc | Mean MCC | Cost-Adjusted Sharpe | Net Expectancy ($10 base) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MODEL A (Pure Momentum Continuation) | 5 | 0.5265 | 0.0544 | 0.3538 | 0.0365 | -11.9619 | -0.0198 |
| MODEL B (Pure Mean Reversion) | 1 | 0.5205 | 0.0403 | 0.3531 | 0.0269 | -16.5114 | -0.0279 |
| MODEL C (Hybrid Confluence) | 6 | 0.5223 | 0.0583 | 0.3414 | 0.017 | -11.5107 | -0.0197 |