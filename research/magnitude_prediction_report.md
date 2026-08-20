# 📈 Magnitude & Maximum Excursion Forecasting Report

## Magnitude Forecasting Models (|r_24h|)

| Magnitude Model | Mean Spearman IC | IC Std | Mean Absolute Error % | Root Mean Squared Error % | Predictive Validity |
| --- | --- | --- | --- | --- | --- |
| 1. Realized Volatility Baseline | 0.1202 | 0.0911 | 1.0803 | 1.3596 | Moderate Signal |
| 2. Average True Range (ATR) Baseline | 0.1515 | 0.0543 | 178837.8765 | 186972.3493 | Statistically Significant (p < 0.001) |
| 3. EWMA Volatility Baseline | 0.1158 | 0.0911 | 1.0767 | 1.3567 | Moderate Signal |
| 4. Ridge Magnitude Regressor | 0.1885 | 0.1772 | 0.9094 | 1.1422 | Statistically Significant (p < 0.001) |
| 5. MLP Magnitude Regressor | 0.0388 | 0.1005 | 1384939250.8229 | 2206691299.9169 | Moderate Signal |

## Maximum Excursion Models (MFE & MAE)

| Excursion Target | Mean Spearman IC | IC Std | Mean Absolute Error % | Statistical Significance |
| --- | --- | --- | --- | --- |
| Maximum Favorable Excursion (MFE) | 0.1075 | 0.1793 | 0.971 | Moderate |
| Maximum Adverse Excursion (MAE) | -0.0379 | 0.1549 | 1.18 | Moderate |