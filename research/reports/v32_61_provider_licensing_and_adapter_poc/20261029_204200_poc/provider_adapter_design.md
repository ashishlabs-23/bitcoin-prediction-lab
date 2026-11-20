# Market Data Provider Adapter Architecture & Design Specification (V32.61)

**Date:** 29 October 2026  
**Auditor / Architect:** BTCognitive Lead Research Orchestrator  
**Document Status:** TECHNICAL ARCHITECTURE DESIGN  
**Scope:** Public Chart MVP (TradingView-like read-only market charting & technical analytics).

---

## 1. Architectural Overview & Boundaries

The BTCognitive market data ingestion subsystem is redesigned around a pluggable **Provider Adapter Architecture**. This isolates all upstream transport protocols, data formats, vendor rate limits, and legal attribution clauses from the core application engine.

```mermaid
graph TD
    subgraph Upstream Market Data Feeds
        BitstampFeed["Bitstamp REST/WS (Rank 1: Single-Venue Spot)"]
        CoinGeckoFeed["CoinGecko REST (Rank 2: Multi-Venue Aggregate)"]
        QALoopback["QA Deterministic Loopback (/api/qa/seed-candles)"]
    end

    subgraph Feature Flag Isolation Gate
        FlagGate{"BTC_ENABLE_PROVIDER_ADAPTER == true?"}
    end

    subgraph BTCognitive Normalized Adapter Layer
        AdapterBase["IMarketDataProviderAdapter (Base Contract)"]
        BitstampAdapter["BitstampAdapter (Concrete Implementation)"]
        CoinGeckoAdapter["CoinGeckoAdapter (Concrete Implementation)"]
        MockAdapter["DeterministicMockAdapter (Isolated QA)"]
    end

    subgraph Normalized Data Stream & Validation
        Validator["Strict Invariant Validator (Extrema, Monotonic, Gaps)"]
        FreshnessMonitor["Feed Freshness & Staleness Evaluator"]
        ParquetCache["Provider-Specific Parquet Archive (Isolated Namespace)"]
    end

    subgraph Internal Consumers
        FastAPI["FastAPI /api/market/candles Endpoint"]
        ForecastEngine["Volatility Risk Forecast Engine (Closed-Bar Only)"]
        LightweightCharts["TradingView Lightweight Charts UI (app.js)"]
    end

    BitstampFeed -.-> FlagGate
    CoinGeckoFeed -.-> FlagGate
    QALoopback --> MockAdapter

    FlagGate -->|Enabled| BitstampAdapter
    FlagGate -->|Enabled| CoinGeckoAdapter
    FlagGate -->|Disabled (Default)| FailClosed["Fail-Closed (DATA_UNAVAILABLE / Mock Only)"]

    BitstampAdapter --> AdapterBase
    CoinGeckoAdapter --> AdapterBase
    MockAdapter --> AdapterBase

    AdapterBase --> Validator
    Validator --> FreshnessMonitor
    FreshnessMonitor --> ParquetCache
    FreshnessMonitor --> FastAPI
    FreshnessMonitor --> ForecastEngine
    FastAPI --> LightweightCharts
```

---

## 2. Normalized Data Contract

All provider adapters must transform raw upstream responses into the canonical normalized record:

```python
class NormalizedCandle(BaseModel):
    provider_id: str = Field(..., description="Unique provider ID (e.g. 'bitstamp', 'coingecko')")
    venue_or_aggregate: str = Field(..., description="'VENUE_SPECIFIC' or 'CROSS_VENUE_AGGREGATE'")
    symbol: str = Field(..., description="Standardized pair (e.g. 'BTC/USD')")
    base_currency: str = Field(..., description="Base asset (e.g. 'BTC')")
    quote_currency: str = Field(..., description="Quote asset (e.g. 'USD')")
    interval: str = Field(..., description="Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')")
    open_time_utc: str = Field(..., description="ISO 8601 UTC timestamp of candle open")
    close_time_utc: str = Field(..., description="ISO 8601 UTC timestamp of candle close")
    source_timestamp_utc: str = Field(..., description="Timestamp reported by provider")
    fetched_at_utc: str = Field(..., description="Local system retrieval timestamp in UTC")
    open: float = Field(..., gt=0.0)
    high: float = Field(..., gt=0.0)
    low: float = Field(..., gt=0.0)
    close: float = Field(..., gt=0.0)
    volume: float = Field(..., ge=0.0)
    candle_complete: bool = Field(..., description="True if bar is closed; False if forming")
    license_reference: str = Field(..., description="Mandatory attribution string")
```

