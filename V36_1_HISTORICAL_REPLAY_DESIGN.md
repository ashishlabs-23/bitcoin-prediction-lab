# BTCognitive V36.1 — Historical Replay Design

## Status: design only

No replay code was implemented or run. The verified Bitstamp snapshot is stale for a current-market decision, and the existing tournament route rejects it before invoking the analysis engine. Do not weaken current freshness policy. The replay needs a separate explicit `HISTORICAL_REPLAY` mode, review, and passing acceptance tests before any engine execution.

## Existing enforcement gaps

- `api/routes_tournament.py` validates submitted candle input and returns from the stale-data branch before calling the analysis function. This is correct for current-market analysis; it prevents exercising the engine with stale input.
- The untracked `engine/regime_strategy_tournament.py` validation/freshness helpers use system time when `as_of` is omitted; internal analysis timestamps/freshness also need explicit replay propagation.
- Downstream services may consult current-time or persistence state. The offline design must trace all calls before implementation and prevent fallback to providers, wall-clock-derived features, or writeable ledgers.
- The 1h snapshot does not contain 15m decision bars, 1m execution paths, order-book events, or aligned derivatives. The replay can only exercise compatible hourly OHLCV behavior; trade outcome and microstructure services must return `DATA_UNAVAILABLE`.

## Proposed request/result contract

Request fields (explicit, no default to wall clock):

```json
{
  "mode": "HISTORICAL_REPLAY",
  "symbol": "BTC/USD",
  "source_id": "bitstamp_local_snapshot",
  "snapshot_sha256": "d64cd2591b4cc5c5a6328785b1722ec5f8e01b78f30dee7f1dc7dff583e7fc54",
  "as_of_timestamp": "2026-11-03T15:00:00Z",
  "execution_authorization": false
}
```

`as_of_timestamp` is the latest eligible closed-candle availability/close timestamp from the verified snapshot; it must be rederived and verified against the file at runtime, not trusted as caller input. The supplied date is the inspected latest close, not current time. The replay is `HISTORICAL` and `STALE_FOR_CURRENT_MARKET`; a replay timestamp never makes old data fresh. The response carries the source/hash, data status, freshness status, analysis timestamp, feature availability, model identity, and per-feature failure/abstention reasons. Authorization is hard-coded false by this mode.

## Required cutoff and isolation design

1. Load only the exact allowlisted local Parquet path. Recompute SHA-256 and compare with the stored provenance manifest and request contract before parsing.
2. No HTTP client/provider adapter, exchange request, alternate cache, current quote, or environment-dependent source is reachable in this mode. Network access should be denied by the replay test harness as defense in depth.
3. Use timezone-aware UTC timestamps. Define candle `timestamp` as event/open time and `available_time` as the first time the closed bar can be used. Filter source rows by `available_time <= as_of_timestamp` before feature construction.
4. Require the caller to provide `as_of_timestamp`. Do not call `datetime.now()`, `date.today()`, or use system time for any replay feature, regime, label, freshness override, data quality, or serialization field. Wall clock may be recorded only as non-analytical audit metadata if the frozen audit policy allows it.
5. Propagate the same `as_of_timestamp` through route validation, engine validation, feature computation, regime evaluation, risk gates, response serialization, and UI display. No downstream helper may silently choose its own cutoff.
6. Preserve current-mode validation unchanged. Historical mode marks stale status; it does not bypass candle integrity, source, hash, cadence, or causal cutoff validation.
7. Disable writeable persistence dependencies through explicit interfaces or read-only handles. Fail if a called function attempts to write to the prospective ledger, market-memory DB, FeatureStore, forecast observatory, risk budget, experiment/trial ledgers, or manifests.
8. Every feature declares minimum history, cadence, required columns, and `available_time` semantics. Unsupported feature inputs produce `DATA_UNAVAILABLE`; no reindex fill, neutral default, synthetic candle, or cross-cadence interpolation.
9. Keep an execution authorization invariant in both response and downstream decision object: `OFF`. Do not expose order placement, broker, exchange-private API, or live-position mutation from the replay route.
10. Frontend renders the historical/stale badges from backend status and displays the same input hash/time. Do not render a replay as a fresh current-market recommendation.

## Acceptance criteria before any engine run

- Offline path reads exactly one immutable local snapshot; SHA-256 equals `d64cd2591b4cc5c5a6328785b1722ec5f8e01b78f30dee7f1dc7dff583e7fc54`.
- A missing or mismatched hash fails with a provenance error; it never falls back to another provider.
- Explicit historical as-of is mandatory; omitting it fails validation.
- A sentinel row with `available_time > as_of_timestamp` cannot affect any feature, regime, candidate, risk output, or response hash.
- Changing machine wall-clock time leaves all analytical output and cutoff behavior unchanged.
- Current/live mode retains its existing freshness rejection for this stale snapshot.
- Replay result states `data_status=HISTORICAL`, `freshness_status=STALE_FOR_CURRENT_MARKET`, `execution_authorization=OFF`, and exact source hash/time.
- Unsupported 15m/1m/L2/funding/OI/liquidation features return `DATA_UNAVAILABLE` with reason; they produce no values.
- Provider calls, order submission, private API access, and all persistent writes are blocked and verified by mocks/denylist/unchanged pre/post protected hashes.
- Invalid/missing/duplicate candles, OHLC errors, incomplete candle, exception/missing model output, and invalid serialization fail explicitly with established error codes.
- Tests establish identical replay outputs for repeated calls and no changes to protected ledgers, databases, datasets, or manifests.
- Design review checks every reachable engine dependency and UI value origin before the first replay execution.

## Out of scope

This design does not authorize full engine invocation, new live freshness behavior, data downloads, model training, calibration, prospective-ledger writes, trade simulation on hourly OHLCV, or current-market recommendations. Replay is retrospective development evidence, not confirmatory prospective validation.
