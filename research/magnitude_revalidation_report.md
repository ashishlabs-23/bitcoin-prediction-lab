# 📈 Magnitude & Excursion Model Revalidation Report

## Partition Decay Analysis (Train -> Val -> Confirmation)

| Evaluation Partition | Sample Count (n) | Magnitude |r_24h| IC | MFE IC | MAE IC | Status |
| --- | --- | --- | --- | --- | --- |
| Train | 2100 | 0.2855 | 0.1727 | 0.298 | Baseline Training |
| Validation | 450 | 0.4241 | 0.3669 | -0.2599 | Tuning / Selection |
| Confirmation | 450 | -0.1357 | 0.2536 | -0.1078 | UNTOUCHED CONFIRMATION |

## Confirmation Model Comparison

| Model Variant | Target | Confirmation IC | MAE % |
| --- | --- | --- | --- |
| 1. Realized Volatility Baseline | |r_24h| | 0.0617 | 0.8195 |
| 2. Average True Range (ATR) Baseline | |r_24h| | 0.1209 | 118389.7173 |
| 3. EWMA Volatility Baseline | |r_24h| | 0.1476 | 0.8027 |
| 4. Ridge Magnitude Regressor | |r_24h| | -0.1357 | 0.877 |
| 5. Ridge MFE Regressor | MFE | 0.2536 | 0.5928 |
| 6. Ridge MAE Regressor | MAE | -0.1078 | 1.0975 |

- **Confirmation Magnitude IC**: `-0.1357`
- **Bootstrap 95% CI (IC)**: `[-0.2266, -0.0487]` (Excludes 0.0: **False**)
