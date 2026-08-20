# 🎯 Quantile Calibration & Regime-Conditional Coverage Report

## Quantile Calibration (Pinball Loss & Coverage Error)

| Target Quantile | Nominal Quantile % | Empirical Confirmation Coverage % | Coverage Error % | Pinball Loss (x100) | Interval Sharpness % | Calibration Status |
| --- | --- | --- | --- | --- | --- | --- |
| P10 MFE | 10% | 11.11 | 1.11 | 0.0903 | 0.181 | Well-Calibrated (|err| <= 3%) |
| P25 MFE | 25% | 33.33 | 8.33 | 0.1891 | 0.532 | Miscalibrated |
| P50 MFE | 50% | 60.67 | 10.67 | 0.2601 | 1.056 | Miscalibrated |
| P75 MFE | 75% | 90.89 | 15.89 | 0.249 | 1.816 | Miscalibrated |
| P90 MFE | 90% | 99.78 | 9.78 | 0.1613 | 2.552 | Miscalibrated |

## Regime-Conditional 80% Coverage Stability

| Market Regime | Sample Count (n) | Empirical 80% Coverage % | Coverage Error % | Mean Interval Width % | Regime Coverage Reliability |
| --- | --- | --- | --- | --- | --- |
| Sideways | 450 | 88.67 | 8.67 | 2.371 | Conditional Shift |