# Current market-data flow — verified repository inventory

## Acquisition and display

1. `web/app.js` implements `useCoinbaseFeed`. It directly requests Coinbase's public BTC-USD candles from the browser (`api.exchange.coinbase.com/products/BTC-USD/candles`) and opens a Coinbase WebSocket. This exposes raw candles in browser-network traffic and bypasses server-side provider-key and rights gating.
2. The same hook has a backend fallback: `/api/market/candles?symbol=BTCUSDT&interval=...`. This is a material pair/venue ambiguity: `BTCUSDT` must never be silently labelled or treated as `BTCUSD`.
3. `api/routes_market.py`, `api/http_client.py`, `api/market_drivers.py`, and `api/market_monitor_routes.py` acquire/normalize market observations from configured public-provider clients. `api/market_monitor_routes.py` supplies dashboard, candles and forecast endpoints.
4. `data/raw/ohlcv.parquet` and its backups are protected research artifacts. V2/V3 versioned Coinbase acquisitions live under `data/research/`; V3 remains `ACQUIRED_WITH_REVIEW_REQUIRED`, with 42,237 rows and 13 missing hourly candles. They were not modified by this preflight.
5. `web/app.js` renders the data using TradingView Lightweight Charts, computes EMA/Bollinger/RSI/ATR/ADX in the client, and sends chart context to Analyse/tournament workflows. `api/routes_tournament.py` can also accept client-submitted candle arrays; it is not a rights-gated public candle-delivery design.
6. `api/market_monitor_routes.py` serves the research/forecast contract. `engine/forecast_engine_15m.py` is the direct `/api/forecast/latest` contract. `OFFLINE_RESEARCH_ONLY` and `NO_GO_NO_VALIDATED_EDGE` restrict model authorization/live-capital status; they do not grant data-display rights.

## User-visible exposure audit

- Chart data is exposed through direct browser requests and backend candle/dashboard responses.
- No raw-candle download control was located. Paper-trade CSV/JSON export exists in `web/app.js`; it is separate from candle export but must remain separate.
- Any browser can inspect direct provider responses, so treating visual-only chart display as non-redistribution would be unsafe without provider confirmation.
- The chart label currently identifies Coinbase BTC/USD, while fallback code references BTCUSDT. This must be corrected via explicit source/venue identity, not a UI-only rename.

## Configuration and operations

- Backend: FastAPI (`api/server.py`); frontend bundle: `web/app.js`; chart dependency: Lightweight Charts script from unpkg in `web/index.html`.
- Current CI workflow only runs `tests/test_market_drivers.py` and `tests/test_market_monitor_routes.py`.
- Docker/Fly/Render artifacts exist. No provider licence configuration/approval record was located.
- No broker order route or exchange-account trading integration was found. Simulation/journal paths remain isolated non-MVP functionality.

## Required boundary before any provider selection

Disable direct browser provider acquisition in favour of a server-side, provider-neutral adapter **only after** a written data licence is selected. The adapter must return data with source identity and rights status; it must refuse public delivery unless a provider-specific release record is affirmative. Never fall back across pairs, venues, or providers silently.
