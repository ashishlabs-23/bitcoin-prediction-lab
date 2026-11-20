# Multi-Provider Market Data License Matrix (V32.61)

**Date of Legal Research:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Operational Invariant:** Zero vendor outreach sent (no sales calls, emails, or contact submissions). All findings are derived strictly from authoritative published legal documentation, Terms of Service, and developer API policies.  
**Purpose:** Formally catalog and compare market data candidates for a public, TradingView-like online charting and research analytics application.

---

## 1. Comprehensive Comparative License Matrix

| Provider / Feed | Primary Terms URL | Date Accessed / Verified | Minimum Plan for Commercial Display | Public Customer-Facing Chart Display | Commercial Monetization Permitted | AI/ML Model Training Allowed | AI/ML Live Inference Allowed | Server Caching & Retention | Mandatory Attribution | Rate Limits & Intraday Granularity | Unresolved Questions / Blockers |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **1. Bitstamp** | [Bitstamp API Licensing](https://www.bitstamp.net/api/) | 29 Oct 2026 | Commercial Data License Agreement (DLA) | **YES** (Under signed DLA) | **YES** | **YES** (Must be scheduled in DLA) | **YES** (Original derived works) | **YES** (Per contractual retention) | "Market Data provided by Bitstamp" | 60s, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d. Max 1,000 candles/req. | Exact bespoke DLA pricing; timeline for contract execution. |
| **2. CoinGecko** | [CoinGecko Terms](https://support.coingecko.com/articles/1043089972) & [API Terms](https://www.coingecko.com/en/api_terms) | 29 Oct 2026 | Paid Self-Serve (Analyst / Lite ~$129–$499/mo) | **YES** (With badge/link) | **YES** | **STRICTLY PROHIBITED** (Explicit AI ban) | **YES** (Non-reconstructable outputs) | **LIMITED** (Active subscription only; delete on termination) | Prominent "Powered by CoinGecko" badge + active hyperlink | 1m/5m history limited on self-serve; automatic granularity (1d=5m, 90d=1h). 500–1000 calls/min. | Cannot be used to train/validate AI models. Granularity beyond 1 day is restricted. |
| **3. CoinPaprika** | [CoinPaprika Licensing](https://coinpaprika.com/api/licensing) | 29 Oct 2026 | Enterprise Tier (Standard paid is internal only) | **YES** (Only under Enterprise) | **YES** | **UNRESOLVED** (Requires contract clause) | **YES** (Under Enterprise redistribution) | **YES** (Contractual) | "Powered by CoinPaprika" | Documented frequent refreshes; custom limits on Enterprise. | Standard paid plans do not allow customer-facing redistribution. Enterprise quote required. |
| **4. CoinAPI** | [CoinAPI Usage Policy](https://www.coinapi.io/usage-policy) & [Licence](https://www.coinapi.io/api-licence-agreement) | 29 Oct 2026 | Commercial Paid Tier (~$250–$500/mo) | **CONFLICTING** (Blog says yes, legal terms require written agreement) | **YES** (With executed agreement) | **UNRESOLVED** (Written addendum needed) | **YES** (Derived analytics) | **RESTRICTED** (Bulk data export banned) | "Powered by CoinAPI" logo | High rate limits; normalized multi-exchange order books and OHLCV. | Contradiction between Nov 2025 marketing blog and Nov 2024 binding legal terms. |
| **5. CryptoCompare / CCData** | [CCData API Licence](https://www.cryptocompare.com/api-licence-agreement) | 29 Oct 2026 | Custom Enterprise (Standard terms are internal-use only) | **PROHIBITED** without written exception | **NO** (Without enterprise contract) | **PROHIBITED** without addendum | **PROHIBITED** without addendum | **PROHIBITED** | Required if licensed | Tiered API credits. | Standard terms explicitly prohibit public display. |
| **6. Binance Vision** | [Binance Public Data Terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md) | 29 Oct 2026 | Enterprise Agreement (Vision is CC BY-NC-SA 4.0) | **PROHIBITED** for commercial SaaS | **PROHIBITED** | **PROHIBITED** for commercial models | **PROHIBITED** | Research only | Mandatory CC BY-NC-SA | Daily/Monthly archive dumps in CSV/Parquet. | Terms explicitly exclude commercial use; GitHub issue #478 confirmed no commercial exception. |
| **7. Coinbase Exchange** | [Coinbase Market Data Terms](https://www.coinbase.com/legal/market_data) | 29 Oct 2026 | Commercial Redistribution License | **PROHIBITED** without prior express written consent | **PROHIBITED** under default terms | **PROHIBITED** (Explicit AI/ML restriction) | **PROHIBITED** without written consent | Internal dev only | Mandatory if licensed | REST limits apply (300 candles/req). | Default terms restrict use to personal/internal research. Public product launch blocked. |
| **8. Kraken Public API** | [Kraken API Guide](https://docs-legacy.kraken.com/api/docs/guides/global-intro/) | 29 Oct 2026 | Commercial Agreement | **RESTRICTED** (Non-personal commercial use requires permission) | **RESTRICTED** | **PROHIBITED** without agreement | **PROHIBITED** without agreement | **RESTRICTED** | Mandatory | Public rate counters. | Prior written permission required for non-personal commercial use. |
| **9. Community Scrapes (GitHub/Hugging Face)** | Various (e.g. `Speirsy11`, `humblefool06`) | 29 Oct 2026 | None (Non-commercial research only) | **LEGALLY VOID** (Chain of title failure) | **PROHIBITED** | Permitted for offline bench only | Permitted for offline bench only | Permitted | N/A | Static frozen files; no live updates. | Scrapers cannot convey rights they do not possess. CC0/MIT tags cannot override upstream exchange terms. |

---

## 2. In-Depth Operational Analysis of Top Candidates

### 2.1 Bitstamp Commercial Data License Agreement (Rank 1: Primary Choice)
- **Data Fidelity:** Pure, single-venue BTC/USD exchange order books and trades dating back to 2011. Eliminates synthetic cross-venue price distortions.
- **Intraday Breadth:** Native support for 1m, 3m, 5m, 15m, 1h, and 1d candles. Matches BTCognitive's exact UI timeframe selector.
- **Contractual Path:** Must execute a signed Data License Agreement with Bitstamp Partners. The agreement must explicitly cover:
  1. Public customer-facing chart display (TradingView Lightweight Charts).
  2. Server-side caching and append-only Parquet storage.
  3. Mathematical derived works (conformal volatility envelopes, HAR-RS-DOW realized variance).
  4. AI/ML model inference and offline research re-training.

### 2.2 CoinGecko Paid API (Rank 2: Display-Only Alternative)
- **Data Fidelity:** Volume-weighted multi-exchange price index. Does not reflect a specific executable order book.
- **AI/ML Prohibition:** **CoinGecko Terms of Service explicitly prohibit using its data for AI/ML training, tuning, or benchmarking.**
- **Architectural Consequence:** If CoinGecko is utilized, all AI models (HAR-RS-DOW, GBDT, conformal risk engines) must be completely decoupled and trained on a separate historical dataset (such as an institutional archive). CoinGecko can ONLY serve as a visual price feed for the chart widget.
- **Intraday History Limitation:** CoinGecko's market-chart endpoint automatically degrades resolution over time (5m for 1 day, 1h for 1–90 days, daily after 90 days). Extended high-resolution minute history requires Enterprise.

---

## 3. Disqualification Decisions

1. **Coinbase Default API:** Disqualified for public launch due to Aug 2026 Terms of Service Section 2 (restricts default access to personal/research).
2. **Binance Vision / Scraped GitHub Repositories:** Disqualified due to CC BY-NC-SA 4.0 non-commercial restrictions and chain-of-title defects (*nemo dat quod non habet*).
3. **CryptoDataDownload:** Disqualified due to explicit non-commercial terms.

---

## 4. Current Milestone Verdict
**RELEASE STATUS: `NO-GO (BLOCKED_BY_DATA_RIGHTS)`**  
Public customer-facing deployment remains strictly blocked until a written commercial Data License Agreement is executed with Bitstamp or CoinAPI.

