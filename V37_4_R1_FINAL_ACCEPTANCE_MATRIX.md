# BTCognitive V37.4-R1 — Final Acceptance Matrix

**Assessment date:** 2026-11-04  
**Final status:** `PARTIAL_PASS`  
**R1 engineering complete:** Yes, for the deterministic local application path  
**Live-ready:** No

## Acceptance criteria

| # | Requirement | Status | Evidence / qualification |
|---|---|---|---|
| 1 | Feed lifecycle is safe and idempotent | `PASS` | `BitstampTradeFeed.start()` enforces the authoritative network gate, is idempotent for the same running instance, rejects another active in-process worker, and `stop()` reports termination vs timeout. Lifecycle tests cover failure/reconnect and timeout. Multi-process coordination is not established; deploy only one ingestion worker if a future provider is approved. |
| 2 | Network restrictions cannot be bypassed through feed injection | `PASS` | The FastAPI lifespan checks policy before starting any injected feed; denied custom injection is replaced with blocked/unavailable feed state. The feed's own start path also checks policy. Default policy remains false. |
| 3 | Normal FastAPI lifespan works | `PASS` | Actual server lifespan test completed with policy denied and exposed `NETWORK_BLOCKED` / `DATA_UNAVAILABLE`. A separate local fixture run used a test-only permission mock to exercise the permitted branch without transport. |
| 4 | Existing API returns observations from the candle manager | `PASS` (fixture) | Deterministic trade messages pass through `_handle_raw_message`, `process_trade_ingestion_only`, the existing market candle route, and JSON response. No actual provider observation was used in this closure run. |
| 5 | Event-time candle aggregation is correct | `PASS` (deterministic) | Tests cover OHLCV, duplicate and out-of-order trades, minute boundaries and gaps without synthetic fill. Live browser/API fixture used this existing aggregation path. |
| 6 | Source, symbol, event timestamp, receipt timestamp propagate | `PASS` (fixture) | API response and chart preserve `bitstamp`, `BTC/USD`, event timestamp, receipt timestamp, and fixture origin. Fixture timestamps are not provider evidence. |
| 7 | Existing intelligence engine runs only for eligible input and fails closed otherwise | `PASS` (contract tests) | Requires 20 consecutive valid, closed, fresh one-minute candles. Stale, insufficient, invalid, provisional, or gapped input returns `DATA_UNAVAILABLE`; no directional forecast or trading signal is emitted. Eligible output is `UNVALIDATED`. |
| 8 | Existing frontend chart consumes the running app's API response | `PASS` (local browser fixture) | Browser selected 1m and displayed `LOCAL TEST FIXTURE ONLY · NOT MARKET DATA`, fixture price, status, timestamp label, and `Feed: bitstamp · FRESH`. This is a local fixture, not a market-data observation. |
| 9 | Existing frontend routes remain accessible | `PARTIAL_PASS` | `#/terminal`, `#/research`, and `#/journal` rendered their existing views; application API/OpenAPI routes remained mounted. The journal view displayed an existing `window.api.fetchJournalTrades is not a function` error in the local harness. No route was removed. |
| 10 | Focused and relevant regression tests pass | `PARTIAL_PASS` | 94 passed, 1 failed in the combined R1/market-data regression command. Sole failure is a pre-existing hard-coded parquet digest expectation. Dedicated lifecycle, integration, and combined R1 suites passed. |
| 11 | Protected-file integrity remains intact | `PASS` for protected parquet; guard warning retained | `data/raw/ohlcv.parquet` remains SHA-256 `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`, matching preflight. No data or assertion was changed. A test-time manifest guard saw transient SQLite WAL/SHM sidecars that disappeared after tests; report this as an environment warning. |
| 12 | Existing soak evidence reconciled | `PARTIAL_PASS` | Saved summary records 1,800.1986 seconds and 3,693 events, but only aggregate JSON exists. No raw consecutive messages, so event sequence, aggregate counters and 227.028209-second maximum are not independently validated. Current host clock is unsynchronized; actual latency/freshness remains unqualified. |

