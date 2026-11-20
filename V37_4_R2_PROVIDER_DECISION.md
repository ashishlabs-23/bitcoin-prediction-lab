# V37.4 R2 — Alternative Provider Qualification

**Assessment date:** 2026-11-04  
**Scope:** Official CoinAPI and Gemini primary sources only. This is a technical and contract-language qualification, not legal advice or legal clearance. No provider API/WebSocket was called, no credential was used, and no account, subscription, or provider feed was activated. Coinbase remains excluded.

## Decision

| Provider | Decision | Summary |
|---|---|---|
| CoinAPI — `BITSTAMP_SPOT_BTC_USD` | **CONDITIONAL; not cleared to activate** | Official docs describe the requested symbol, live trade/book streams, and historical REST endpoints. But the public Customer Agreement limits use of the Services to “internal business purposes only,” incorporates an Acceptable Usage Policy that was not available for review, and makes the customer responsible for third-party data-source restrictions and licenses. The public material does not settle whether this individual, one-user local research use and this particular Bitstamp feed are covered. |
| Gemini — BTCUSD public market-data stream | **CONDITIONAL; closer textual fit, not cleared to activate** | The Market Data Agreement expressly includes “personal and/or internal use,” “general informational purposes,” and price/market analysis as Permitted Use, which appears to fit a strictly local, one-user, non-executing research app. Use remains subject to prohibited-use rules, fees, the applicable residence-specific User Agreement and API Agreement; market-data event-time semantics are not sufficiently specified for exchange-time claims. |

**Overall:** Treat both as research candidates only. Do not connect either provider until the gates below are documented and approved. This conclusion does not authorize redistribution, user-facing service, commercial use, product/benchmark creation, or trading/execution.

## CoinAPI

### Instrument, stream fields, identity, and sequencing

The official CoinAPI WebSocket V1 message examples use the exact identifier `BITSTAMP_SPOT_BTC_USD`. Its trade payload includes `symbol_id`, `sequence`, `time_exchange`, `time_coinapi`, `uuid`, `price`, `size`, and `taker_side`. CoinAPI defines:

- `time_exchange` as the trade time reported by the exchange.
- `time_coinapi` as the time CoinAPI first received the trade from the exchange.
- `sequence` as a number per `(type, symbol_id)`, valid only for the lifetime of the connection.
- `uuid` as CoinAPI’s unique trade identifier, a UUIDv4—not an exchange-provided trade identifier.

Therefore, the documented fields support distinguishing exchange-reported event time from provider receipt time, but the sequence cannot be treated as a durable cross-reconnect cursor. Preserve both timestamps and the provider UUID; do not treat `time_coinapi` as exchange execution time or `sequence` as a persistent trade ID. The example is not a live check that this instrument is currently active or subscribed.

The WebSocket documentation describes `trade`, `quote`, and L2 book feeds. A `hello`/`subscribe` request specifies data types and symbol filters; for exact matching the docs say to append `$` to the symbol filter. A WebSocket key is required. Public docs say WebSocket connections are limited by subscription plan; the plan’s actual entitlement and connection limit for this feed have not been verified.

### Historical REST coverage

The documented REST endpoints include:

- `GET /v1/trades/{symbol_id}/history`, returning transactions in ascending time order. Its docs describe hourly granularity for APITP data and automatic fallback to daily data for older records, with exact time-range filtering.
- `GET /v1/ohlcv/{symbol_id}/history`, which documents history by symbol and period and notes that historical OHLCV may be delayed by a few seconds.
- The symbol catalog documentation provides an active-symbol endpoint and a separate historical-symbol endpoint.

CoinAPI’s Bitstamp exchange product page claims historical records from 2011 and “every trade since exchange launch.” Those are provider claims, not independently verified coverage or a guarantee for this specific instrument, plan, or requested time range. No catalog, history, or market-data request was made under this task; present-day active status, earliest available `BITSTAMP_SPOT_BTC_USD` record, gaps, corrections, and retention are **unknown**.

### Credentials, subscription, and pricing facts

CoinAPI docs state that REST and WebSocket V1 support API-key authentication. The WebSocket guide requires a key in the subscription handshake. The Market Data API pricing page, accessed on the assessment date, lists Pay As You Go as metered with $25 free credits and REST/WebSocket access, and lists Startup at $79/month ($69/month annual) with 1,000 REST credits/day and 32 GiB/day Tier 1 data. The same page lists WebSocket V1 and historical/real-time data across displayed plans and describes Tier 1 as trade, quote, and order-book transfer. These are posted plan facts, not confirmation of current account eligibility, an order, instrument-level access, a particular Bitstamp feed’s usage classification, or total cost. No plan was selected.

