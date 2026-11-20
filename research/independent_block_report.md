# 🧱 Independent Non-Overlapping 24H Block Validation Report

## 1. Overview ($N = 31$ Independent Blocks)

To eliminate temporal overlap correlation, forecasts are evaluated strictly in stride-24 non-overlapping intervals.

## 2. Cumulative Longitudinal Performance

| Cumulative Blocks | Mean MFE Error % | Mean MAE Error % | MFE P90 Coverage % | MAE P90 Coverage % | Joint Path Containment % | Mean Range Width % | Calibration Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 blocks (120 hours) | 1.1557 | 0.9368 | 80.0% | 100.0% | 80.0% | 5.92% | CALIBRATION_OK |
| 10 blocks (240 hours) | 0.881 | 1.1238 | 90.0% | 90.0% | 80.0% | 5.92% | CALIBRATION_OK |
| 20 blocks (480 hours) | 0.7705 | 0.9712 | 95.0% | 95.0% | 90.0% | 5.92% | CALIBRATION_OK |
| 30 blocks (720 hours) | 0.7617 | 0.9013 | 96.7% | 93.3% | 90.0% | 5.92% | CALIBRATION_OK |
| 31 blocks (744 hours) | 0.7455 | 0.8896 | 96.8% | 93.5% | 90.3% | 5.92% | CALIBRATION_OK |

## 3. Key Findings

- Across `31` independent 24-hour blocks, joint price path containment remains stable at `90.3%`.
- Mean Range Width remains sharp at `5.92%` with zero lookahead bias.