## R2 live-operation gates

| Gate | Status | Current decision |
|---|---|---|
| Verified host clock | `BLOCKED` | Windows reports `Local CMOS Clock`, not synchronized; `w32tm` source offsets are approximately 226 seconds in magnitude. No time correction was authorized or attempted. |
| Repeated fresh provider observations | `NOT VERIFIED` | No provider connection was made in R2/R1 closure. Historic aggregate soak has no raw sequence and is clock-confounded. |
| Provider/source timestamps compared | `PARTIAL / NOT QUALIFIED` | Parser unit tests pass; timestamp comparison exists for historical observations, but true source-to-receiver latency cannot be inferred. |
| Permitted data use | `BLOCKED` | Bitstamp rights unresolved; CoinAPI and Gemini remain conditional/not cleared per provider review. |
| Approved application network configuration | `BLOCKED` | `is_external_network_permitted()` remains false in every mode. `provider` mode is not authorization. No owner/legal approval or provider-specific allow decision exists. |
| Automatic feed startup in approved deployment | `NOT VERIFIED` | Deterministic lifecycle branch is tested with mocks only; no operational policy approval exists. |
| Actual candle delivery in authorized running app | `NOT VERIFIED` | Local browser/API delivery is fixture-only. |
| Browser display of actual market data | `NOT VERIFIED` | Browser display proved only fixture rendering. |
| No synthetic values / cross-venue mixing | `PASS` for R1 changes | Test fixture is explicitly marked test-only; Bitstamp path remains source-specific; no venue fallback/mixing was added. |
| Feature scope preservation | `PASS` | No core route, engine, strategy, research module, or frontend feature family was removed or replaced. |

## Test record

- **Dedicated feed lifecycle:** 7 passed; no live provider connection.
- **Combined R1 feed/lifecycle/API/frontend rerun:** 22 passed, one existing Pydantic deprecation warning.
- **FastAPI local fixture integration:** 2 passed, one existing Pydantic deprecation warning.
- **Combined focused + market-data regression:** 94 passed, 1 failed, 0 skipped/setup errors. Failure: existing protected-hash assertion expects `c007…ce3f`; unchanged parquet is `ba06…4057`.
- **Frontend syntax:** `npm run check --silent` passed.
- **Whitespace:** Final report files pass scoped `git diff --check`. Repository-wide `git diff --check` reports trailing whitespace in other modified worktree files; those unrelated files were left untouched. Git also emitted LF-to-CRLF working-copy notices.
- **Browser:** actual local app page loaded; 1m chart displayed fixture response; three hash routes rendered. No provider, no real market observation.

## Repository and data governance

- Branch: `milestone/v35.3-critical-remediation`
- HEAD: `25d483f4c3646661b57311de9d0b53d2be881adb`
- Protected parquet: unchanged from R1 preflight.
- Holdout custody manifest SHA-256: `664aaed5229361cb00ab544763e80ad2146c135ec1887156ce8d53c40ad8f5f1` (matches preflight).
- Contract freeze manifest SHA-256: `b5a17a75862339bcc8928971f323f6df4f642f55b3a5a43a502a3afa75e4f1ce` (matches preflight).
- Existing user modifications, research ledgers, manifests, and frozen contracts were preserved.
- No branch creation, commit, push, stash, reset, discard, system clock change, provider connection, model promotion, or trading activation occurred.

## Release decisions

1. **Research Experiment:** `INCONCLUSIVE`
2. **Prospective Evidence:** `NOT_STARTED`
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`
4. **Live Trading:** `DISABLED`

**Acceptance:** `PARTIAL_PASS`. R1 local engineering is complete and verified with deterministic fixtures. Operational live-data readiness is blocked until clock synchronization is independently approved, a provider and underlying-source license is cleared, and a documented provider-specific application network authorization is approved and tested.
