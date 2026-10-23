# 🧱 Independent Non-Overlapping 24H Block Validation Report

## 1. Overview ($N = 11$ Independent Blocks)

To eliminate temporal overlap correlation, forecasts are evaluated strictly in stride-24 non-overlapping intervals.

## 2. Cumulative Longitudinal Performance

| Cumulative Blocks | Mean MFE Error % | Mean MAE Error % | MFE P90 Coverage % | MAE P90 Coverage % | Joint Path Containment % | Mean Range Width % | Calibration Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 blocks (120 hours) | 1.0215 | 1.3268 | 80.0% | 80.0% | 60.0% | 5.93% | CALIBRATION_WARNING |
| 10 blocks (240 hours) | 0.7489 | 0.9895 | 90.0% | 90.0% | 80.0% | 5.93% | CALIBRATION_OK |
| 11 blocks (264 hours) | 0.7071 | 0.9509 | 90.9% | 90.9% | 81.8% | 5.93% | CALIBRATION_OK |

## 3. Key Findings

- Across `11` independent 24-hour blocks, joint price path containment remains stable at `81.8%`.
- Mean Range Width remains sharp at `5.93%` with zero lookahead bias.
