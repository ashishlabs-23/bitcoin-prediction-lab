# BTCognitive V37.4-R1 — Integration Test Report

**Assessment date:** 2026-11-04  
**Integration disposition:** Local deterministic path verified; provider/live path not authorized or verified

## Test evidence classes

| Evidence class | Result | What was demonstrated |
|---|---|---|
| Deterministic unit tests | Passed except one pre-existing protected-hash assertion in the combined suite | Trade timestamp parsing, deduplication, event-time OHLCV aggregation, gaps, stale state, reconnection behavior, lifecycle gate, duplicate-start block, shutdown timeout, and invalid/future-time fail-closed handling. |
| Running FastAPI application integration | Passed with a local test fixture | The repository's `api.server.app` and actual lifespan were started locally with a deterministic feed override. Fixture observations flowed through the existing parser, `MarketDataObservation`, candle manager, market candle route, and response normalization. |
| Local browser integration | Passed for the 1-minute chart; route behavior had an unrelated backend caveat | The existing web application was loaded from the local FastAPI static mount. Selecting the existing 1m button made the existing chart consume the local API response and display the fixture-only label. Existing `#/terminal`, `#/research`, and `#/journal` views rendered. |
| Actual exchange smoke test in this task | Not run | No Bitstamp/CoinAPI/Gemini provider was contacted. The previous R1 smoke remains a historical record with unresolved clock skew and rights. |
| Sustained live-feed soak in this task | Not run | Historic JSON records a completed-duration aggregate, but raw per-message evidence is absent and freshness is unqualified. |

## Running FastAPI local fixture check

The manager launched the actual `api.server.app` on loopback (`127.0.0.1:8765`) with its real FastAPI lifespan and router/static mounts. The injected `LocalFixtureFeed` was a test-only subclass. In this temporary process, scientific-readiness dependencies and the network permission function were mocked to let the fixture pass the normal lifespan gate; the fixture's `start()` method did not invoke the provider transport. The fixture generated deterministic Bitstamp-shaped trade messages and called the existing parser/ingestion-only path. It did not persist data.

The browser's request to `/api/market/candles?symbol=BTC-USD&interval=1m&limit=500` returned:

- HTTP `200`
- `status=ACTIVE`, `freshness_status=FRESH`
- `source=bitstamp`, `data_origin=TEST_FIXTURE_ONLY`
- 23 fixture candles at the sampled response (the local fixture refreshed the latest closed minute)
- `analysis.status=UNVALIDATED`, `engine_invoked=true` for the deterministic 20+ closed consecutive candle tail
- Event timestamp `2026-11-04T17:12:59.900000Z`
- Receipt timestamp `2026-11-04T17:13:48.560739Z`

The 48.660739-second event/receipt difference is solely from the local fixture and the unsynchronized host clock; it is **not** provider latency evidence.

In the existing browser chart, selecting `#tf-btn-1m` displayed:

- `BTC / USD · LOCAL TEST FIXTURE ONLY · NOT MARKET DATA`
- Fixture price `$68,031.00`
- `ACTIVE`
- `Local test fixture timestamp:`
- Chart diagnostic `BTC-USD · 1m · Feed: bitstamp · FRESH`

No live trade, market quote, or forecast accuracy result is implied by these values.

### Existing route navigation

Browser hash navigation reached existing views:

- `#/terminal` — Smart Entry Simulator / Strategy Tournament view rendered.
- `#/research` — Historical Research Results / Scientific Evidence view rendered.
- `#/journal` — Manual Trade Journal view rendered.

The journal view showed `window.api.fetchJournalTrades is not a function` in this local test setup. The browser also logged unrelated unavailable forecast/smart-entry requests where the fixture app supplied no production client or active tournament analysis. These errors are recorded rather than attributed to R1 or hidden; route rendering does not establish that unrelated backend features are operational in this test harness. No frontend route or feature family was removed.

The temporary server was stopped after the browser check. A preliminary malformed fixture attempt was rejected by the parser (`Extra data`); it was corrected in the local harness, no application timestamps or freshness threshold were relaxed, and the successful evidence above uses the corrected JSON-encoded fixture messages.

## Eligibility and failure-state coverage

The integration test drives 20 closed consecutive one-minute fixture candles through the existing route and checks source, instrument, event/receipt timestamps, OHLCV, and test-only origin. The existing descriptive `MarketIntelligenceEngine` components are invoked only for eligible fresh closed candles and remain `UNVALIDATED`; no directional forecast/trading result is created.

