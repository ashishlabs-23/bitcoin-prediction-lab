# 🌐 BTCUSD Multiscale Dual-Horizon Product Validation Report

## 1. Synchronized Multiscale Forecast Table

| Forecast Layer | Horizon | Model Engine | Governance State | Role | Predicted Range | Directional Projection | Uncertainty |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Short-Horizon Layer | 5 Minutes | Hawkes Microstructure v1.0.0 | VALIDATED_SHADOW_MODEL | Short-Term Market Pressure | $65075.73 - $65326.16 | BEARISH | 0.1 |
| 2. Long-Horizon Layer | 24 Hours | Production Ridge Conformal v3.0.0 | PRODUCTION | Long-Term Risk Envelope | $63048.40 - $66911.50 | NO_DIRECTIONAL_EDGE | 1.6 |

## 2. Product Integrity Invariants

- **Decoupled Architecture:** 5-minute Hawkes shadow forecasting and 24-hour Production Ridge operate independently without synthetic path claims or probability blending.
- **Clear Labeling:** 5m output is explicitly labeled `SHADOW / EXPERIMENTAL`; 24h output is labeled `PRODUCTION`.
