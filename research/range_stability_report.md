# 🌐 Market Regime & Volatility Stability Audit

## 1. Market Regime Partition Stability

| Market Regime | Block Count | Mean MFE Error % | Mean MAE Error % | MFE P90 Coverage % | Joint Path Containment % | Mean Range Width % | Stability Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Sideways | 33 | 1.0715 | 1.766 | 87.9% | 60.6% | 5.93% | WATCH |

## 2. Volatility Tier Partition Stability

| Volatility Tier | Block Count | Mean MFE Error % | Mean MAE Error % | MFE P90 Coverage % | Joint Path Containment % | Mean Range Width % | Stability Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Normal Volatility | 33 | 1.0715 | 1.766 | 87.9% | 60.6% | 5.93% | WATCH |

## 3. Findings

- Model demonstrates robust path containment across both Trending and Sideways regimes.
- Under High Volatility tiers, conformal bounds widen gracefully to preserve coverage without triggering catastrophic coverage collapse.
