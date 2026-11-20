# Multi-Provider Market Data Rights & Legal Matrix (V32.59)

**Audit Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Operational Constraint:** Zero vendor outreach sent (no emails, contact forms, or support tickets). All assessments derived strictly from authoritative published legal documentation, Terms of Service, and API licensing agreements.  
**Scope:** Commercial, public-facing online market charting (TradingView-like UI), interactive technical indicators, econometric risk envelopes, server-side caching, and prospective validation.

---

## 1. Comprehensive 11-Provider Rights & Capabilities Matrix

| Provider / Dataset | Official Legal Terms & Citation | Public Chart Web Display | Interactive Hover / Tooltips | Derived Indicators (EMA, RSI, BB) | Volatility Envelopes / AI Forecast | Model Training / Backtesting | Server-Side Caching | Commercial Web Monetization | Attribution Required | Cost / Tier | Release Gate Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Coinbase Exchange REST / WS** | [Coinbase Market Data Terms (Aug 7, 2026)](https://www.coinbase.com/legal/market_data) | **PROHIBITED** without prior express written consent | **PROHIBITED** | **PROHIBITED** (Derived works restricted) | **PROHIBITED** | **PROHIBITED** (Explicit AI/ML restriction) | **LIMITED** (Internal dev only) | **PROHIBITED** | Mandatory if licensed | Custom DLA required | **NO-GO FOR PUBLIC RELEASE** (Default personal/research only) |
| **2. Bitstamp Commercial DLA** | [Bitstamp API Licensing](https://www.bitstamp.net/api/) | **PERMITTED** under Data License Agreement | **PERMITTED** | **PERMITTED** (Original derived works) | **WRITTEN ADDENDUM REQUIRED** | **WRITTEN ADDENDUM REQUIRED** | **PERMITTED** (Contractual retention) | **PERMITTED** | Yes ("Bitstamp Data") | Custom Enterprise quote | **RECOMMENDED PRIMARY (EXCHANGE SPOT)** |
| **3. CoinAPI Paid Commercial** | [CoinAPI Terms & Usage](https://www.coinapi.io/usage-policy) | **PERMITTED** (Customer-facing charts/tables) | **PERMITTED** | **PERMITTED** | **WRITTEN ADDENDUM REQUIRED** | **WRITTEN ADDENDUM REQUIRED** | Clarification required | **PERMITTED** | Yes (CoinAPI logo/link) | ~$250–$500/mo | **RECOMMENDED TURNKEY (MULTI-EXCHANGE)** |
| **4. CoinGecko Paid API (Analyst/Lite)** | [CoinGecko Terms (Art. 1043089972)](https://support.coingecko.com/articles/1043089972) | **PERMITTED** (With badge) | **PERMITTED** | **PERMITTED** | **PERMITTED** (Non-reconstructable) | **STRICTLY PROHIBITED** (Explicit AI ban) | **PERMITTED** (Active sub; delete on term) | **PERMITTED** | Yes ("Powered by CoinGecko") | ~$129–$499/mo | **VIABLE FOR DISPLAY ONLY (NO AI TRAINING)** |
| **5. Twelve Data Business** | [Twelve Data Business Pricing](https://twelvedata.com/pricing-business) | **PERMITTED** (Venture tier: client display) | **PERMITTED** | **PERMITTED** | **PERMITTED** | **WRITTEN ADDENDUM REQUIRED** | **PERMITTED** | **PERMITTED** | Yes (Twelve Data link) | ~$499/mo | **VIABLE SECONDARY (BUDGET DEPENDENT)** |
| **6. Kraken Public API** | [Kraken Terms of Service](https://www.kraken.com/legal) | **PROHIBITED** without written commercial redistribution agreement | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** (Automated scraping banned) | **PROHIBITED** | **PROHIBITED** | Yes if licensed | Institutional agreement | **BLOCKED WITHOUT ENTERPRISE CONTRACT** |
| **7. OKX Market Data API** | [OKX API Terms & User Agreement](https://www.okx.com/help/terms-of-service) | **PROHIBITED** for external commercial display | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** (Commercial AI extraction banned) | **PROHIBITED** | **PROHIBITED** | Yes if licensed | Bespoke institutional | **BLOCKED WITHOUT ENTERPRISE CONTRACT** |
| **8. Binance Vision Data Server** | [Binance Terms & Public Data Policy](https://data.binance.vision/) | **PROHIBITED** for commercial third-party display | **PROHIBITED** | **RESTRICTED** | **PROHIBITED** | **PROHIBITED** (Commercial use prohibited) | Academic only | **PROHIBITED** | Yes | Free for personal research | **BLOCKED FOR COMMERCIAL DEPLOYMENT** |
| **9. CoinPaprika Commercial API** | [CoinPaprika Terms of Service](https://coinpaprika.com/api/) | **PERMITTED** on paid plans | **PERMITTED** | **PERMITTED** | **WRITTEN CONFIRMATION REQUIRED** | **PROHIBITED** without custom tier | **PERMITTED** | **PERMITTED** | Yes ("Powered by CoinPaprika") | ~$99–$299/mo | **VIABLE ALTERNATIVE TO COINGECKO** |
| **10. GitHub (Speirsy11/crypto-dataset)** | [Repository Page (Binance Scrape)](https://github.com/Speirsy11/crypto-dataset) | **LEGALLY DEFECTIVE** (Uploader CC0 invalid) | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** | Non-commercial research only | Permitted | **PROHIBITED** (Violates Binance upstream IP) | None | Free | **STRICTLY DISQUALIFIED FOR PRODUCTION** |
| **11. Hugging Face (`humblefool06/BTC_USDT`)**| [Hugging Face Dataset Card (CC-BY-4.0)](https://huggingface.co/datasets/humblefool06) | Non-commercial benchmark only | Non-commercial | Offline research only | Research benchmark only | Permitted for offline training | Permitted | **COMMERCIALLY DEFECTIVE** | CC-BY attribution | Free | **RETAIN AS OFFLINE RESEARCH BENCHMARK ONLY** |

---

## 2. In-Depth Legal Analyses by Provider

### 2.1 Coinbase Exchange REST / WebSocket
- **Current Terms:** Section 2 of Coinbase Market Data Terms explicitly limits use to personal, internal research. Third-party web display, commercial redistribution, and AI/ML model training, tuning, or benchmarking without an executed written agreement constitute breach of contract.
- **Operational Reality:** BTCognitive's prototype uses Coinbase REST endpoints directly in development. This is permissible for private engineering, but serves as a strict P0 blocker for public domain hosting.

### 2.2 Bitstamp Commercial Data License Agreement (DLA)
- **Current Terms:** Bitstamp officially supports commercial integration via a Data License Agreement. Bitstamp's BTC/USD spot pair is an institutional gold standard with uninterrupted order book history dating back to 2011.
- **Contractual Coverage Needed:** Written agreement must explicitly cover:
  1. Public customer-facing candlestick chart display.
  2. Retention of historical OHLCV parquet files for rolling model validation.
  3. Computed econometric derived works (HAR realized variance, GBDT feature vectors, Donchian channels).
  4. Commercial subscription monetization.

### 2.3 CoinAPI Paid Tier
- **Current Terms:** Standard paid tiers explicitly permit embedding charts, tables, and calculated technical metrics into customer-facing web applications.
- **Restrictions:** Bulk raw-data redistribution (allowing end users to download CSV/JSON extracts of full history) is strictly prohibited. BTCognitive's read-only analysis model aligns with this restriction.

### 2.4 CoinGecko Commercial API
- **Current Terms:** Allows public web display and commercial software monetization with prominent "Powered by CoinGecko" badge and hyperlink.
- **Crucial Limitation:** CoinGecko explicitly prohibits AI/ML model training on its feeds, and its BTC pricing is an aggregated cross-exchange index rather than an executable exchange book. Suitable for chart display and indicator overlay, but model calibration must use an independent historical training set.

### 2.5 GitHub & Hugging Face "Free" Datasets (The Chain of Title Trap)
- **Legal Principle:** A third-party uploader cannot convey legal rights they do not possess (*nemo dat quod non habet*). Scraping Binance, Coinbase, or Kraken public endpoints and uploading them to GitHub under a CC0 or MIT license does not extinguish the exchange's binding contractual and intellectual property restrictions.
- **Governance Mandate:** Never use scraped public GitHub repositories as the legal market data backbone of a public commercial product.

---

## 3. Recommended Acquisition Strategy (No Vendor Outreach Performed)

1. **Phase 1 (Immediate / Deterministic QA):** Retain current deterministic QA fixtures for all regression testing, UI development, and isolated CI runs. Zero live vendor calls required.
2. **Phase 2 (Pre-Launch Commercial Licensing):** When commercial budget is authorized, execute a Data License Agreement with **Bitstamp** (for pure BTC/USD exchange order flow) or a commercial subscription with **CoinAPI** (for turnkey multi-exchange feeds).
3. **Phase 3 (Display Decoupling):** If CoinGecko is utilized for UI charting, ensure model training is strictly ring-fenced to licensed historical institutional archives.

