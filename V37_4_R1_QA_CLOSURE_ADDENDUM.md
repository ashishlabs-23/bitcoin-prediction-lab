# V37.4-R1 Independent QA Closure Addendum

**Date:** 2026-11-04  
**Scope:** Read-only evidence reconciliation and deterministic QA. No production code, existing tests, protected datasets/assertions, provider policy, or manager deliverables were changed by this QA workstream. No live exchange connection or model validation was performed.

## Soak evidence reconciliation

The session-persisted artifact `files/v37_4_bitstamp_soak_summary.json` reports a completed Bitstamp BTC/USD WebSocket soak:

- Requested duration: 1,800 seconds; reported actual duration: 1,800.1986 seconds.
- 3,693 trade events and 3,693 unique trade IDs; one successful connection and no reconnects.
- Aggregate counters report no invalid messages/trades, duplicate IDs, out-of-order event timestamps, or gaps over 60 seconds.
- Maximum receive lag: 227.028209 seconds. The final trade event was at `2026-11-04T15:50:58.957Z`; the last receipt was at `2026-11-04T15:54:45.036723Z`.

The persisted V37.4 evidence contains only this aggregate summary—not raw consecutive WebSocket messages, a per-trade event/receipt timestamp-and-ID sequence, or a connection transcript. The separate `v37_3_bitstamp_public_ohlc_qa/request_metadata.json` is metadata for a V37.3 HTTP OHLC request, not the V37.4 WebSocket soak. Therefore classify this as a **completed aggregate-only soak with delayed/stale observations**, not an independently auditable continuous-message soak or fresh-feed qualification. The summary’s zero-gap counters cannot be independently verified without per-message evidence; the recorded maximum lag also exceeds the 60-second freshness threshold.

Earlier V37.4 notes that a 30-minute attempt stopped before completion remain preserved as historical evidence of that earlier attempt. The later persisted summary records a completed-duration attempt, but does not supply raw sequence evidence; this addendum distinguishes rather than rewrites those records.

## Protected parquet hash reconciliation

The R1 preflight record captured `data/raw/ohlcv.parquet` at SHA-256:

`ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`

The focused QA run reported the same actual digest. The failure is an existing hard-coded expectation of `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`, including `tests/test_v32_61_provider_adapter_poc.py` and other historical integrity tests—not a discrepancy between the parquet file and its captured R1 preflight digest. No dataset or assertion was edited.

This explains why the earlier manager record that the parquet digest matched preflight and the regression report of a failing hard-coded digest check can both be retained: they compare the same unchanged file against different expected values. Existing reports and historical assertions were left untouched.

During the combined pytest run, the protected-file manifest guard also logged transient `experiments/results/observatory.db-shm` and `observatory.db-wal` entries and different before/after manifest digests (`d424b3c0dd43a0b4a91735a2050fd43315edd341d3f146655aad6698ec3ce031` and `86efa292302eb81f80b2725399e400cd109d2fd87e5032978e541677b72fc013`). Immediate post-run inspection found those sidecars absent and only the existing `observatory.db` present; no cleanup or modification was performed. Treat this guard output as an additional test-environment warning, not evidence that the parquet changed.

## Focused regression results

After the feed-lifecycle and local app-integration work was complete, ran:

```text
.\.venv_win\Scripts\pytest.exe -q -p no:cacheprovider --tb=short -ra -m "not network and not quarantined" tests\test_v37_4_r1_trade_feed.py tests\test_v37_4_r1_api.py tests\test_v37_4_r1_frontend.py tests\test_v37_4_r1_feed_lifecycle.py tests\test_v37_4_r1_app_integration.py tests\test_v37_4_r1_evidence_qa.py tests\test_market_data_feed.py tests\test_candle_manager.py tests\test_market_monitor_routes.py tests\test_market_drivers.py tests\test_coinbase_l2_collector_and_gating.py tests\test_single_market_data_contract.py tests\test_v32_61_provider_adapter_poc.py tests\test_v32_66_provider_contract.py tests\test_v33_7_bitstamp_integration.py
```

**Result:** 94 passed, 1 failed, 0 skipped, 0 errors/setup errors; one existing Pydantic deprecation warning. The failure was `tests/test_v32_61_provider_adapter_poc.py::test_protected_artifacts_bit_level_invariance`, where the unchanged parquet digest `ba06…4057` did not match that test’s stale `c007…ce3f` expectation. The new QA edge-case test for an ACTIVE snapshot with event/receipt times more than five seconds in the future passed; it verifies the API downgrades that snapshot to `STALE`.

The focused run is not an all-green regression result because of the protected-hash assertion above. The separate local integration report records **2 passed** for `tests/test_v37_4_r1_app_integration.py`; the lifecycle report records **7 passed** for `tests/test_v37_4_r1_feed_lifecycle.py`. Browser automation was not run because the page depends on external CDN assets and external-network access was outside this QA scope.

## Governed disposition

1. **Research Experiment:** `INCONCLUSIVE` — this QA did not validate a model or establish fresh-feed qualification.
2. **Prospective Evidence:** `NOT_STARTED` for confirmatory model evaluation; this aggregate-only delayed soak is not confirmatory evidence.
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`.
4. **Live Trading:** `DISABLED`.

## Manager follow-up — local browser integration — 2026-11-04

The QA workstream did not run browser automation. After its report was written, the manager separately completed a local-only browser integration check; this supersedes only the browser limitation above and does not change the soak or provider-readiness findings.

The existing `api.server.app` and its actual FastAPI lifespan were started on `127.0.0.1:8765` with a deterministic in-memory feed fixture. In that local test process only, the network policy function was mocked to permit the injected fixture. The fixture generated Bitstamp-shaped trade messages through the existing parser and `CandleStateManager` ingestion-only aggregation path. Its `start()` method made no provider connection. It set `test_only=true` and `data_origin=TEST_FIXTURE_ONLY`; no live observation was used or persisted.

From the browser, `/api/market/candles?symbol=BTC-USD&interval=1m&limit=500` returned HTTP 200 with `status=ACTIVE`, `freshness_status=FRESH`, `source=bitstamp`, `data_origin=TEST_FIXTURE_ONLY`, 23 observed fixture candles, and `analysis.status=UNVALIDATED`. The response preserved event time `2026-11-04T17:12:59.900000Z` and receipt time `2026-11-04T17:13:48.560739Z`; the derived fixture timestamp difference was 48.660739 seconds and is not market latency evidence.

Selecting the existing 1-minute chart in the browser rendered `LOCAL TEST FIXTURE ONLY · NOT MARKET DATA`, the fixture price, `ACTIVE`, and `Local test fixture timestamp:`. The chart diagnostics showed `BTC-USD · 1m · Feed: bitstamp · FRESH`. Existing `#/terminal`, `#/research`, and `#/journal` hash routes rendered their corresponding content. The journal view also showed an existing `window.api.fetchJournalTrades is not a function` message in this test setup; route reachability is not a claim that every unrelated route backend operation passed. Other dashboard requests likewise showed expected errors where the local harness supplied no real forecast service/client.

The test server was stopped after the browser check. This proves local app/API/chart plumbing with explicitly labeled fixtures only; it is not an exchange smoke test, provider authorization, clock qualification, sustained soak, forecast validation, or live readiness.
