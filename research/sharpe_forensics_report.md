# ⚖️ Sharpe Ratio Annualization & Dispersion Forensic Report

## Sharpe Scaling Comparison

| Sharpe Variant | Annualization Factor | Sharpe Value | Forensic Status |
| --- | --- | --- | --- |
| 1. Unannualized (Per 1h Bar) | 1.00x | -0.2299 | Pure Statistical Metric |
| 2. Time-Based Annualized (sqrt(8766)) | 93.63x | -21.5252 | WARNING: High Frequency Scaling |
| 3. Trade-Based Annualized (sqrt(Trades/Yr)) | 89.14x | -20.4938 | Correct Trade-Weighted Scaling |
| 4. Lag-1 Autocorrelation Adjusted | 0.28x | -5.9587 | Serial Correlation Corrected |
- **Calendar Days**: `18.71 days`
- **Lag-1 Autocorrelation**: `0.8576`
