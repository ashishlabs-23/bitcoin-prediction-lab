# 🟢 Live Paper Forecast Validation Session Report

- **Session ID**: `7b8f609b-398c-4750-a7e8-60d52fd46500`
- **Start Time**: `2026-08-20T18:26:52.124321+00:00`
- **Forecast Count**: `276`
- **Resolved Count**: `276`
- **Joint Path Containment**: `99.28%` (Target: 78.87%)
- **Distribution Drift**: `NORMAL` (Distribution stable. No statistically significant drift.)

## Rolling Calibration Windows

| Rolling Window Size | Observed Samples | Calibration Status | MFE P90 Coverage % | MAE P90 Coverage % | Joint Path Containment % | Mean Range Width % | Mean MFE Error % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 25 bars | 25 | CALIBRATION_OK | 100.0% | 100.0% | 100.0% | 2.92% | 0.3246% |
| 50 bars | 50 | CALIBRATION_OK | 100.0% | 100.0% | 100.0% | 2.92% | 0.4729% |
| 100 bars | 100 | CALIBRATION_OK | 100.0% | 100.0% | 100.0% | 2.93% | 0.6046% |
| 250 bars | 250 | CALIBRATION_OK | 99.2% | 100.0% | 99.2% | 2.93% | 0.5423% |

## Benchmark Comparison

| Model / Baseline | Spearman IC | p-value | MAE % | RMSE % | P90 Coverage % | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Production Ridge MFE Model | nan | nan | 0.5291 | 0.6332 | 75.36 | Production Core |
| 2. Historical Percentile (168h) | 0.9018 | 7.3203e-102 | 0.1759 | 0.2188 | 88.77 | Baseline Reference |
| 3. EWMA Volatility Baseline | 0.6355 | 1.2567e-32 | 0.4187 | 0.521 | 79.71 | Baseline Reference |
| 4. Average True Range (ATR) | 0.7741 | 2.4971e-56 | 0.2915 | 0.3637 | 85.51 | Baseline Reference |