# 📉 Maximum Adverse Excursion (MAE) & Price Envelope Report

## Quantile MAE Confirmation Models (Pinball Loss)

| Target Quantile | Nominal Quantile % | Empirical Confirmation Coverage % | Coverage Error % | Pinball Loss (x100) | Mean Predicted MAE % |
| --- | --- | --- | --- | --- | --- |
| P10 MAE | 10% | 14.0 | 4.0 | 0.1005 | 0.158 |
| P25 MAE | 25% | 40.0 | 15.0 | 0.2412 | 0.579 |
| P50 MAE | 50% | 71.33 | 21.33 | 0.4111 | 1.197 |
| P75 MAE | 75% | 86.67 | 11.67 | 0.4532 | 2.329 |
| P90 MAE | 90% | 94.22 | 4.22 | 0.2725 | 3.357 |

## Conformal MAE Prediction Intervals

| Conformal Level | Target Coverage % | Empirical Confirmation Coverage % | Mean Interval Width % | Calibration Status |
| --- | --- | --- | --- | --- |
| 90% | 90.0% | 89.56 | 2.658 | Valid Coverage (Within 3%) |
| 95% | 95.0% | 93.11 | 3.054 | Valid Coverage (Within 3%) |

## Joint Excursion Price Envelope (Base $100,000 BTCUSD)

| Envelope Boundary | Magnitude % | BTCUSD (Base $100k) |
| --- | --- | --- |
| Expected Median Upside (MFE P50) | +0.91% | $100,914 |
| Expected Median Downside (MAE P50) | -1.20% | $98,803 |
| Tail Favorable Upside (MFE P90) | +1.77% | $101,766 |
| Tail Adverse Downside (MAE P90) | -3.36% | $96,643 |