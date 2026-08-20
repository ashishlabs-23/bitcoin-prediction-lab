# 🏆 Analyst Layer Confirmation & Independent Holdout Report

## Executive Summary
Evaluates the deterministic Analyst Layer against raw features across 5 walk-forward CV folds and a strictly untouched independent confirmation holdout set ($n=250$).

## Model Confirmation Performance Table

| Model Variant | Features | CV Mean AUC | CV AUC Std | CV Balanced Acc | CV MCC | CV Cost-Adj Sharpe | Holdout AUC | Holdout Balanced Acc | Holdout MCC | Holdout Cost-Adj Sharpe | Holdout Net Expectancy ($10 base) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MODEL A (Raw Technical Features) | 23 | 0.4819 | 0.1139 | 0.3201 | -0.0115 | -19.5852 | 0.5307 | 0.3026 | -0.0232 | -18.3006 | -0.008 |
| MODEL B (Analyst Factors Only) | 12 | 0.525 | 0.0918 | 0.3572 | 0.0288 | -9.9899 | 0.4882 | 0.2575 | -0.0789 | -39.4319 | -0.0175 |
| MODEL C (Raw Technical + Analyst Factors) | 35 | 0.533 | 0.096 | 0.3793 | 0.0119 | -12.6821 | 0.5015 | 0.3064 | -0.0127 | -21.0831 | -0.0093 |
| MODEL D (Minimal Signal Set - 6 Factors) | 6 | 0.5014 | 0.0694 | 0.3514 | 0.0537 | -5.4905 | 0.4817 | 0.3461 | -0.0297 | -33.7381 | -0.0136 |

## Independent Holdout Block Bootstrap & Permutation Test

- **Holdout Observed AUC**: `0.4817`
- **Bootstrap 95% Confidence Interval**: `[0.2884, 0.5793]` (Excludes 0.50: **False**)
- **Block Permutation p-value**: `0.5000` (Rejects null: **False**)
