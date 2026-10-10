# Read-Only Market Data and Provenance Audit

**Scope:** Source-code and contract inspection only. No live market request was made.

## Finding

There is no verified live feed for the research instrument. The frozen instrument contract specifies Bitstamp BTC/USD spot, one-minute OHLCV, UTC interval-close Unix-second timestamps, and prohibits cross-exchange pooling. The local data-intake manifest describes a historical Bitstamp snapshot whose last bar is `2026-10-07T03:11:00Z`; that is historical data, not a fresh live feed.

The generic `fetch_live_binance_btc_price_async` returns a bare float and tries Binance Coin-M perpetual, Coinbase, Kraken, then Bybit. It does not establish Bitstamp venue provenance and can mix distinct instruments/venues. `fetch_binance_ticker_24h_async` also uses Binance/Bybit. `/market/latest` can use an unqualified cached close and stamps the response with request time rather than the source event time. The application exchange setting is Binance.

## Recommendation

For research-compatible live context, add a minimal public, read-only Bitstamp BTC/USD adapter; do not silently fall back to another exchange or cached/perpetual prices. Every successful response should identify venue, symbol, source, UTC event/bar time, retrieval time, and configured freshness threshold. Validate completed one-minute OHLCV bars for finite values, OHLC consistency, nonnegative volume, monotonic unique interval-close timestamps, and the allowed instrument. Reject stale or future-dated observations.

Use bounded request timeouts and explicit failure states:

- `DATA_UNAVAILABLE` for timeout/upstream absence;
- `STALE_DATA` when source time exceeds the declared freshness limit;
- `PROVENANCE_FAILURE` for wrong venue/symbol, invalid schema/values, or timestamp violations.

No credentials or order permissions are needed. Never pool venues, use trading endpoints, or substitute synthetic/sample/cached data when the source fails.

## Evidence inspected

- `research/entry_tp_sl/instrument_contract.json`
- `research/entry_tp_sl/data_intake_manifest.json`
- `api/http_client.py`
- `api/routes_market.py`
- `config.py`
