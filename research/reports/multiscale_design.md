# 🌐 Multiscale BTCUSD Forecast Architecture & UI Specification

## 1. Dual-Horizon Architecture Specification

- **Short-Horizon Subsystem (5m):** High-frequency Hawkes point-process + LOB imbalance emitting transient 5-minute volatility and excursion bounds.
- **Long-Horizon Subsystem (24h):** Production Ridge Conformal Regressor emitting daily structural risk envelopes.

## 2. Decoupled Display Invariant

The two layers remain mathematically independent without probability blending, presenting distinct high-frequency pressure vs daily structural limits.
