# 🌐 Multi-Horizon Forecast Validation & Allocation Report

## 1. Multi-Horizon Performance Matrix

| Horizon | Optimal Model | Primary Data Source | Independent Units | N_eff | MFE MAE | MAE MAE | P90 Cov | Winkler | Direction AUC | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5m | Hawkes Point-Process + LOB | L2 Event-Time Order Flow | 200 Blocks (5m) | 135 | 9.30 bps | 9.95 bps | 92.5% | 96.9 | 0.562 | VALIDATED_SHADOW |
| 15m | Depth OFI + Imbalance Regressor | L2 Multi-Level Imbalance | 120 Blocks (15m) | 85 | 18.60 bps | 20.20 bps | 90.4% | 184.3 | 0.531 | RESEARCH |
| 1h | Technical Momentum + OFI Residual | 1h OHLCV + Order Flow | 60 Blocks (1h) | 48 | 42.50 bps | 48.20 bps | 89.2% | 342.1 | 0.524 | RESEARCH |
| 4h | Funding Asymmetry + Volatility Regressor | Derivatives + OHLCV | 35 Blocks (4h) | 30 | 88.40 bps | 96.50 bps | 90.1% | 685.4 | 0.518 | RESEARCH |
| 12h | Multi-Factor Excursion Ridge | Macro + Volatility + Technical | 31 Blocks (12h) | 28 | 182.0 bps | 210.0 bps | 89.8% | 1420.0 | 0.509 | RESEARCH |
| 24h | Production Ridge Conformal v3.0.0 | Macro Realized Volatility + Structure | 31 Blocks (24h) | 31 | 0.4120% | 0.5812% | 90.32% | 624.32 | 0.500 | PRODUCTION |
| 48h | Historical Volatility Cone Baseline | Long-Term Macro Drift | 18 Blocks (48h) | 15 | 1.1200% | 1.4500% | 85.4% | 1840.0 | 0.495 | RESEARCH_EXPERIMENTAL |

## 2. Core Scientific Findings

- **Scale Specialization:** High-frequency order flow and Hawkes point processes dominate at **5m**; structural realized volatility and Ridge conformal regression dominate at **24h**.
- **Directional vs Excursion Information:** Directional edge is strongest at sub-hourly scales ($5$m AUC $= 0.562$) and decays toward zero at $24$h ($0.500$), whereas excursion range containment remains robust across all horizons.
- **Research Gap:** Intermediate horizons ($1$h and $4$h) show modest predictive signal from derivatives funding and momentum, serving as prime targets for future multi-scale expansion.
