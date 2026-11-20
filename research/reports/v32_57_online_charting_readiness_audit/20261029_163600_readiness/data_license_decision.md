# Market Data Licensing Decision Matrix & Policy (V32.57)

**Document ID:** DL-20261029-01  
**Scope:** Commercial, public-facing online market charting and AI analytics release gates.

---

## 1. Provider Rights Evaluation Matrix

| Licensing Scope Required | Coinbase Default (Aug 2026 Terms) | Required Written Enterprise Agreement | Commercial Provider Alternative (Kaiko / Polygon / TwelveData) |
| :--- | :--- | :--- | :--- |
| **Public Web Display of Candles** | **PROHIBITED** (personal/research only) | Requires express written consent | Granted under Commercial Display Tier |
| **Derived Technical Indicators** | **PROHIBITED** (Derived Works restriction) | Requires express written consent | Granted under Derived Works addendum |
| **AI/ML Model Training & Validation** | **PROHIBITED** (Explicit clause) | Requires AI/ML specific license clause | Permitted under institutional research license |
| **Historical Data Retention & Backtest** | Permitted for internal research only | Permitted across application cache/db | Permitted for historical store |
| **Real-Time Client Distribution (WS/SSE)**| **PROHIBITED** without consent | Requires WebSocket distribution rights | Standard API tier |
| **Commercial / Monetized Subscription** | **PROHIBITED** | Custom commercial pricing/royalty | Enterprise SaaS tier |

---

## 2. Gate Decision: BLOCKED

### Decision
Public staging or production release of BTCognitive using Coinbase REST/WebSocket market data is **BLOCKED**.

### Rationale
Coinbase terms explicitly demand written permission for third-party display and AI/ML evaluation. Deploying a public app without this written instrument introduces immediate operational, intellectual property, and compliance liability.

### Action Plan for 30-Day Milestone
1. Prepare formal inquiry package to Coinbase Enterprise Market Data team detailing:
   - Read-only web charting application (no broker integration, no trading execution).
   - Expected concurrent user volume (100–500 DAU for private beta).
   - Display of 1h BTC-USD candlesticks and derived risk bands.
   - Non-directional empirical volatility baselines (HAR-RS-DOW, Parkinson RV).
2. Parallel track: Benchmark Twelve Data and Polygon.io commercial APIs for pricing, latency, and explicit display terms.
3. During Phase 0/1 development, isolate QA using `deterministic_hourly_v1` fixtures; never deploy live feeds without signed terms.

