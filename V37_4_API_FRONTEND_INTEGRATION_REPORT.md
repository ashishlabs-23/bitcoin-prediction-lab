# BTCognitive V37.4 — API and Frontend Integration Report

**Disposition:** `NOT_VERIFIED` for a real feed-to-API-to-frontend path.

## Existing contracts preserved

The route audit identified existing aliases in [api/market_monitor_routes.py](./api/market_monitor_routes.py) for health/readiness, dashboard, latest market/prediction data, and candles. [api/server.py](./api/server.py) registers `market_monitor_router` before legacy overlapping routes; preserve this ordering and all aliases. Forecast/terminal and price-direction endpoints are distinct contracts and must not be merged.

The active frontend entry is [web/index.html](./web/index.html), which loads [web/app.js](./web/app.js). Existing consumers include market health/latest, forecast/latest, terminal live status, the Coinbase candle hook/chart, ticker, and AI risk outlook. The `web_src` client/views are not the active entry path.

## Findings

- Health status can be `ok` while market observations remain `FETCH_ON_REQUEST`; health is not live-data freshness.
- Current candle state includes `historyFreshness`, but this is not consistently returned/consumed. A stale or unavailable chart state can appear as loading.
- Ticker source labeling can identify Coinbase when the displayed value is not source-backed by an active Coinbase observation.
- Missing forecast model identity/direction can be inferred in the UI instead of being displayed as unavailable/contract-invalid.
- Existing backend unavailable responses are preferable to synthetic price/candle fallbacks and should be retained.

## Actual live smoke versus application API

The public WebSocket smoke appears in [V37_4_LIVE_INGESTION_REPORT.md](./V37_4_LIVE_INGESTION_REPORT.md). It received three Bitstamp trades, but their interpreted event times were about 226 seconds behind receive time. These trades were not made available to FastAPI or persisted.

No actual application API sample containing those observed Bitstamp trades was produced. No FastAPI lifecycle was started against the live feed, and no existing frontend chart was shown rendering the captured trades. The browser shared with this session is a `file://` page, not evidence of local FastAPI integration.

## Route-level status

| Surface | Existing behavior/evidence | V37.4 status |
|---|---|---|
| `/health`, `/api/health` | Service health can be OK while feed is fetch-on-request/unavailable. | `NOT_LIVE_FEED_EVIDENCE` |
| Dashboard/latest market | Existing source-backed or explicit unavailable response. | `NO_BITSTAMP_STREAM_HANDOFF` |
| `/market/candles`, `/api/market/candles` | Existing route consumed by the chart; freshness propagation is incomplete. | `NO_REAL_STREAM_CANDLES` |
| Forecast/terminal routes | Existing model-authority and unavailable contracts remain separate. | `NO_NEW_ENGINE_INPUT` |
| Frontend chart/ticker | Existing active UI consumes API and Coinbase feed paths. | `NO_REAL_BITSTAMP_OBSERVATION_RENDERED` |

## Engine/data-status mapping

Bitstamp trades alone can supply spot trade prints and, after a trusted candle builder exists, per-venue OHLCV. They do not supply a synchronized L2 book, funding/open interest, derivatives, sentiment, or the long historical windows required by HAR and some regime/setup engines. Each unsupported feature must remain `DATA_UNAVAILABLE` or its existing precise status; no engine should derive an observed book/funding/regime from a trade event.

No code changes were made to API routes or frontend in this run. The required next integration is additive: expose the event source, event/receive times, latest completed/provisional candles, freshness, gaps, recovery status, and reason through existing compatible routes; then carry that response into the existing active chart/ticker.