---

## 3. Strict Operating Invariants & Validation Rules

### 3.1 Mathematical & Extrema Validation
Before any candle is accepted into memory or cached:
1. `high >= max(open, close, low)`
2. `low <= min(open, close, high)` and `low > 0`
3. `open > 0` and `close > 0`
4. `volume >= 0`
5. All values must be finite floating-point numbers (no `NaN`, `Inf`, or `null` prices in candle bars).

### 3.2 Monotonicity & Timestamp Integrity
1. Candlestick series must be strictly monotonic in time: $T_{i} > T_{i-1}$.
2. Duplicate timestamps are strictly rejected.
3. Timestamp intervals must match the declared candle cadence (e.g., exactly 3,600s between 1h bars). Any interval discrepancy $> 1.1 \times \text{cadence}$ is flagged as an explicit gap.

### 3.3 Zero Synthetic Candle Fabrication
- **Rule:** Under no circumstance may the adapter or storage engine interpolate, linearly synthesize, or carry forward prices to fill missing time intervals or outages.
- **Enforcement:** If an expected candle is missing, the response reflects an explicit gap. The backend flags `gap_detected = True` and fails closed (`status: "ABSTAIN"` / `DATA_UNAVAILABLE`) if downstream algorithms require gap-free series.

### 3.4 Explicit Null Price & Fail-Closed Behavior
- **Rule:** When the provider feed is unavailable, disconnected, rate-limited, or returns a 5xx error, the adapter must return an explicit `FeedFreshnessStatus.UNAVAILABLE` with `candles: []`.
- **Enforcement:** Returning a fabricated fallback quote (such as the legacy $80,000 price) is strictly forbidden. The frontend receives HTTP 400 or HTTP 503 with a structured error payload and renders an empty chart with an "Offline Market Data" warning banner.

### 3.5 No Silent Provider Fallback or Candle Stitching
- **Anti-Pattern Eliminated:** Legacy `fetch_binance_klines_async` silently chained Binance $\to$ Coinbase $\to$ Kraken $\to$ Bybit, mixing spot and perpetual futures across different venues.
- **Strict Invariant:** Adapters MUST NOT fall back across different venues. A Bitstamp request either succeeds with Bitstamp data or fails closed. Candles from different venues must NEVER be stitched into a single time series.

### 3.6 Forecast-Origin Anchoring Rule
- **Rule:** Volatility forecast markers (e.g., HAR-RS-DOW 7D Realized Variance) must be anchored to the chart ONLY when:
  1. `forecast.provider == chart.provider`
  2. `forecast.symbol == chart.symbol`
  3. `forecast.timeframe == chart.timeframe`
  4. `forecast.origin_timestamp == chart.latest_closed_candle.timestamp`
- **Enforcement:** If there is any mismatch in provider, symbol, or cutoff timestamp, the forecast marker is withheld from the candlestick overlay and rendered exclusively in an isolated diagnostic drawer labeled `SOURCE_MISMATCH_UNANCHORED`.

---

## 4. Feature Flag & Security Isolation

1. **Feature Flag:** `BTC_ENABLE_PROVIDER_ADAPTER` (environment variable, default: `false`).
2. **Offline-by-Default:** In production without a verified license key, the system remains in `OFFLINE_RESEARCH_ONLY` with the adapter disabled.
3. **Server-Side Credentials:** Vendor API keys (`BITSTAMP_API_KEY`, `COINGECKO_API_KEY`) reside exclusively in server environment variables and are never bundled into client-side JavaScript or returned in API responses.
4. **Namespace Isolation:** Data ingested by adapters is persisted to a dedicated namespace (`data/provider_cache/<provider_id>/`) and NEVER writes to or mutates the 6 protected research artifacts (`data/raw/ohlcv.parquet`, etc.).

