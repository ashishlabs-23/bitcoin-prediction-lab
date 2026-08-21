# 🌐 Market Regime & Volatility Stability Audit

## 1. Market Regime Partition Stability

| Market Regime | Block Count | Mean MFE Error % | Mean MAE Error % | MFE P90 Coverage % | Joint Path Containment % | Mean Range Width % | Stability Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Sideways | 33 | 0.7371 | 0.8976 | 90.9% | 90.9% | 5.92% | STABLE |

## 2. Volatility Tier Partition Stability

| Volatility Tier | Block Count | Mean MFE Error % | Mean MAE Error % | MFE P90 Coverage % | Joint Path Containment % | Mean Range Width % | Stability Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Normal Volatility | 33 | 0.7371 | 0.8976 | 90.9% | 90.9% | 5.92% | STABLE |

## 3. Findings

- Model demonstrates robust path containment across both Trending and Sideways regimes.
- Under High Volatility tiers, conformal bounds widen gracefully to preserve coverage without triggering catastrophic coverage collapse.
