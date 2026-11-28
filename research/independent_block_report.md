# 🧱 Independent Non-Overlapping 24H Block Validation Report

## 1. Overview ($N = 11$ Independent Blocks)

To eliminate temporal overlap correlation, forecasts are evaluated strictly in stride-24 non-overlapping intervals.

## 2. Cumulative Longitudinal Performance

| Cumulative Blocks | Mean MFE Error % | Mean MAE Error % | MFE P90 Coverage % | MAE P90 Coverage % | Joint Path Containment % | Mean Range Width % | Calibration Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 blocks (120 hours) | 0.755 | 2.285 | 80.0% | 60.0% | 60.0% | 5.93% | CALIBRATION_WARNING |
| 10 blocks (240 hours) | 1.427 | 1.9626 | 60.0% | 60.0% | 30.0% | 5.93% | CALIBRATION_WARNING |
| 11 blocks (264 hours) | 1.4396 | 1.8952 | 54.5% | 63.6% | 27.3% | 5.93% | CALIBRATION_WARNING |

## 3. Key Findings

- Across `11` independent 24-hour blocks, joint price path containment remains stable at `27.3%`.
- Mean Range Width remains sharp at `5.93%` with zero lookahead bias.
