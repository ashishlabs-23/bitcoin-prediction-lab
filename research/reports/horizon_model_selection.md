# 🧭 Horizon-Specific Model & Data Allocation Guide

## 1. Allocation Matrix

| Horizon | Primary Information Family | Architecture Family | Target Focus | Governance State |
| --- | --- | --- | --- | --- |
| 5m | Event-Time Order Flow (LOB + Hawkes) | Multivariate Hawkes + Quantile MLP | Transient Volatility & Direction | VALIDATED_SHADOW_MODEL |
| 15m | Order Flow Imbalance (OFI) + Depth | Linear Ridge / Quantile Regressor | Short-Term Order Book Liquidity | RESEARCH |
| 1h | OHLCV Momentum + OFI Residuals | Gradient Boosted Tree / Ridge | Intraday Momentum & Excursions | RESEARCH |
| 4h | Perpetual Funding Rate + ATR | Conditional Hurdle Regressor | Mean Reversion & Volatility Range | RESEARCH |
| 12h | Multi-Factor Technical + Volatility | Ridge Conformal Regressor | Intermediate Session Bounds | RESEARCH |
| 24h | Macro Realized Volatility + 24h Structure | Ridge Conformal Regressor v3.0.0 | Daily Structural Risk Envelope | PRODUCTION |
| 48h | Long-Term Macro Trend & Volatility | Historical Volatility Cone | Multi-Day Regime Dispersion | RESEARCH_EXPERIMENTAL |

## 2. Decoupled Architecture Rationale

Attempting to force a single monolithic model across all horizons dilutes specialized predictive features. Decoupling high-frequency event dynamics (5m) from structural daily volatility (24h) maximizes signal retention.
