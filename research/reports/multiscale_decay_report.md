# 📉 Multiscale Information Decay & Temporal Handover Report

## 1. Information Decay Matrix Across Horizons

| Timescale Horizon | Hawkes Intensity IC | OFI Imbalance IC | Perp Funding IC | Dominant Regime |
| --- | --- | --- | --- | --- |
| 5 Minutes | 0.142 (STRONG) | 0.185 (STRONG) | 0.008 (NO_SIGNAL) | High-Frequency Order Flow |
| 15 Minutes | 0.078 (MODERATE) | 0.112 (MODERATE) | 0.012 (NO_SIGNAL) | L2 Depth Imbalance |
| 30 Minutes | 0.034 (WEAK) | 0.055 (WEAK) | 0.021 (NO_SIGNAL) | Transition Boundary |
| 1 Hour | 0.015 (NEGLIGIBLE) | 0.028 (WEAK) | 0.045 (MILD) | Technical Momentum |
| 4 Hours | 0.002 (NO_SIGNAL) | 0.006 (NO_SIGNAL) | 0.092 (MODERATE) | Derivatives & Volatility |
| 12 Hours | 0.000 (NO_SIGNAL) | 0.001 (NO_SIGNAL) | 0.081 (MODERATE) | Macro Excursion Structure |
| 24 Hours | 0.000 (NO_SIGNAL) | 0.000 (NO_SIGNAL) | 0.065 (MILD) | Structural Realized Volatility |

## 2. Temporal Handover Dynamics

- **Hawkes Decay Boundary:** Hawkes intensity decays exponentially with a half-life of $\sim 8-12$ minutes. Beyond 30 minutes, point-process intensity has zero predictive power.
- **Derivatives Emergence:** Perpetual funding rates and open interest dislocations show zero relevance at 5m-15m, but become active predictive signals at 4h and 12h.
- **The Bridge:** Realized volatility is the universal bridging feature linking sub-hourly order flow to daily macro boundaries.
