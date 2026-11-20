# Market Data Provider Requirements Specification (V32.61)

**Date:** 29 October 2026  
**Auditor / Author:** BTCognitive Lead Research Orchestrator  
**Document Status:** FROZEN SPECIFICATION  
**Scope:** Public-facing TradingView-like BTC market charting, technical indicators, and econometric volatility risk intelligence. Strictly NO live trading, broker connectivity, custody, or order execution (`trading_enabled = False`).

---

## 1. Product Scope & Functional Identity

BTCognitive is a read-only market intelligence and charting terminal. It provides:
1. High-fidelity candlestick charting (TradingView Lightweight Charts 4.1.3).
2. Standard technical indicators (EMA-9, EMA-21, EMA-50, RSI-14, ATR-14, Bollinger Bands, Donchian Channels).
3. Statistical volatility risk cones and conformal uncertainty envelopes (HAR-RS-DOW 7D Realized Variance).
4. Market state and macro regime monitoring.
5. Research excursion analysis.

**Strict Boundaries:**
- The application NEVER executes trades, places orders, routes orders to brokers, connects to exchange private trading APIs, or holds client funds/custody.
- All forecasts serve research and market risk visualization only; directional predictive hit rate claims are strictly unsupported.

---

## 2. Instrument & Data Shape Specifications

### 2.1 Canonical Instrument Selection
- **Primary Canonical Symbol:** `BTC/USD` spot pair on a single high-liquidity, transparent venue (Rank 1: **Bitstamp**).
- **Secondary Reference Symbol:** Aggregated `BTC/USD` cross-exchange index (Rank 2: **CoinGecko**, with attribution, display only).
- **Strict Invariant:** The platform must NEVER treat `BTC/USD` spot, `BTCUSDT` spot, and `BTCUSD_PERP` (perpetual futures) as interchangeable, nor stitch candles from different venues into a single undisclosed time series.

### 2.2 Timeframes & Granularities
| Timeframe | Candle Duration | Primary Consumer | Minimum Historical Window | Freshness Threshold |
| :---: | :---: | :--- | :--- | :--- |
| **1m** | 60 seconds | High-resolution intraday zoom, tick aggregator | 24 hours (~1,440 bars) | Stale if age > 120s |
| **5m** | 300 seconds | Intraday momentum inspection | 7 days (~2,016 bars) | Stale if age > 600s |
| **15m** | 900 seconds | Short-horizon volatility regime (`forecast_engine_15m`) | 30 days (~2,880 bars) | Stale if age > 1,800s |
| **1h** | 3,600 seconds | Core strategy tournament, Donchian channels, 24h RV | 365 days (~8,760 bars) | Stale if age > 7,200s |
| **4h** | 14,400 seconds | Intermediate swing structure | 2 years (~4,380 bars) | Stale if age > 28,800s |
| **1d** | 86,400 seconds | Macro HAR-RS-DOW 7D volatility model (`ohlcv.parquet`) | 5+ years (~1,825 bars) | Stale if age > 172,800s |

### 2.3 Required Candle Data Fields
Every ingested bar must satisfy the normalized schema:
1. `timestamp_utc`: ISO 8601 string (e.g. `2026-10-29T20:00:00Z`).
2. `timestamp_epoch`: Unix timestamp in integer seconds matching candle open boundary.
3. `open`: Floating-point price $> 0.0$.
4. `high`: Floating-point price $\ge \max(\text{open}, \text{close}, \text{low})$.
5. `low`: Floating-point price $\le \min(\text{open}, \text{close}, \text{high})$ and $> 0.0$.
6. `close`: Floating-point price $> 0.0$.
7. `volume`: Floating-point base currency volume $\ge 0.0$.
8. `is_closed`: Boolean flag. Must be `True` for finalized historical bars and `False` for forming/live bars.

---

## 3. Legal & Commercial Licensing Requirements

To be eligible for public production integration, a provider agreement must grant explicit, written authorization for:
1. **Public Customer-Facing Web Display:** Permission to render candlestick charts and technical indicators on a public website accessible to anonymous and registered visitors.
2. **Commercial Monetization:** Freedom to charge end users for subscriptions, premium analytics, or research reports without breaching redistribution terms.
3. **Derived Works & Volatility Forecasting:** Explicit permission to compute and display mathematical transformations (returns, realized variance, rolling volatilities, Sharpe ratios, conformal quantiles).
4. **AI/ML Model Training & Inference:** Written distinction authorizing:
   - *Inference:* Passing live/recent candles into pre-trained models to generate risk envelopes.
   - *Training/Validation:* Using historical candles to train, calibrate, tune, and backtest machine learning and econometric models.
5. **Server-Side Retention & Caching:** Right to maintain a local append-only Parquet database of closed candles for historical chart loading and feature calculation.
6. **Explicit Termination Provisions:** Clear documentation of post-termination data obligations (e.g., whether historical Parquet archives must be deleted or may be retained for audit compliance).

---

## 4. Disallowed Operations & Export Safeguards

The platform must enforce technical restrictions to prevent violating provider redistribution terms:
1. **No Raw Data Re-Export / Bulk API:** End users must NEVER be able to download full raw OHLCV datasets via CSV, JSON, or unmetered public API endpoints.
2. **Rate-Limited Server Proxying:** All upstream calls must be proxied and rate-limited by the FastAPI backend. API keys and vendor credentials must NEVER appear in client-side JavaScript bundles or public network requests.
3. **Fixture Isolation:** Deterministic QA fixtures must be strictly restricted to internal testing loopback routes (`/api/qa/seed-candles`) and inaccessible via public query parameters.
4. **No Synthetic Fabrication:** Incomplete candles or feed outages must result in an explicit `DATA_UNAVAILABLE` or `status: "ABSTAIN"` response. The system must NEVER interpolate missing prices or carry forward stale quotes.

