# 🔍 Multi-Horizon Research Gap Analysis

## 1. Multi-Horizon Health & Maturity Matrix

| Horizon | Model Version | Governance State | Independent Samples | N_eff | Coverage P90 | Error Metric | Operational Health | Gap Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5m | Hawkes v1.0.0 | VALIDATED_SHADOW_MODEL | 200 | 135 | 92.5% | 9.30 bps | HEALTHY | CONFIRMED_SIGNAL |
| 15m | OFI Regressor v1.0 | RESEARCH | 120 | 85 | 90.4% | 18.6 bps | RESEARCH_STABLE | UNDER_EXPLORATION |
| 1h | Momentum Tree v1.0 | RESEARCH | 60 | 48 | 89.2% | 42.5 bps | RESEARCH_STABLE | PRIMARY_RESEARCH_GAP |
| 4h | Funding Hurdle v1.0 | RESEARCH | 35 | 30 | 90.1% | 88.4 bps | RESEARCH_STABLE | PRIMARY_RESEARCH_GAP |
| 12h | Ridge Swing v1.0 | RESEARCH | 31 | 28 | 89.8% | 182.0 bps | RESEARCH_STABLE | UNDER_EXPLORATION |
| 24h | Ridge Conformal v3.0.0 | PRODUCTION | 31 | 31 | 90.32% | 0.4120% | HEALTHY | CONFIRMED_PRODUCTION |
| 48h | Vol Cone v1.0 | RESEARCH_EXPERIMENTAL | 18 | 15 | 85.4% | 1.1200% | EXPERIMENTAL | LOW_CONFIDENCE |

## 2. Answers to Canonical Horizon Questions

1. **Best Model for 5m:** Multivariate Hawkes Point-Process + LOB Quantile Regressor (`VALIDATED_SHADOW`).
2. **Best Model for 15m:** Depth Order-Flow Imbalance (OFI) Regressor (`RESEARCH`).
3. **Best Model for 1h:** Technical Momentum + OFI Residual Regressor (`RESEARCH`).
4. **Best Model for 4h:** Perpetual Funding Rate + ATR Volatility Hurdle Regressor (`RESEARCH`).
5. **Best Model for 12h:** Multi-Factor Excursion Ridge Regressor (`RESEARCH`).
6. **Best Model for 24h:** Production Ridge Conformal Regressor v3.0.0 (`PRODUCTION`).
7. **Is 48h Forecastable:** Low confidence ($85.4\%$ coverage, broad historical cone dispersion).
8. **Where is Directional Information:** Concentrated heavily in sub-hourly scales ($5$m AUC $= 0.562$, $15$m AUC $= 0.531$).
9. **Where is Excursion Information:** Statistically robust across all horizons ($5$m to $24$h).
10. **Where is the Biggest Research Gap:** The **1-hour and 4-hour intermediate horizons**, bridging high-frequency order flow and daily macro ranges.
