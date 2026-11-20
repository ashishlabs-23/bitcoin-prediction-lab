# BTCognitive V32.68 — Provider Written Licensing Questions & Response Register

**Document Date:** 30 October 2026  
**Auditor:** BTCognitive Legal & Technical Governance Subsystem  
**Milestone:** V32.68 — Core Workflow Verification & Provider Delta  
**Purpose:** Formal, binding written questionnaire required before signing commercial agreements or activating external provider feeds.  

---

## 1. Mandatory 10-Point Questionnaire for Shortlisted Providers

The following 10 binding questions must be submitted to vendor legal/licensing representatives for any shortlisted provider candidate:

1. **Public End-User Web Display:**
   *Question:* Does our subscription expressly grant the right to display live and historical BTC/USD OHLCV candlestick charts to both unauthenticated public visitors and authenticated users in a browser application?
2. **Interactive UI Tooltips & Granularities:**
   *Question:* Does interactive chart interaction (hovering crosshairs displaying open/high/low/close/volume per bar, zoom, pan, and client-selected intervals) qualify as permitted display, or is it legally classified as "Redistribution"?
3. **Commercial Monetization Model:**
   *Question:* Is commercial exploitation permitted, including offering paid user subscriptions, displaying advertisements, sponsorships, and providing a free tier?
4. **Derived Mathematical Calculations & Technical Indicators:**
   *Question:* Are we authorized to calculate, transform, and publicly display derived mathematical indicators (EMA 20/50, Bollinger Bands 20,2, RSI-14, ATR-14, realized volatility, regime classifications, and uncertainty envelopes) computed from your OHLCV data?
5. **AI/ML Validation, Calibration, and Training Separation:**
   *Question:* Does your license permit:
   - (a) Internal offline model validation, backtesting, and loss evaluation?
   - (b) Live inference scoring for risk envelopes?
   - (c) Internal parameter optimization and model training?
   *(Please state permissions separately for validation vs training).*
6. **Server-Side Caching, Retention, and Archival:**
   *Question:* What are the exact caching rules, permitted database retention periods, and maximum time-to-live (TTL)? What are the specific data purge/deletion requirements upon contract termination?
7. **Downstream Export, Screenshots, and Derivative Boundaries:**
   *Question:* Does user generation of chart screenshots, social sharing of images, or watchlist/alert configuration trigger any downstream redistribution restrictions or additional licensing fees?
8. **Product & Instrument Basis Integrity:**
   *Question:* What is the exact instrument and price basis provided by the endpoint: is it venue-specific spot orderbook trades (e.g., Bitstamp BTC/USD), volume-weighted global benchmark across multiple exchanges, or synthetic index pricing?
9. **Technical Specifications & Service Level Agreements:**
   *Question:* What are the supported intervals (1m, 5m, 15m, 1h, 4h, 1d), historical lookback depth, rate limits (requests per minute and daily quota), endpoint latency, REST vs WebSocket availability, and uptime SLA guarantee?
10. **Jurisdictional & Cross-Border Usage Rights:**
    *Question:* Are there any geographic restrictions on querying your API from servers located in India, the US, or the EU, and displaying the resulting charts to end users globally?

---

## 2. Shortlisted Provider Response Status Register

| Shortlisted Provider | Target Plan / Pathway | Inquiries Dispatched | Written Response Status | Notes & Blockers |
| :--- | :--- | :--- | :--- | :--- |
| **Bitstamp Europe S.A.** | Commercial Data License Agreement (DLA) | **PENDING MANAGEMENT OUTREACH** | **NO RESPONSE ON FILE (PENDING)** | Bilateral DLA template reviewed; counter-signed contract required. |
| **CoinGecko** | Paid API (Starter / Pro Plan) | **PENDING MANAGEMENT OUTREACH** | **NO RESPONSE ON FILE (PENDING)** | FAQ confirms public display with attribution; written confirmation required for Section 5.3 AI validation rider. |
| **CoinPaprika** | Enterprise Custom Contract | **PENDING MANAGEMENT OUTREACH** | **NO RESPONSE ON FILE (PENDING)** | Enterprise page advertises redistribution; contract terms not yet negotiated. |
| **Twelve Data** | Business Plan (Venture Tier) | **PENDING MANAGEMENT OUTREACH** | **NO RESPONSE ON FILE (PENDING)** | Indian/international exchange licensing rights require written clarification. |

> [!IMPORTANT]
> **Strict Governance Invariant:** In accordance with the BTCognitive Epistemic Prime Directive, zero responses have been fabricated. Provider written confirmation remains strictly **PENDING OUTREACH**. Staging with external network calls remains **BLOCKED** until counter-signed agreements are secured.