The same integration suite verifies stale input, fewer than 20 candles, invalid quality, provisional candles, and nonconsecutive timestamps all remain `DATA_UNAVAILABLE` with `engine_invoked=false`. The route does not fill missing candles or substitute a different venue.

Feed lifecycle tests additionally verify:

- The feed itself refuses startup under the default-denied external-network policy.
- A mocked-permitted local worker can start without transport.
- Same-instance start does not create a second worker, and another in-process feed instance is rejected while a worker is alive.
- FastAPI does not start an injected feed when policy is denied.
- Normal denied-policy lifespan exposes `NETWORK_BLOCKED` / `DATA_UNAVAILABLE`.
- A mocked failed connection retains reconnect state.
- `stop()` reports timeout if a worker fails to exit; lifespan logs the timeout.

These are deterministic tests, not proof of multi-process worker election, real socket shutdown, provider authorization, or successful live connection.

## Commands and outcomes

1. Combined focused R1 feed/lifecycle/API/frontend suite:

```text
.\.venv_win\Scripts\pytest.exe tests\test_v37_4_r1_feed_lifecycle.py tests\test_v37_4_r1_trade_feed.py tests\test_v37_4_r1_api.py tests\test_v37_4_r1_frontend.py -q --tb=short
```

**Result:** 22 passed, 1 existing Pydantic deprecation warning. The first run before adjusting the pre-existing API fixture's test-only permission mock had one expected failure (injected fixture did not start under the newly enforced gate); after the fixture explicitly mocked permission and the mock transport remained local, the rerun passed.

2. Local FastAPI/integration/chart tests:

```text
.\.venv_win\Scripts\pytest.exe tests\test_v37_4_r1_app_integration.py -q --tb=short
```

**Result:** 2 passed, 1 existing Pydantic deprecation warning.

3. Focused R1 plus relevant market-data/candle regressions:

```text
.\.venv_win\Scripts\pytest.exe -q -p no:cacheprovider --tb=short -ra -m "not network and not quarantined" tests\test_v37_4_r1_trade_feed.py tests\test_v37_4_r1_api.py tests\test_v37_4_r1_frontend.py tests\test_v37_4_r1_feed_lifecycle.py tests\test_v37_4_r1_app_integration.py tests\test_v37_4_r1_evidence_qa.py tests\test_market_data_feed.py tests\test_candle_manager.py tests\test_market_monitor_routes.py tests\test_market_drivers.py tests\test_coinbase_l2_collector_and_gating.py tests\test_single_market_data_contract.py tests\test_v32_61_provider_adapter_poc.py tests\test_v32_66_provider_contract.py tests\test_v33_7_bitstamp_integration.py
```

**Result:** 94 passed, 1 failed, 0 skipped, 0 setup errors; one existing Pydantic deprecation warning. The sole failure is `test_protected_artifacts_bit_level_invariance`: the unchanged `data/raw/ohlcv.parquet` SHA-256 `ba06…4057` does not match the test's hard-coded `c007…ce3f` expectation. Neither dataset nor assertion was modified. The new future-clock-skew test passed.

4. `npm run check --silent` — passed.
5. A final repository-wide `git diff --check` reported trailing whitespace in other modified worktree files (`README.md`, `engine/price_forecast_engine.py`, `research/post_repair_block_builder.py`, and four `research/reports/` files). These were left untouched as out of scope. The three V37.4-R1 final report files pass a scoped `git diff --check`; Git also emitted LF-to-CRLF working-copy notices.

The combined protected-file guard once observed transient SQLite `-wal`/`-shm` sidecars during tests and logged a changed manifest digest. Immediate post-run inspection found only the existing `experiments/results/observatory.db`; sidecars were absent. The protected parquet hash remained identical to preflight. This guard observation is recorded as a test-environment warning, not silently reported as a clean immutable-database run.

## What this report does not establish

- No live provider connection or actual market feed through the application.
- No clock synchronization or qualified exchange latency statistics.
- No permitted data retention/research rights.
- No provider-specific production network approval.
- No 30-minute R2 soak or independently auditable historic raw-message sequence.
- No prospective model evidence or model authorization.

Research experiment: `INCONCLUSIVE` · Prospective evidence: `NOT_STARTED` · Model authorization: `OFFLINE_RESEARCH_ONLY` · Live trading: `DISABLED`.
