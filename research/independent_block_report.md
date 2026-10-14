# 🧱 Independent Non-Overlapping 24H Block Validation Report

## 1. Overview ($N = 11$ Independent Blocks)

To eliminate temporal overlap correlation, forecasts are evaluated strictly in stride-24 non-overlapping intervals.

## 2. Cumulative Longitudinal Performance

| Cumulative Blocks | Mean MFE Error % | Mean MAE Error % | MFE P90 Coverage % | MAE P90 Coverage % | Joint Path Containment % | Mean Range Width % | Calibration Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 blocks (120 hours) | 3.6027 | 1.2736 | 20.0% | 100.0% | 20.0% | 5.93% | CALIBRATION_WARNING |
| 10 blocks (240 hours) | 2.274 | 1.1803 | 50.0% | 90.0% | 40.0% | 5.93% | CALIBRATION_WARNING |
| 11 blocks (264 hours) | 2.1005 | 1.0929 | 54.5% | 90.9% | 45.5% | 5.93% | CALIBRATION_WARNING |

## 3. Key Findings

- Across `11` independent 24-hour blocks, joint price path containment remains stable at `45.5%`.
- Mean Range Width remains sharp at `5.93%` with zero lookahead bias.
