# 🔬 Hurdle Target Audit & Classifier Diagnostic Report

## Prevalence Across Partitions & Cost Multipliers

| Hurdle Definition | Train Prevalence % | Validation Prevalence % | Confirmation Prevalence % | Class Imbalance Ratio | Classification Feasibility |
| --- | --- | --- | --- | --- | --- |
| MFE > 14 bps (1.0x Cost) | 92.24 | 92.22 | 90.67 | 9.71:1 | Heavily Imbalanced (>85%) |
| MFE > 28 bps (2.0x Cost) | 86.57 | 86.22 | 86.44 | 6.38:1 | Heavily Imbalanced (>85%) |
| MFE > 42 bps (3.0x Cost) | 80.71 | 79.56 | 74.67 | 2.95:1 | Balanced Target |
| MFE > 56 bps (4.0x Cost) | 74.95 | 68.89 | 66.67 | 2.00:1 | Balanced Target |
| MFE > 70 bps (5.0x Cost) | 69.62 | 60.22 | 62.44 | 1.66:1 | Balanced Target |

## Classifier Probability Distribution (Explaining 0% High-Confidence Coverage)

| Probability Percentile | Predicted Probability P(MFE > 14 bps) |
| --- | --- |
| Min | 0.2847 |
| P10 | 0.378 |
| P25 | 0.4098 |
| P50 | 0.4606 |
| P75 | 0.5058 |
| P90 | 0.5387 |
| P95 | 0.5576 |
| Max | 0.6318 |

## Continuous Regression vs Binary Hurdle Comparison

| Model Paradigm | Primary Metric | Information Preserved | Practical Utility |
| --- | --- | --- | --- |
| 1. Continuous MFE Regression (Ridge) | Spearman IC = 0.2536 (p < 0.0001) | Full continuous ranking & magnitude | High (Sizes range, uncertainty, and envelope) |
| 2. Binary Hurdle Classification (Logistic) | ROC AUC = 0.6380 | Collapses to binary sign around threshold | Low (Underconfident, 0% high-conf coverage) |