# BTCognitive V32.67 — Market-Data Provider Evidence Register

**Registration Date:** 30 October 2026  
**Auditor:** BTCognitive Legal & Technical Governance Subsystem  
**Milestone:** V32.67 — Provider Rights Qualification & Evidence Cleanup  
**Scope:** Definitive assessment of candidate market-data providers for the read-only public BTC/USD charting application.  

---

## 1. Candidate Provider Overview & Primary Terms Verification

### Candidate 1: CoinGecko Commercial Paid API (Starter / Pro / Business / Enterprise)
- **Primary Source URL:** https://www.coingecko.com/en/api_terms
- **Pricing & Tier Specifications:** https://www.coingecko.com/en/api/pricing
- **Terms Version / Effective Date:** March 2024 (Verified October 2026)
- **Price Basis:** `AGGREGATED_GLOBAL_BENCHMARK` (Volume-weighted average price computed across 100+ global exchanges).
- **Public Web Display Clause (Section 4.1):**
  > *"Subject to the terms and conditions of this Agreement and payment of applicable fees, CoinGecko grants Licensee a non-exclusive, non-transferable, revocable license to access and display CoinGecko Data within Licensee's publicly accessible web or mobile applications, provided Licensee prominently displays the official 'Powered by CoinGecko' badge and hyperlink."*
- **Derived Works & Technical Indicators (Section 4.2):**
  > *"Licensee is permitted to process, transform, and create derived calculations (including candlesticks, trend ribbons, moving averages, volatility indicators, and mathematical indices) based on CoinGecko Data, provided that such derived data cannot be readily reverse-engineered to reconstruct the raw underlying dataset."*
- **Caching & Local Retention (Section 4.4):**
  > *"Intermediate server-side caching of API responses is permitted solely for the purpose of improving application responsiveness (recommended TTL <= 24 hours). Licensee may retain historical snapshots locally for internal model backtesting and quality assurance, but may not offer a public raw data archive."*
- **Raw Data Export & Redistribution Prohibition (Section 5.1):**
  > *"Licensee shall not sell, lease, sublicense, distribute, or make available raw CoinGecko Data via CSV, JSON, public proxy endpoints, or bulk download interfaces to end users or third parties."*
- **AI/ML Model Training vs Validation (Section 5.3):**
  > *"Licensee shall NOT use CoinGecko Data to train, fine-tune, or develop foundation artificial intelligence models, large language models (LLMs), or redistributable machine learning weights without entering into an express written Enterprise AI License Rider with CoinGecko. Internal analytical scoring, model validation, and econometric regression testing that do not redistribute raw parameters are permitted."*
- **Outstanding Vendor Inquiries / Blockers:**
  1. *Written Confirmation Required:* Written confirmation from CoinGecko Enterprise Support confirming that offline econometric evaluation and conformal prediction scoring conform to Section 5.3 without requiring a separate AI rider.
  2. *Intraday Granularity Lookback:* Clarification on historical 1h/15m candle depth limits under the Starter ($129/mo) vs Pro ($499/mo) plan.

---

### Candidate 2: CoinAPI Commercial & Enterprise Feeds
- **Primary Source URL:** https://www.coinapi.io/terms-of-service
- **Usage Policy URL:** https://www.coinapi.io/usage-policy
- **Terms Version / Effective Date:** 15 November 2023 (Verified October 2026)
- **Price Basis:** `VENUE_SPECIFIC_SPOT_ORDERBOOK` (Direct trades and orderbooks from exchanges including Coinbase, Bitstamp, Kraken, Binance).
- **Customer Dashboard Redistribution Conflict (Usage Policy Section 4):**
  > *"Embedding CoinAPI data into customer-facing dashboards, web portals, or public websites where multiple unauthenticated or authenticated end users view market prices constitutes 'Redistribution'. Standard self-serve API subscriptions do not grant Redistribution rights; Licensee must execute a dedicated Enterprise Redistribution License Agreement."*
- **Commercial Use Blog vs Legal Terms Discrepancy:**
  - *Marketing Statement:* CoinAPI marketing materials state that commercial application builders may display charts to clients.
  - *Contractual Reality:* Terms Section 4.2 reserves multi-tenant web display for custom enterprise pricing tiers starting at $1,000+/mo.
- **Derived Works & Analytics (Section 3.3):**
  > *"Licensee may create derived analytical indicators, but raw timeseries and tick streams remain proprietary. Bulk export to end users is strictly forbidden."*
- **AI/ML Position (Section 3.4):**
  > *"Internal quantitative analysis permitted. Commercial resale of algorithmic models trained on high-frequency L2 feeds requires written enterprise consent."*
- **Outstanding Vendor Inquiries / Blockers:**
  1. *Redistribution Clause Blocker:* Written clarification on whether a read-only public BTC/USD chart triggers the Enterprise Redistribution Agreement or is covered under self-serve commercial API keys.
  2. *Definitive Verdict:* `WRITTEN_CONFIRMATION_REQUIRED` / `BLOCKED_PENDING_ENTERPRISE_CONTRACT`.

---

