# 🎯 24H Directional Signal Revalidation Report

## Directional Model Comparison

| Model Variant | Evaluation Split | AUC | Accuracy % | Balanced Acc % | MCC | Net Expectancy ($10) |
| --- | --- | --- | --- | --- | --- | --- |
| Majority Class Baseline | Final Confirmation | 0.5 | 30.67 | 33.33 | 0.0 | 0.0 |
| Random Guess Baseline | Final Confirmation | 0.5 | 33.33 | 33.33 | 0.0 | -0.014 |
| Purged Walk-Forward Logistic Reg | Walk-Forward CV (Dev) | 0.4963 | 32.99 | 34.45 | 0.0033 | -0.0418 |
| Purged Walk-Forward Logistic Reg | Untouched Final Confirmation | 0.4498 | 33.11 | 31.22 | -0.0397 | -0.0313 |

## Confirmation Bootstrap & Block Permutation Statistics

- **Confirmation AUC**: `0.4498`
- **Bootstrap 95% CI (AUC)**: `[0.4082, 0.4917]` (Excludes 0.50: **False**)
- **Block Permutation p-value**: `0.5000` (Rejects Null: **False**)
