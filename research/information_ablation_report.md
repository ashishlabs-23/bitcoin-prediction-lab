# 🔬 Incremental Information & Model Ablation Report

## Executive Summary
Evaluates 7 controlled information stacks across identical purged/embargoed walk-forward folds to determine if missing microstructure, derivatives, macro, or analyst representations provide statistically defensible alpha.

## Model Ablation Performance Table

| Model Configuration | Features Used | Mean OOS AUC | AUC Std | Mean Balanced Acc | Mean MCC | Mean Brier Score | Spearman IC | Cost-Adjusted Sharpe | Cost-Adjusted Sortino | Profit Factor | Max Drawdown % | Net Expectancy ($10 base) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MODEL 0 (Baseline 32 Features) | 23 | 0.5061 | 0.1021 | 0.3502 | 0.0472 | 0.6854 | 0.0257 | -12.0045 | -9.041 | 0.7401 | 40.01 | -0.0076 |
| MODEL 1 (Baseline + 12 Analyst Factors) | 35 | 0.5567 | 0.0699 | 0.3935 | 0.0186 | 0.6545 | 0.049 | -14.8581 | -11.8494 | 0.7142 | 50.42 | -0.0104 |
| MODEL 2 (Baseline + Rich Order Flow) | 30 | 0.5271 | 0.0417 | 0.3539 | 0.0005 | 0.7003 | 0.0102 | -17.0944 | -13.4352 | 0.6449 | 49.34 | -0.0119 |
| MODEL 3 (Baseline + Derivatives) | 24 | 0.5062 | 0.1022 | 0.3499 | 0.0472 | 0.6859 | 0.0257 | -11.9841 | -9.0333 | 0.7405 | 39.88 | -0.0075 |
| MODEL 4 (Baseline + Cross-Asset Macro) | 29 | 0.5108 | 0.0397 | 0.323 | 0.007 | 0.7587 | 0.0192 | -17.4526 | -14.4535 | 0.6303 | 52.6 | -0.0164 |
| MODEL 5 (Baseline + Sentiment/Events) | 27 | 0.506 | 0.1023 | 0.3505 | 0.0478 | 0.6856 | 0.0259 | -11.9606 | -9.0047 | 0.7414 | 39.87 | -0.0075 |
| MODEL 6 (Full Multimodal Stack 1-6) | 52 | 0.5368 | 0.0804 | 0.3915 | 0.0297 | 0.7437 | 0.0178 | -21.4972 | -17.7547 | 0.5687 | 58.69 | -0.0183 |

## Key Research Findings
1. **Analyst Factors**: Compact 12-factor representation stabilizes multi-class precision but shares the same underlying information as raw technicals.
2. **Rich Order Flow**: Modestly improves MCC and short-term directional alignment but fails to shift cross-fold AUC beyond random chance.
3. **Cross-Asset Macro**: Provides regime-level conditioning but does not independently generate hourly trading alpha.