### Binding terms and permitted use

The official **Customer Agreement** on CoinAPI’s legal page is effective 2025-08-18. Relevant terms include:

- **§1.2, Rights Granted:** a non-exclusive, non-transferable, revocable right to use the Services “for your internal business purposes only.”
- **§1.3, Applicability of Specific Terms:** service-specific terms may supplement the Customer Agreement and prevail for that Service where they conflict.
- **§2.1, Account Registration:** account registration is required to place orders, receive API keys, and manage access.
- **§2.3, Data Source:** the customer is “solely responsible” for use of external data sources, which “may be subject to restrictions of use and require additional license agreements with the third party.”
- **§4.2, Fair Usage:** Cloud Services usage is governed by CoinAPI’s Acceptable Usage Policy; §5.4 also requires customer data to comply with that policy and applicable law.

The public legal page refers to the Acceptable Usage Policy but the policy’s actual text and a stable public policy URL were not located in the official material reviewed. No public Market Data API service-specific license resolving the Bitstamp source/data rights was found. Consequently, the public Customer Agreement is not enough to conclude that an individual’s personal one-user local app is authorized: its express grant is for **internal business** use. The project’s internal research/risk-intelligence purpose may fit if actually operated as internal business use, but that is not established by the public wording alone. The exchange’s underlying data rights are a separate open issue under §2.3.

## Gemini

### BTCUSD public stream and event semantics

Gemini’s official WebSocket introduction documents the public endpoint as `wss://ws.gemini.com` and says public market-data streams are available without authentication. Its stream reference documents:

- Trade stream `{symbol}@trade`: `E` (event time, nanoseconds), `s` (symbol), `t` (trade ID), `p` (price), `q` (quantity), and `m` (whether the buyer is maker).
- Book ticker `{symbol}@bookTicker`: `u` (update ID), `E` (event time, nanoseconds), `s`, best bid/ask prices and quantities, plus optional last-trade price/size.
- L2 partial depth streams (`{symbol}@depth5`, `@depth10`, `@depth20`, including 100ms variants) and differential depth (`{symbol}@depth`, `@depth@100ms`). Differential updates include `U`/`u` update-ID bounds; the introduction describes an optional initial snapshot.

The stream docs label `E` only as **“Event time (nanoseconds)”**. They do not define whether it is the venue’s execution timestamp, feed-generation timestamp, or another event clock, nor define its clock source, precision guarantees, or latency relationship to local receipt. The trade ID and update IDs are documented as identifiers but their durability, uniqueness scope, and restart/replay semantics are not specified on these pages. Thus `E` must not be relabeled as exchange execution time without written provider clarification; local receipt time must be captured separately if used.

The streams are parameterized by `{symbol}`. Gemini’s symbol/minimums page references live symbols but its page states that the table loads directly from the API; no live catalog/API query was made. Accordingly, the exact stream spelling and current availability for `BTCUSD`/`btcusd` were not verified in this assessment.

### Binding Market Data Agreement and permitted use

Gemini’s official Market Data Agreement states that accessing or using Gemini Market Data binds the user to the Agreement, and that it is subject to the applicable User Agreement. Its **License** grants a non-exclusive, non-transferable, non-sublicensable, revocable license to receive, download, store, and copy data only for Permitted Use. Under **Permitted Use — Personal and Internal Use**, the allowed purposes are “(i) personal and/or internal use; (ii) general informational purposes; or (iii) analysis of prices and markets and financial products relating thereto,” in all cases excluding Prohibited Use.

This language is a substantially better textual fit for a strictly private, local, single-user research/market-intelligence app, provided use is genuinely personal/internal and non-prohibited. It is not a general redistribution or SaaS grant:

- **Prohibited Use** includes creating or using data for an investment/financial product or benchmark/index, and distributing, redistributing, disseminating, selling, reselling, licensing, or sublicensing Market Data except for authorized OEMS services.
- The Agreement says to contact Gemini for commercial-purpose use and to request a Redistribution Agreement for distribution or resale.
- OEMS redistribution requires a separate executed OEMS Service Provider Agreement and compliant subscriber agreements.
- The **Market Data Fees** clause makes access/use subject to Gemini’s Market Data Fee Schedule and allows the schedule to change. A fee amount for this specific use was not established from the reviewed Agreement page.

The applicable User Agreement depends on the user’s place of residence. The Agreement also cites the Gemini API Agreement among prohibited-use conditions. Neither the user’s contracting jurisdiction nor the applicable Market Data Fee Schedule was determined here. This report does not determine whether an app associated with a commercial product or business remains “personal and/or internal use.”

