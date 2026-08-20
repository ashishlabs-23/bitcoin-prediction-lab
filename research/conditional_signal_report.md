# 🔬 Conditional Information & Factor Residualization Report

## Executive Summary
Tests whether Analyst factors contain genuinely new independent information or represent non-linear representation compression of raw OHLCV features.

## Factor Residualization Table

| Analyst Factor | Raw Factor IC | Raw IC p-val | Variance Explained by Raw (R²) | Residual Factor IC | Residual IC p-val | Functional Role |
| --- | --- | --- | --- | --- | --- | --- |
| tech_trend_score | -0.1646 | 0.0 | 0.9601 | -0.0263 | 0.4343 | Representation Compression |
| tech_momentum_score | -0.1575 | 0.0 | 1.0 | -0.1639 | 0.0 | Incremental Information |
| tech_breakout_score | 0.0 | 1.0 | 1.0 | 0.0 | 1.0 | Representation Compression |
| of_imbalance_score | 0.0186 | 0.5809 | 1.0 | 0.051 | 0.1301 | Representation Compression |
| of_liquidity_score | 0.0 | 1.0 | 0.0 | 0.0 | 1.0 | Representation Compression |
| of_pressure_score | 0.0 | 1.0 | 1.0 | 0.0 | 1.0 | Representation Compression |
| deriv_leverage_risk | 0.0 | 1.0 | 0.0 | 0.0775 | 0.0211 | Incremental Information |
| deriv_funding_pressure | -0.1598 | 0.0 | -0.2407 | -0.1599 | 0.0 | Incremental Information |
| deriv_oi_pressure | 0.0 | 1.0 | 1.0 | 0.0 | 1.0 | Representation Compression |
| sent_sentiment_score | -0.1754 | 0.0 | 0.9406 | -0.0926 | 0.0059 | Incremental Information |
| sent_sentiment_change | 0.0499 | 0.1385 | 0.4702 | 0.0405 | 0.2292 | Representation Compression |
| sent_event_intensity | 0.0312 | 0.354 | 0.0465 | 0.0103 | 0.7594 | Representation Compression |

### Primary Determination: **Incremental Information**
- Mean Raw Factor IC: `-0.0465`
- Mean Residual Factor IC: `-0.0219`
