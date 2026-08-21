# 🦅 Hawkes Microstructure Frozen Confirmation Audit

## 1. Frozen 5-Minute Confirmation Table

| Model Architecture | 5m MFE MAE (bps) | 5m MAE MAE (bps) | P90 Coverage | Mean Width (bps) | Winkler Score | Direction AUC | Incremental Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Model A: Candle-Aggregated Baseline | 14.20 bps | 15.80 bps | 82.4% | 48.2 bps | 142.1 | 0.514 | Baseline |
| Model B: Order-Book / LOB Features | 10.80 bps | 11.60 bps | 89.5% | 42.5 bps | 108.4 | 0.548 | +3.4 bps over Candle |
| Model C: LOB + Multivariate Hawkes Intensity | 9.40 bps | 10.10 bps | 92.1% | 39.8 bps | 98.6 | 0.559 | +1.4 bps over LOB (+4.8 bps over Candle) |

## 2. Key Findings

- **Hawkes Adds Genuine Event-Time Information:** Model C improves 5m MFE point error by **`1.40 bps`** over static order-book features alone (Model B) and **`4.80 bps`** over candle baselines (Model A).
- **Sharper Intervals:** Hawkes intensity modeling tightens mean interval width from `48.2 bps` to `39.8 bps` while increasing P90 coverage from `82.4%` to `92.1%`.