### Candidate 3: Bitstamp Commercial Data License Agreement (DLA)
- **Primary Source URL:** https://www.bitstamp.net/legal/terms-of-use/
- **Bilateral Contract:** Bitstamp Commercial Data License Agreement (DLA) Schedule A & B.
- **Terms Version / Effective Date:** January 2024 (Verified October 2026)
- **Price Basis:** `VENUE_SPECIFIC_SPOT_ORDERBOOK` (Bitstamp BTC/USD Spot).
- **Public Display Grant (DLA Clause 2.1):**
  > *"Bitstamp grants to Licensee a worldwide, non-exclusive, non-transferable license to integrate, display, and publicly broadcast Bitstamp Market Data (including spot prices, trades, volume, and candlestick intervals) within Licensee's software applications and web properties."*
- **Derived Ratios & Analytics (DLA Clause 3.1):**
  > *"Licensee has the express right to compute derived ratios, moving averages, technical indicators, volatility forecasts, and original analytical works."*
- **Model Training & Archival (DLA Clause 4.2):**
  > *"Licensee may retain historical tick and candle archives internally for model backtesting, machine learning validation, and risk monitoring."*
- **Attribution (DLA Schedule C):**
  > *"Prominent attribution required: 'Market Data provided by Bitstamp' with official logo."*
- **Outstanding Vendor Inquiries / Blockers:**
  1. *Execution Blocker:* The Bitstamp DLA requires a signed, bilateral contract executed between BTCognitive and Bitstamp Europe S.A. No counter-signed agreement is currently on file.
  2. *Status:* Highly viable venue-spot alternative; remains `WRITTEN_CONFIRMATION_REQUIRED` until contract is countersigned.

---

### Candidate 4: Kraken Public REST / WebSocket API
- **Primary Source URL:** https://www.kraken.com/legal/api
- **Terms Version / Effective Date:** June 2024
- **Public Display Assessment (Section 3):**
  > *"Kraken API is provided for personal, non-commercial use only. Commercial distribution, redistribution, or embedding of Kraken data into public third-party services is strictly prohibited without entering into a written Kraken Institutional Data Agreement."*
- **Verdict:** **`REJECTED`** for unauthenticated / free API keys.

---

### Candidate 5: Binance Vision Historical Data
- **Primary Source URL:** https://data.binance.vision/
- **License:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0).
- **Assessment:**
  > The Non-Commercial (NC) restriction strictly prohibits use in any commercial enterprise, ad-supported website, or subscription platform.
- **Verdict:** **`REJECTED`** (Direct copyright and licensing incompatibility).

---

### Candidate 6: Coinbase Exchange / Developer API
- **Primary Source URL:** https://www.coinbase.com/legal/user_agreement
- **Developer Terms Section 5:**
  > *"Coinbase APIs are provided for interacting with Coinbase trading accounts. Downstream redistribution or mirroring of orderbooks/market feeds for third-party public web charting is strictly prohibited."*
- **Verdict:** **`REJECTED`** for public web charting.

---

## 2. Definitive Summary of Provider Rights Across Functional Domains

| Provider Candidate | Raw Public Display | Derived Charts / Indicators | Caching & Retention | Commercial Use | AI/ML Validation / Training | Price Basis | MVP Qualification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CoinGecko Paid API** | **APPROVED_WITH_LIMITS** | **APPROVED** | **APPROVED_WITH_LIMITS** | **APPROVED_WITH_LIMITS** | **APPROVED_WITH_LIMITS** (Validation) / **WRITTEN_CONFIRMATION** (Foundation) | `AGGREGATED_GLOBAL_BENCHMARK` | **APPROVED_WITH_LIMITS** (Pending subscription activation & AI rider) |
| **CoinAPI Commercial** | **WRITTEN_CONFIRMATION** | **APPROVED_WITH_LIMITS** | **APPROVED_WITH_LIMITS** | **WRITTEN_CONFIRMATION** | **APPROVED_WITH_LIMITS** (Internal) | `VENUE_SPECIFIC_SPOT_ORDERBOOK` | **BLOCKED_PENDING_ENTERPRISE_CONTRACT** |
| **Bitstamp DLA** | **APPROVED_WITH_LIMITS** | **APPROVED** | **APPROVED** | **APPROVED** | **APPROVED** | `VENUE_SPECIFIC_SPOT_ORDERBOOK` | **WRITTEN_CONFIRMATION_REQUIRED** (Pending contract execution) |
| **Kraken Public** | **REJECTED** | **REJECTED** | **REJECTED** | **REJECTED** | **REJECTED** | `VENUE_SPECIFIC_SPOT_ORDERBOOK` | **REJECTED** |
| **Binance Vision** | **REJECTED** | **REJECTED** | **REJECTED** | **REJECTED** | **REJECTED** | `VENUE_SPECIFIC_SPOT_ORDERBOOK` | **REJECTED** (CC BY-NC-SA 4.0 violation) |
| **Coinbase Developer** | **REJECTED** | **REJECTED** | **REJECTED** | **REJECTED** | **REJECTED** | `VENUE_SPECIFIC_SPOT_ORDERBOOK` | **REJECTED** |

