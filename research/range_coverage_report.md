# 📈 Multi-Target Range & Price Path Coverage Report

## Coverage By Target Category

| Target Category | Nominal Target % | Empirical Coverage % | Target Definition | Status |
| --- | --- | --- | --- | --- |
| A. MFE Excursion Quantile (P90) | 90.0% | 90.0 | Actual MFE <= Predicted MFE P90 | Valid Excursion Bound |
| B. MAE Excursion Quantile (P90) | 90.0% | 90.0 | Actual MAE <= Predicted MAE P90 | Valid Downside Bound |
| C. Future High Price Containment (P90 Upper) | 90.0% | 89.44 | Future 24h High <= P_t * (1 + MFE_P90) | Robust High Bound |
| D. Future Low Price Containment (P90 Lower) | 90.0% | 89.44 | Future 24h Low >= P_t * (1 - MAE_P90) | Robust Low Bound |
| E. Full 24h Price Path Containment (P90 Joint) | 81.0% (0.90x0.90) | 78.87 | Entire 24h candle path stays inside [Lower, Upper] | Valid Joint Containment |
| F. Median Full Price Path Containment (P50 Joint) | 25.0% (0.50x0.50) | 12.68 | Entire 24h candle path stays inside [Lower_P50, Upper_P50] | Balanced Central Core |