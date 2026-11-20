# BTCognitive — Market-Data Provider Qualification Record & Legal Assessment

**Audit Milestone:** V32.65 — Provider Qualification & Preparation Gate  
**Date:** 30 October 2026  
**Status:** **FAIL-CLOSED (NO PROVIDER CURRENTLY LICENSED)**  
**Operating Mode:** `OFFLINE_RESEARCH_ONLY`  
**Public Release Gate:** **BLOCKED**  

---

## 1. Executive Legal & Technical Assessment

A public commercial deployment of BTCognitive requires clear, documented rights covering five specific operational dimensions:
1. **Public Visual Display:** Rendering interactive candlestick charts, order flows, and depth charts to end users in a web browser.
2. **Derived Calculations & Overlays:** Computing and displaying mathematical indicators (EMA, ATR, Donchian, Bollinger), volatility regimes, and empirical baseline forecast bounds.
3. **Data Retention & Caching:** Persisting historical closed candles locally to avoid redundant API polling and survive transient network outages.
4. **Model Training & Research Validation:** Using historical observations to train, validate, and red-team quantitative models (e.g. HAR-RS-DOW, Chronos-2, Wilson CIs).
5. **No Raw Redistribution / Downstream Resale:** Ensuring end-users cannot bulk-export, scrape, or treat BTCognitive as an unauthenticated market-data proxy.

### Critical Legal Boundaries
- **"Public API" ≠ Redistribution Rights:** Free REST endpoints provided by exchanges (Coinbase, Kraken, Binance) are licensed for account holders and individual trading, NOT for re-hosting in public SaaS or analytics applications.
- **Open-Source Client ≠ Data Rights:** The MIT or Apache 2.0 license of an API wrapper (e.g. CCXT, exchange SDKs) covers software logic only. It conveys zero proprietary rights to the market quotes returned by the underlying exchange.
- **Third-Party Datasets & Mirrors:** Public mirrors (e.g. Hugging Face datasets, GitHub repositories tagged CC-BY 4.0) frequently mislabel upstream exchange data. Under the upstream terms of Binance, Coinbase, and Kraken, raw tick/orderbook data remains proprietary; downstream users cannot rely on third-party CC-BY claims without verifying the chain of provenance.
- **Binance Vision Non-Commercial Restriction:** Binance Public Data (Vision) is explicitly published under the **CC BY-NC-SA 4.0** license. Commercial products are strictly prohibited without an executed enterprise data license agreement.

---

## 2. Evaluation of Primary Candidates

### Candidate A: CoinGecko (Primary Candidate to Qualify)
- **Licensing Tier:** Paid Commercial API (Analyst tier at $35/mo, Pro at $129/mo, or Custom Enterprise).
- **Price Basis:** **Aggregated Volume-Weighted Global Benchmark Price.** CoinGecko aggregates order books and trades across 100+ global spot exchanges. It is **not** a venue-specific orderbook (such as Coinbase BTC-USD).
- **UI Labeling Obligation:** The UI must explicitly state: `"Data Source: CoinGecko (Aggregated Global Benchmark)"`. It must not claim to represent venue-specific Coinbase spot execution.
- **Attribution Requirement:** CoinGecko commercial terms mandate prominent visual attribution: displaying the CoinGecko logo and linking back to `https://www.coingecko.com`.
- **Endpoint Granularity & Lookback Limitations:**
  - Standard `/coins/{id}/ohlc` returns fixed granularities tied to duration:
    - 1–2 days: 30-minute intervals.
    - 3–30 days: 4-hour intervals.
    - 31+ days: 4-day intervals.
  - Native 1-hour candles require `/coins/{id}/market_chart` (hourly sampling) or higher-tier Enterprise access.
  - 5-minute candles are limited to short lookback windows.
- **Redistribution Boundary:** Standard commercial plans permit display in customer applications with attribution, but **forbid** raw data resale, sublicensing, or exposing unrestricted raw JSON proxy endpoints.
- **Gate Status:** **PENDING WRITTEN CONFIRMATION.** Before executing an order form, obtain written confirmation from CoinGecko support/sales covering:
  1. Public web chart display of BTC hourly candles.
  2. Derived indicator and forecast overlays.
  3. Local caching for up to 90 days.
  4. Non-commercial model research and historical walk-forward validation.

### Candidate B: CoinAPI (Secondary Candidate; Clarification Required)
- **Licensing Tier:** CoinAPI Market Data API (Startup $79/mo, Business $249/mo, Enterprise).
- **Price Basis:** Offers both **Venue-Specific Spot Feeds** (`COINBASE_SPOT_BTC_USD`, `KRAKEN_SPOT_BTC_USD`, etc.) and aggregated indexes.
- **Current Terms Ambiguity:**
  - *Commercial Use Page:* Indicates paid subscribers may display charts, conduct internal analytics, and train ML models.
  - *Usage Policy & Redistribution Guidance:* Classifies any customer-facing application dashboard displaying market quotes as "redistribution", instructing customers to contact sales for custom pricing.
- **Redistribution Boundary:** Relying on the commercial-use blog post while ignoring the usage policy creates legal exposure.
- **Gate Status:** **PENDING WRITTEN AMENDMENT.** Written confirmation or order-form rider explicitly authorizing public customer-facing chart display without custom enterprise redistribution surcharges is required.

---

## 3. Provider Decision Record Template

```markdown
# Provider Qualification Decision Record

- **Vendor Name:** [CoinGecko / CoinAPI]
- **Proposed Tier:** [Analyst / Pro / Startup / Enterprise]
- **Estimated Monthly Cost:** [US$]
- **Contact / Inquiry Date:** [YYYY-MM-DD]
- **Vendor Representative:** [Name / Email / Ticket #]
- **Written Reply Status:** [PENDING / RECEIVED / REJECTED]

### Scope Checklist
| Operational Use | Permitted in Writing? | Contract Clause / Reference |
| :--- | :--- | :--- |
| Public Visual Chart Display | [YES / NO] | |
| Derived Indicator Overlays (EMA, ATR, Donchian) | [YES / NO] | |
| Volatility Forecast Bands (HAR-RS-DOW Baseline) | [YES / NO] | |
| Local In-Memory & Parquet Caching (<= 90 Days) | [YES / NO] | |
| Offline Model Evaluation / Research Training | [YES / NO] | |
| Raw Data Export / User CSV Download | [DISABLED] | Explicitly blocked in BTCognitive |

### Technical Limitations
- **Price Basis:** [Aggregated Benchmark / Venue-Specific Spot]
- **Supported Granularities:** [15m / 1h / 4h / 24h]
- **Historical Depth at 1h:** [Days / Candles]
- **Rate Limit:** [Calls / Minute]
- **Attribution String:** [Exact required UI banner text and link URL]

### Decision Sign-Off
- **Lead Orchestrator Verdict:** [REJECTED / APPROVED_FOR_STAGING]
- **Governance Status:** [FAIL_CLOSED_MAINTAINED]
```

---

## 4. Current Operating Invariant

Until a written vendor agreement covering all required uses is formally executed:
1. `DATA_MODE=provider` remains strictly **fail-closed** (`status="DATA_UNAVAILABLE"`, `reason="PROVIDER_NOT_CONFIGURED"`).
2. Outbound network transport from backend services to external exchanges remains blocked by [`assert_no_external_network()`](file:///c:/Projects/BTCognitive/BTCognitive/engine/data_mode.py).
3. The frontend chart runs solely on `fixture` (synthetic deterministic fixtures) or `offline_research` (local snapshot `data/raw/ohlcv.parquet`).

