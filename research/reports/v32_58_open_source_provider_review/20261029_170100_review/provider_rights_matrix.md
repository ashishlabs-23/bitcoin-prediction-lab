# Market Data Provider Rights & Feasibility Matrix (V32.58)

**Audit Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Scope:** Commercial, public-facing online market charting and AI analytics release gates.

---

## 1. Provider Permissions Matrix

All entries reflect official, publicly verifiable terms as of October 2026. A public HTTP endpoint or developer key **never** implies commercial redistribution or public web display rights.

| Permission / Dimension | Bitstamp Commercial DLA | CoinAPI Paid Tier | CoinGecko Paid Commercial | Twelve Data Business | Speirsy11 (GitHub CC0) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Official Citation** | [bitstamp.net/api](https://www.bitstamp.net/api/) | [coinapi.io/faq](https://www.coinapi.io/products/market-data-api/faq) & [usage](https://www.coinapi.io/usage-policy) | [coingecko.com/terms](https://support.coingecko.com/articles/1043089972) | [twelvedata.com/pricing](https://twelvedata.com/pricing-business) | [github.com/Speirsy11](https://github.com/Speirsy11/crypto-dataset) |
| **Public Chart Web Display** | **CONFIRMED** (via Data License Agreement) | **CONFIRMED** (Customer-facing charts/tables permitted) | **CONFIRMED** (On paid plans with attribution) | **CONFIRMED** (Venture tier: client display) | **PROHIBITED** (Upstream Binance terms prohibit commercial use) |
| **Candle Tooltips / Interactive Hover** | **CONFIRMED** (Covered under redistribution agreement) | **CONFIRMED** (Interactive UI supported) | **CONFIRMED** (Supported in web apps) | **CONFIRMED** (Supported in web apps) | **PROHIBITED** (Chain of title broken) |
| **Derived Indicators (EMA, RSI, BB)** | **CONFIRMED** (Derived original works permitted) | **CONFIRMED** (Calculated metrics permitted) | **CONFIRMED** (Calculated inputs permitted) | **CONFIRMED** (Derived analytics permitted) | **PROHIBITED** (Derived works restricted by upstream) |
| **Risk Envelopes / Forecast Bounds** | **WRITTEN CONFIRMATION REQUIRED** | **WRITTEN CONFIRMATION REQUIRED** | **CONFIRMED** (Provided non-reconstructable) | **CONFIRMED** (Derived analytics permitted) | **PROHIBITED** |
| **Commercial Charging / Monetization** | **CONFIRMED** (Commercial tiers available) | **CONFIRMED** (Commercial plans permitted) | **CONFIRMED** (Permitted on paid plans) | **CONFIRMED** (Permitted on business plans) | **PROHIBITED** (Violates Binance commercial exclusion) |
| **Server-Side Caching & Retention** | **CONFIRMED** (Subject to contract retention clause) | **WRITTEN CONFIRMATION REQUIRED** (Requires specific clarification) | **CONFIRMED** (Allowed during subscription; deletion on termination) | **CONFIRMED** (Local caching permitted) | **UNKNOWN** |
| **Inference-Time Model Inputs** | **CONFIRMED** (Exchange spot price input) | **CONFIRMED** (API data consumption) | **CONFIRMED** (Calculation inputs) | **CONFIRMED** (API queries for inference) | **PROHIBITED** |
| **Model Training & Validation** | **WRITTEN CONFIRMATION REQUIRED** | **WRITTEN CONFIRMATION REQUIRED** (Requires AI addendum) | **PROHIBITED** (Explicitly prohibits AI/ML model training) | **WRITTEN CONFIRMATION REQUIRED** | **PROHIBITED** |
| **Raw Data Export / Download by Users** | **PROHIBITED** (Unless bespoke redistribution tier) | **PROHIBITED** (Standard policy forbids raw rehosting) | **PROHIBITED** (Raw redistribution prohibited) | **PROHIBITED** (Redistribution requires Enterprise tier) | **PROHIBITED** |
| **API Re-Export / Public Downstream API**| **PROHIBITED** (Without enterprise re-distributor grant) | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** |
| **Attribution Mandatory** | Yes (Bitstamp Data Attribution) | Yes (CoinAPI Logo/Attribution) | Yes ("Powered by CoinGecko" badge/link) | Yes (Twelve Data Attribution) | N/A |
| **Pair Coverage** | BTC/USD (Direct exchange spot) | BTC/USD (Multiple exchanges) | BTC/USD (Aggregated index) | BTC/USD (Aggregated & exchange spot) | Binance BTC/USDT only |
| **Estimated Cost** | Custom enterprise quote via partners@bitstamp.net | ~$250–$500/mo for commercial startup | ~$129–$499/mo depending on call volume | ~$499/mo (Venture tier monthly) | $0 (Non-commercial research only) |

---

## 2. In-Depth Provider Assessments

### 1. Bitstamp Commercial Data License Agreement (Rank 1A)
- **Strengths:** Pure exchange-specific BTC/USD spot candles with decades of continuous market history. Bitstamp explicitly offers a Data License Agreement permitting commercial redistribution and derived original works.
- **Constraints:** Pricing and contract negotiation must go through `partners@bitstamp.net`. Must ensure written addendum includes model validation and server-side caching rights.
- **Verdict:** Recommended primary candidate for exchange-native BTC/USD charting.

### 2. CoinAPI Paid Tier (Rank 1B)
- **Strengths:** Explicitly clarifies in official FAQ and Usage Policy that customer-facing charts, tables, and analytics applications are supported on paid plans.
- **Constraints:** Explicitly prohibits raw-data resale, bulk-export APIs, or rehosting. Written confirmation is needed regarding AI/ML training and retention lifetimes.
- **Verdict:** Highly viable turnkey API candidate for public MVP launch.

### 3. CoinGecko Commercial API (Rank 2)
- **Strengths:** Lowest friction self-serve commercial licensing with explicit allowance for customer-facing display and monetized websites.
- **Constraints:** **Strictly prohibits AI model training or public dataset creation.** BTC price is an aggregated global index rather than an exchange-specific order book execution price. Caching requires deletion upon contract termination.
- **Verdict:** Ideal for an analytics/display-first MVP, provided model retraining is decoupled from CoinGecko feeds.

### 4. Twelve Data Business Tier (Rank 3)
- **Strengths:** Turnkey WebSocket and REST infrastructure with explicit client-facing display tiers (Venture).
- **Constraints:** High baseline entry price (~$499/month), which may exceed initial private beta budget constraints.
- **Verdict:** Viable secondary candidate if Bitstamp or CoinAPI negotiations stall.

### 5. Critical Provenance Warning: Open GitHub / Hugging Face Datasets
- **Speirsy11/crypto-dataset (GitHub):** Although the repository uploader declared CC0, the data was scraped from Binance public endpoints. Binance's binding Terms and Conditions explicitly exclude commercial use without a signed enterprise license. Under copyright and database law, a downstream uploader cannot grant rights they do not own. **Do NOT use Speirsy11 for commercial production release.**
- **Hugging Face (`humblefool06/BTC_USDT_1m_candles`):** CC-BY-4.0 finite dataset (Jan 2024–Jan 2025) of BTC/USDT perp/spot. Useful strictly as an isolated, offline research benchmark; not a live feed or a legal substitute for BTC/USD spot.

