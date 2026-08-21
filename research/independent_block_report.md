# 🧱 Independent Non-Overlapping 24H Block Validation Report

## 1. Overview ($N = 11$ Independent Blocks)

To eliminate temporal overlap correlation, forecasts are evaluated strictly in stride-24 non-overlapping intervals.

## 2. Cumulative Longitudinal Performance

| Cumulative Blocks | Mean MFE Error % | Mean MAE Error % | MFE P90 Coverage % | MAE P90 Coverage % | Joint Path Containment % | Mean Range Width % | Calibration Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 blocks (120 hours) | 0.2869 | 0.8462 | 100.0% | 100.0% | 100.0% | 5.92% | CALIBRATION_OK |
| 10 blocks (240 hours) | 0.4593 | 0.8712 | 100.0% | 100.0% | 100.0% | 5.92% | CALIBRATION_OK |
| 11 blocks (264 hours) | 0.4429 | 0.9027 | 100.0% | 100.0% | 100.0% | 5.92% | CALIBRATION_OK |

## 3. Key Findings

- Across `11` independent 24-hour blocks, joint price path containment remains stable at `100.0%`.
- Mean Range Width remains sharp at `5.92%` with zero lookahead bias.
