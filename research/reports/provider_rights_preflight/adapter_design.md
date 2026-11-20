# Provider-neutral candle adapter proposal — design only

## Non-goals

This proposal does not select, call, ingest, or activate any provider. It does not modify V2/V3 or protected parquet/ledgers. It does not add order execution.

## Interface

```python
class CandleProvider(Protocol):
    async def fetch_candles(
        self, request: CandleRequest
    ) -> CandleFetchResult: ...
```

`CandleRequest` has `canonical_instrument` (`BTC/USD`, not a string-normalized guess), `venue`, `market_type` (`SPOT`, `PERPETUAL`, `FUTURES`), `interval_seconds`, UTC `[start, end]`, and an explicit `rights_context_id`.

`Candle` returns `instrument`, `venue`, `market_type`, `base_currency`, `quote_currency`, `interval_seconds`, UTC `open_timestamp`, `open/high/low/close/volume`, `source_timestamp`, `fetched_at_utc`, `is_closed`, `provider`, `provider_dataset_revision`, and `raw_response_sha256`.

`CandleFetchResult` returns candles plus immutable diagnostics: `duplicate_timestamps`, `missing_bar_intervals`, `invalid_ohlcv_rows`, `nonfinite_rows`, `stale_age_seconds`, `partial_open_bar_count`, `request_id`, provider rate-limit metadata, and `rights_status`.

## Invariants

- `BTCUSDT` and `BTCUSD` differ by quote currency. Their venues and market types are never inferred from a display symbol.
- A chart series is one `(provider, venue, market_type, base, quote, interval)` identity. Cross-venue aggregation needs a separately versioned aggregation policy and its own label/provenance.
- Timestamps are UTC candle-open. `is_closed` is calculated from provider semantics plus fetch time; open bars are labelled `PARTIAL/OPEN`, not silently included in closed-bar analysis.
- Validate monotonic ordering, exact interval cadence, duplicates, finite values, nonnegative volume, and `low <= min(open, close) <= max(open, close) <= high`.
- Missing bars are diagnostics, never synthesized. Invalid rows are rejected with diagnostics, not repaired.
- Cache keys include provider, venue, market type, canonical instrument, interval, requested range, provider revision, and rights-context identifier.

## Rights gate and isolated staging

`ProviderRightsRegistry` is a server-side configuration/document record, not a client flag. Default is `BLOCKED`. A provider can serve public routes only when an approved, dated agreement reference explicitly covers the requested display and analytics use. Model pipeline access has an independent `model_use` scope and stays blocked unless expressly cleared.

Before approval, a bounded probe may write only to a new `data/staging/provider_probes/<run-id>/` directory (or OS temporary directory). It uses one finite request range, provider-published pacing, no persistent collector, redacted headers, archived raw response hashes, request metadata, normalized sample, diagnostics and manifest. It must not feed charts, forecasts, caches, V2/V3, or protected files. Compare only against an independently rights-cleared source and report discrepancies.
