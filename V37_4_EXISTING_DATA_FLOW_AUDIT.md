# BTCognitive V37.4 — Existing Data-Flow Audit

**Review date:** 2026-11-04  
**Disposition:** Read-only architecture audit. No existing engine or route was replaced.

## Current file-level flow

```text
Bitstamp REST OHLC
  -> engine/market_data_adapters/bitstamp.py: BitstampAdapter
  -> engine/market_data_adapters/factory.py: opt-in provider selection
  -> engine/bitstamp_market_data_service.py: TTL cache, validation, source-separated Parquet persistence
  -> API routes / frontend consumers (not a continuous trade feed)

Coinbase Exchange WebSocket
  -> engine/coinbase_l2_collector.py: level2_batch, heartbeat, matches
  -> engine/l2_microstructure_features.py: OrderBookTracker
  -> engine/l2_event_recorder.py: optional raw L2 JSONL record/replay
  -> Coinbase-specific L2/microstructure capability

HTTP request path
  -> api/server.py: FastAPI routers (market_monitor_router registered first)
  -> api/market_monitor_routes.py: dashboard/latest/candle response contracts
  -> web/index.html -> web/app.js API consumer, chart, ticker, and risk views

Separate existing mechanism
  -> api/candle_manager.py: process_tick OHLCV aggregation coupled to inference
  -> engine/prospective_worker.py: Coinbase hourly historical sync to a configured Parquet path
```

## Reusable components and integration gaps

- Reuse the existing Bitstamp REST adapter and source-separated service only for same-venue recovery after current documentation and rights are verified. The historical worker is not an ingestion path for this milestone because it writes its configured Parquet target.
- Reuse the Coinbase L2 collector/recorder only for its existing Coinbase L2 capability. It is not a Bitstamp trade adapter and Coinbase terms prohibit unapproved AI/ML training/validation.
- `engine/market_data_feed.py` already defines a general `MarketDataObservation` carrying source/instrument and event/receive time concepts. This should be reconciled with any exchange-specific event adapter rather than creating a second canonical event schema.
- `api/candle_manager.py` is not a safe drop-in ingestion aggregator: its close/inference coupling emits no explicit missing interval, and its out-of-order guard can accept an older tick inside the active interval.
- Existing provider adapters normalize candles, not a continuous trade stream. The event/candle/API/frontend boundary is therefore not currently demonstrated end-to-end.
- `engine/prospective_worker.py` has a failure-path concern: if every retry raises, the post-loop `data is None` check may reference an uninitialized local.
- `engine/market_data_adapters/bitstamp.py` has an exception-path concern: the reviewed path references `sys.platform` without an observed `sys` import.
- Provider normalization currently retains forming candles in some adapter responses despite a closed-candle provider contract. CoinGecko OHLC volume is encoded as `0.0` despite volume being unavailable; missing data is not distinguishable from observed zero volume.

## API/frontend and engine contract findings

API aliases and router order must remain intact. `/health` can report service health while market data is `FETCH_ON_REQUEST`; it is not proof of fresh data. The active page is [web/index.html](./web/index.html) loading [web/app.js](./web/app.js), not the separate `web_src` API/view modules.

Frontend gaps identified in the current flow:

- The ticker's Coinbase label can be shown without actual Coinbase source/status metadata.
- Candle freshness state is not consistently propagated to the chart; stale/unavailable may render as loading.
- Missing forecast metadata can be replaced with inferred model/direction labels.
- Preserve existing explicit `DATA_UNAVAILABLE` and fail-closed response contracts.

Existing engine contracts require different feeds and histories: one-minute OHLCV features; 1h OHLCV for 4h setup aggregation (84 hourly bars/21 complete 4h bars); 15m volatility requires 32 bars; hourly HAR features require 24/168/720-hour rolling inputs plus 24 future hourly returns for labels; L2 features require a synchronized book and 60/300/900-second windows; funding/OI and sentiment are not present in the Bitstamp trade stream.

Several current pipelines synthesize defaults/proxies when sources are absent: `engine/feature_pipeline.py` pads short history and supplies default features; `engine/point_in_time_features.py` derives OHLCV microstructure proxies and fills absent derivatives; `models/regime_detector.py` defaults missing values; `engine/market_state.py` reports hard-coded values as `VALID`. Those do not become observed market data when connected to a spot feed.

## Minimum safe integration plan

1. Use Bitstamp BTC/USD as the explicitly identified primary source, but retain event and receive timestamps separately and reject stale feed output from `ACTIVE` status.
2. Resolve and use the existing `MarketDataObservation` interface; do not make a new generic event schema.
3. Keep exchange event deduplication, candle aggregation, quality status, and provider identity source-specific; do not silently fill missing intervals or mix venues.
4. Reuse REST recovery only after official semantics and rights are confirmed; record recovery provenance separately and never alter protected historical datasets.
5. Add a truthful API handoff into existing monitor/candle routes; preserve all aliases and fail-closed model contracts.
6. Pass valid, complete, explicitly timed OHLCV to existing compatible engines; keep book/funding/sentiment/derivatives features unavailable until genuine sources exist.
7. Carry source, exchange/receive times, freshness, and quality state through the existing frontend chart and ticker without fallback labels.

No code changes were made in this milestone run; the live feed-to-application connection remains a blocker rather than a claimed implementation.
