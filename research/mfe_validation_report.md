# 📈 Maximum Favorable Excursion (MFE) Validation Report

## MFE Target Audit Across Horizons

| Horizon | Mean Long MFE % | Mean Short MFE % | Mean Long MAE % | Mean Short MAE % | Long/Short MFE Ratio | Leakage Correlation | Leakage Audit Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1h | 0.264 | 0.282 | 0.281 | 0.264 | 0.936 | -0.0623 | PASS (Zero Lookahead) |
| 4h | 0.542 | 0.595 | 0.588 | 0.542 | 0.911 | -0.0202 | PASS (Zero Lookahead) |
| 8h | 0.768 | 0.861 | 0.846 | 0.768 | 0.892 | 0.0153 | PASS (Zero Lookahead) |
| 12h | 0.943 | 1.067 | 1.045 | 0.943 | 0.883 | 0.0078 | PASS (Zero Lookahead) |
| 24h | 1.335 | 1.55 | 1.506 | 1.335 | 0.861 | -0.0189 | PASS (Zero Lookahead) |
| 48h | 1.869 | 2.268 | 2.174 | 1.869 | 0.824 | -0.0059 | PASS (Zero Lookahead) |

## MFE Model Baselines & Confirmation IC

| MFE Model / Baseline | Confirmation IC | p-value | MAE % | RMSE % | Assessment |
| --- | --- | --- | --- | --- | --- |
| 1. Realized Volatility Baseline | 0.1656 | 0.0004 | 0.6435 | 0.7716 | Statistically Significant (p < 0.01) |
| 2. Average True Range (ATR) Baseline | 0.1302 | 0.0057 | 118389.6162 | 124470.2953 | Moderate / Weak |
| 3. EWMA Volatility Baseline | 0.1846 | 0.0001 | 0.6302 | 0.7575 | Statistically Significant (p < 0.01) |
| 4. Historical MFE Percentile (Rolling 168h) | 0.2372 | 0.0 | 0.5033 | 0.6018 | Statistically Significant (p < 0.01) |
| 5. Ridge MFE Regressor | 0.2536 | 0.0 | 0.5928 | 0.6993 | Statistically Significant (p < 0.01) |
| 6. ElasticNet MFE Regressor | 0.0 | 1.0 | 0.6702 | 0.7932 | Moderate / Weak |
| 7. Small MLP Regressor | -0.1586 | 0.0007 | 22381561844.3937 | 22385373456.8671 | Moderate / Weak |

## Partition Decay Analysis (Train -> Val -> Confirmation)

| Partition | Sample Count (n) | Spearman IC | Status |
| --- | --- | --- | --- |
| Train (70%) | 2100 | 0.1727 | Baseline Fit |
| Validation (15%) | 450 | 0.3669 | Validation Tuning |
| Untouched Confirmation (15%) | 450 | 0.2536 | UNTOUCHED OOS CONFIRMATION |

## Volatility Residualization Control

| Signal Variant | Confirmation IC | p-value | Independent Alpha |
| --- | --- | --- | --- |
| 1. Unconditioned Ridge MFE Forecast | 0.2536 | < 0.001 | Yes (Combined) |
| 2. Realized Volatility Only | 0.1656 | < 0.001 | Baseline Proxy |
| 3. MFE Residualized against Volatility & ATR | 0.2435 | 0.0 | Yes (Residual Signal) |