## Approval gates before any provider use

1. **Written scope/rights confirmation:** Have the appropriate legal owner review the exact current provider agreement(s), applicable residence/entity terms, Acceptable Usage Policy (CoinAPI), Gemini Market Data Fee Schedule, and any source-specific terms. Obtain written provider confirmation for the intended local, one-user research/market-intelligence use—especially CoinAPI’s internal-business limitation and underlying Bitstamp rights. Do not treat product pages or this assessment as legal clearance.
2. **No redistribution by default:** Keep raw provider data and derived/display outputs private to the authorized operator unless the provider expressly approves broader use in writing. Any external users, hosted dashboard, publication, customer access, or commercial use requires a separate rights determination first.
3. **Product and safety boundary:** Keep the integration research/risk-intelligence only. No order placement, brokerage/execution, live trading, or real-capital deployment. No use to create a prohibited financial product or benchmark.
4. **Instrument and plan verification:** Only after approval, verify the exact active symbol (`BITSTAMP_SPOT_BTC_USD` or Gemini’s exact BTCUSD symbol), required subscription/connection quotas, data-tier billing, historical start/gaps, and order-specific fees through authorized provider channels. Do not infer these from examples or generic marketing.
5. **Time/identity qualification before analytical use:** For CoinAPI, preserve exchange and provider timestamps separately and treat `sequence` as connection-scoped; validate UUID stability/deduplication behavior. For Gemini, obtain authoritative definitions for `E`, trade-ID and book-update-ID scope, and resynchronization behavior; until then record `E` only as an undocumented-semantics source event time and keep independent local receive timestamps. Validate live feed completeness and gaps before research use.

**Disposition:** No provider is cleared for activation by this report. Gemini is the better textual fit for the narrowly described personal/internal scenario, subject to all gates; CoinAPI remains conditional on both policy/contract clarification and explicit Bitstamp source-rights confirmation.

## Official primary sources reviewed

All sources below were accessed **2026-11-04**. Quoted terms above are from the identified official pages; plan and coverage statements are reported as provider-published claims, not independently tested facts.

### CoinAPI

1. **Market Data API overview and REST/WebSocket product scope:** https://www.coinapi.io/products/market-data-api/docs
2. **WebSocket V1 general subscription/authentication behavior:** https://www.coinapi.io/products/market-data-api/docs/websocket/general
3. **WebSocket V1 message schemas, including trade timestamps/sequence/UUID:** https://www.coinapi.io/products/market-data-api/docs/websocket/messages
4. **WebSocket V1 endpoints:** https://www.coinapi.io/products/market-data-api/docs/websocket/endpoints
5. **Authentication methods for REST and WS V1:** https://www.coinapi.io/products/market-data-api/docs/authentication
6. **REST historical trades:** https://www.coinapi.io/products/market-data-api/docs/rest-api/trades/trades/symbol_id/history/get
7. **REST historical OHLCV:** https://www.coinapi.io/products/market-data-api/docs/rest-api/ohlcv/ohlcv/symbol_id/history/get
8. **Active symbol catalog docs:** https://www.coinapi.io/products/market-data-api/docs/rest-api/metadata/symbols/exchange_id/active/get
9. **Historical symbol catalog docs:** https://www.coinapi.io/products/market-data-api/docs/rest-api/metadata/symbols/exchange_id/history/get
10. **Bitstamp exchange product page (provider coverage claims/example):** https://www.coinapi.io/products/market-data-api/exchanges/bitstamp
11. **Market Data API plans/pricing:** https://www.coinapi.io/products/market-data-api/pricing
12. **Customer Agreement (Effective Date 2025-08-18; §§1.2–1.3, 2.1–2.3, 4.2, 5.4):** https://www.coinapi.io/legal

### Gemini

1. **WebSocket introduction (endpoint and public-stream authentication statement):** https://developer.gemini.com/websocket/introduction
2. **WebSocket public stream schemas (trade, book ticker, depth):** https://developer.gemini.com/websocket/streams
3. **Symbols and minimums page (live table; not queried here):** https://developer.gemini.com/market-data/symbols-and-minimums
4. **Market Data Agreement (License, Market Data Fees, Permitted Use, Prohibited Use, redistribution):** https://www.gemini.com/legal/market-data-agreement
5. **User Agreement applicability by residence:** https://www.gemini.com/legal/user-agreement
6. **Gemini API Agreement (referenced by Market Data Agreement):** https://www.gemini.com/legal/api-agreement
