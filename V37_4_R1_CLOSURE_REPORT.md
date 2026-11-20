# BTCognitive V37.4-R1 — Engineering Closure Report

**Assessment date:** 2026-11-04  
**Final status:** `PARTIAL_PASS`  
**R1 engineering path:** `PASS` for local deterministic FastAPI/API/chart integration  
**Live-ready:** No

## Executive decision

R1's remaining local integration work is closed to the extent that it can be verified without an authorized external data provider. The existing Bitstamp trade parser, `MarketDataObservation`, ingestion-only `CandleStateManager`, FastAPI candle route, and existing chart were exercised together using clearly identified deterministic local test messages. The real FastAPI lifespan and API route returned the aggregated fixture candles, and the existing browser chart consumed the response and displayed `LOCAL TEST FIXTURE ONLY · NOT MARKET DATA`.

The lifecycle was hardened so default-denied policy blocks `BitstampTradeFeed.start()` itself and all FastAPI lifespan start paths, including injected feeds. Startup is idempotent for a feed instance; an in-process duplicate worker is blocked; stop reports whether its thread terminated; and startup without permission produces explicit `DATA_UNAVAILABLE` / `NETWORK_BLOCKED`.

This is **engineering-complete for the local path, not live-ready**. The Windows host clock remains unsynchronized, Bitstamp and alternative-provider data-use rights are not cleared, the authoritative external-market-data policy remains denied in every mode, and no new provider or exchange connection was made. Do not use the aggregate-only historic soak or local test fixtures as freshness, research, or model-validation evidence.

## Dated corrections and evidence reconciliation

- The original [V37_4_R1_MANAGER_ACCEPTANCE_REPORT.md](./V37_4_R1_MANAGER_ACCEPTANCE_REPORT.md) and [V37_4_R1_QA_REPORT.md](./V37_4_R1_QA_REPORT.md) are preserved as historical records. Their earlier statements that a full local browser path was not verified are superseded by the manager's dated local-only browser check in [V37_4_R1_QA_CLOSURE_ADDENDUM.md](./V37_4_R1_QA_CLOSURE_ADDENDUM.md).
- The previously conflicting 30-minute record is reconciled as a **completed aggregate-only run according to the saved summary**, with 1,800.1986 seconds and 3,693 events reported. Raw consecutive messages and a per-message timestamp/ID series are absent, so the aggregate counters and `max_receive_lag_seconds=227.028209` cannot be independently audited. The Windows clock diagnostics show an unsynchronized clock with offsets around the same magnitude; the summary's timestamp differences therefore do not establish true exchange-to-receiver latency or feed freshness. See [V37_4_R1_QA_CLOSURE_ADDENDUM.md](./V37_4_R1_QA_CLOSURE_ADDENDUM.md) and [V37_4_R2_CLOCK_AND_FEED_REPORT.md](./V37_4_R2_CLOCK_AND_FEED_REPORT.md).
- The earlier `data/raw/ohlcv.parquet` mismatch remains: current and preflight SHA-256 is `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`; an existing integrity test expects `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`. Neither file nor guard was modified.
- The R1 preflight manifest hashes were rechecked: [holdout_custody_manifest.json](./research/entry_tp_sl/holdout_custody_manifest.json) remains `664aaed5229361cb00ab544763e80ad2146c135ec1887156ce8d53c40ad8f5f1`; [contract_freeze_manifest.json](./research/entry_tp_sl/contract_freeze_manifest.json) remains `b5a17a75862339bcc8928971f323f6df4f642f55b3a5a43a502a3afa75e4f1ce`.
- Final verification note: repository-wide `git diff --check` reported trailing whitespace in other modified worktree files (`README.md`, `engine/price_forecast_engine.py`, `research/post_repair_block_builder.py`, and four `research/reports/` files). These unrelated files were preserved. All three final V37.4-R1 reports pass a scoped whitespace check.

## Implementation changes included in closure

- [engine/market_data_feed.py](./engine/market_data_feed.py): external-network permission is enforced by the feed's own `start()` method; startup-denied, duplicate-worker, and shutdown-timeout states are explicit; `stop()` returns thread-termination success/failure.
- [api/server.py](./api/server.py): applies the same policy to default and injected feeds, replaces denied injected feeds with a blocked/unavailable feed status, and logs startup/shutdown failures truthfully.
- [api/candle_manager.py](./api/candle_manager.py): retains the ingestion-only, event-time one-minute aggregation separate from inference-coupled `process_tick`.
- [api/market_monitor_routes.py](./api/market_monitor_routes.py): keeps source/event/receipt timestamps, marks fixture origin, and invokes descriptive intelligence only for 20 valid, consecutive, closed, fresh candles.
- [web/app.js](./web/app.js): retains source and timestamps through the active chart hook and visibly labels test fixtures as non-market data.
- Focused additions: [test_v37_4_r1_feed_lifecycle.py](./tests/test_v37_4_r1_feed_lifecycle.py), [test_v37_4_r1_app_integration.py](./tests/test_v37_4_r1_app_integration.py), and [test_v37_4_r1_evidence_qa.py](./tests/test_v37_4_r1_evidence_qa.py). Existing R1 tests were retained; [test_v37_4_r1_api.py](./tests/test_v37_4_r1_api.py) explicitly mocks permission only inside its fixture test.

No duplicate market-data framework, replacement engine, replacement frontend, live-data persistence, strategy activation, trading path, or unrestricted environment-variable override was added. `engine/data_mode.py`'s default-deny behavior was not changed.

## Remaining blockers

1. **Clock and freshness:** the host reports `Local CMOS Clock`, no successful synchronization, and current time-source offsets of about 226 seconds. Do not correct timestamps by shifting observations. R1's historical delay/soak values are not qualified as true source-to-receiver latency.
2. **Data use:** Bitstamp is not cleared for retention or research use. CoinAPI is conditional and not cleared; Gemini is conditional and not cleared under [V37_4_R2_PROVIDER_DECISION.md](./V37_4_R2_PROVIDER_DECISION.md).
3. **Network policy:** `is_external_network_permitted()` remains false in all current data modes; `DATA_MODE=provider` is not authorization. No owner/legal provider-specific approval or runtime allow decision exists. See [V37_4_R2_STARTUP_GATE_REPORT.md](./V37_4_R2_STARTUP_GATE_REPORT.md).
4. **Operations:** no newly authorized automatic provider startup, live application integration, or additional live soak was run. The local browser test used an in-memory deterministic fixture and test-only permission mocks.

### Governed decisions

1. **Research Experiment:** `INCONCLUSIVE`
2. **Prospective Evidence:** `NOT_STARTED`
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`
4. **Live Trading:** `DISABLED`

**Final status:** `PARTIAL_PASS` — R1 local engineering integration is verified; external market-data operation and qualification remain blocked.
