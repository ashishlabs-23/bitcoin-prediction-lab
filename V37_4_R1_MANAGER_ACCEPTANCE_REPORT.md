# BTCognitive V37.4-R1 — Manager Acceptance Report

**Assessment date:** 2026-11-04  
**Final status:** `PARTIAL_PASS`  
**Live-ready:** No

## Executive decision

The R1 implementation adds an in-memory Bitstamp trade collector, event-time one-minute candle aggregation, an existing FastAPI candle response path, and a source-aware chart integration. The bounded live check proved that one actual Bitstamp trade could be parsed into a candle snapshot and returned by the existing API route.

This is not a live-ready or rights-cleared feed. The observed exchange event was **226.076603 seconds older** than its local receipt time, so the API correctly returned `STALE` and withheld the intelligence-engine call. Bitstamp data-use rights remain unverified. The existing external-network policy continues to block automatic feed startup, and no full running-application/browser pass or 30-minute soak was completed.

No live trading, broker connection, order execution, model promotion, prospective validation, persistence of the live observation, provider-policy bypass, or cross-venue mixing was introduced.

## Implemented path and evidence

| Stage | Existing component / change | Evidence and limitation |
|---|---|---|
| Actual exchange trade | `BitstampTradeFeed` in [engine/market_data_feed.py](./engine/market_data_feed.py) subscribes to Bitstamp `live_trades_btcusd`. | A bounded, manual, in-memory connection received and parsed one actual trade. This was a technical check only; data-use rights remain unresolved. |
| Observation contract | Reuses the existing `MarketDataObservation`; preserves `source=bitstamp`, `BTC/USD`, exchange event time, local receipt time, trade ID, price, quantity, and source metadata. | Timestamp regression tests cover seconds/microseconds parsing. Neither event nor candle timestamps are shifted to mask delay. |
| Candle construction | [api/candle_manager.py](./api/candle_manager.py) adds a separate ingestion-only event-time 1-minute path; it does not call the legacy inference-coupled `process_tick`. | Deterministic tests cover OHLCV, duplicates, out-of-order trades, and missing intervals without synthetic gap candles. The live check produced one candle from one observed trade. |
| FastAPI delivery | [api/market_monitor_routes.py](./api/market_monitor_routes.py) exposes the Bitstamp 1-minute snapshot through `/api/market/candles`. | The bounded real observation returned HTTP 200, one `BTC/USD` candle, and its event/receipt timestamps. Status was correctly `STALE`. |
| Intelligence engine | The route permits descriptive `MarketIntelligenceEngine` structure/momentum components only with 20 consecutive closed, valid candles; results are marked `UNVALIDATED` or `STALE`. | A deterministic test verifies compatible handoff for 20 eligible candles. The actual live snapshot had one stale candle, so the engine was not invoked (`DATA_UNAVAILABLE`). No live forecast result is claimed. |
| Frontend | [web/app.js](./web/app.js) requests the existing API route, renders source/status and observed OHLCV, and labels Bitstamp receipt time as a Bitstamp observation. | A frontend test renders API-shaped Bitstamp data and checks source, price, OHLCV, and status. A real observation was not driven through a running browser session. |

### Timestamp and freshness findings

The raw-message parser treats `timestamp` as Unix seconds and `microtimestamp` as Unix microseconds. The earlier raw-message investigation showed the fields agree at sub-second precision; the delay is not explained by a unit conversion error. In the bounded integration check:

- Exchange event timestamp: `2026-11-04T16:11:57.653000Z`
- Local receive timestamp: `2026-11-04T16:15:43.729603Z`
- Event-to-receive delay: **226.076603 seconds**
- API `status` / `freshness_status`: `STALE`
- Returned candle count: `1`
- Analysis: `DATA_UNAVAILABLE`; engine not invoked

The feed uses a 60-second freshness threshold. It reports stale data rather than replacing event time with receipt time or marking delayed events fresh.

## Definition-of-done matrix

| ID | Criterion | Status |
|---|---|---|
| D1 | Primary BTCUSD exchange feed connects | `PARTIAL_PASS` — bounded Bitstamp collector connected manually; automatic application startup is blocked by policy. |
| D2 | Actual trade observations received and parsed | `PASS` — one actual trade parsed in the bounded check; deterministic parser tests also pass. |
| D3 | Raw observations preserve exchange and receive timestamps | `PASS` — distinct event and local receipt timestamps are returned and delay is reported. |
| D4 | Duplicate events handled deterministically | `PASS` — duplicate handling is covered by focused tests. |
| D5 | One-minute candles constructed correctly | `PASS` for deterministic aggregation tests; live check produced one single-trade candle only. |
| D6 | Missing intervals and stale data detected | `PASS` — tests cover gaps without filling; live API correctly reports the observed delay as stale. |
| D7 | Same-source historical recovery and provenance | `NOT_VERIFIED` — no recovery is enabled; source terms and permitted use remain unresolved. |
| D8 | Secondary feeds remain independent | `PASS` — no venue mixing or silent fallback was introduced. |
| D9 | Existing FastAPI exposes actual observations and quality | `PASS` for the bounded in-process API route request; response was `STALE`, not fresh. |
| D10 | Existing engines receive compatible validated data | `PARTIAL_PASS` — deterministic eligible-candle test verifies the descriptive engine handoff; the actual stale one-candle observation was correctly withheld. |
| D11 | Existing frontend charts display actual API observations | `PARTIAL_PASS` — API-shaped chart test passes; real running-browser delivery was not verified. |
| D12 | Existing routes and feature families remain available | `PASS` — no route or product feature was removed; targeted route/frontend tests pass. |
| D13 | Reconnect, duplicate, stale, and error behavior tested | `PASS` for deterministic coverage; no long-duration live stability claim. |
| D14 | Actual application integration tested | `PARTIAL_PASS` — actual trade reached the candle API via an in-process check; normal app startup and browser integration remain unverified. |
| D15 | Live smoke or soak recorded | `PARTIAL_PASS` — bounded smoke completed; the 30-minute soak was not completed. |
| D16 | Protected hashes and Git state remain intact | `PASS` — protected-file guard unchanged, parquet digest matches preflight, branch and HEAD unchanged; existing user modifications were preserved. |

## Changed files

R1 implementation changes:

- [api/candle_manager.py](./api/candle_manager.py)
- [api/market_monitor_routes.py](./api/market_monitor_routes.py)
- [api/server.py](./api/server.py)
- [engine/market_data_feed.py](./engine/market_data_feed.py)
- [tests/test_market_monitor_routes.py](./tests/test_market_monitor_routes.py)
- [web/app.js](./web/app.js)

R1 QA additions:

- [tests/test_v37_4_r1_trade_feed.py](./tests/test_v37_4_r1_trade_feed.py)
- [tests/test_v37_4_r1_api.py](./tests/test_v37_4_r1_api.py)
- [tests/test_v37_4_r1_frontend.py](./tests/test_v37_4_r1_frontend.py)
- [V37_4_R1_QA_REPORT.md](./V37_4_R1_QA_REPORT.md)

This acceptance report is an additional deliverable. Other pre-existing worktree modifications were not changed or discarded.

## Validation results

- `.\.venv_win\Scripts\pytest.exe tests\test_v37_4_r1_trade_feed.py tests\test_v37_4_r1_api.py tests\test_v37_4_r1_frontend.py -q --tb=short` — **15 passed**, 1 existing Pydantic deprecation warning. Protected-file guard: **PASS**, 1,848 files, identical before/after manifest digest `d424b3c0dd43a0b4a91735a2050fd43315edd341d3f146655aad6698ec3ce031`.
- `.\.venv_win\Scripts\pytest.exe -q -p no:cacheprovider -m "not network and not quarantined" tests\test_v32_61_provider_adapter_poc.py tests\test_v32_66_provider_contract.py tests\test_candle_manager.py tests\test_coinbase_l2_collector_and_gating.py tests\test_market_monitor_routes.py` — **42 passed, 1 failed**. The failure is the existing hard-coded `data/raw/ohlcv.parquet` digest expectation (`c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`) versus the unchanged file's preflight/current SHA-256 `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`. Neither dataset nor assertion was altered.
- `npm test` — passed.
- `npm run check` — passed.
- `npm run build` — passed.
- `git diff --check` — clean apart from Git's existing LF-to-CRLF working-copy notices.

The initial QA run's **12 passed, 2 failed** result is retained in [V37_4_R1_QA_REPORT.md](./V37_4_R1_QA_REPORT.md); both defects were fixed, and the final focused R1 suite passes. An earlier adjacent run also recorded an unrelated frontend-directory assertion failure (`web/analysis_contract.js` was present); it is not represented as a clean full regression.

## Repository and protected-data integrity

- Branch: `milestone/v35.3-critical-remediation`
- HEAD: `25d483f4c3646661b57311de9d0b53d2be881adb`
- `data/raw/ohlcv.parquet` SHA-256: `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` (same as R1 preflight)
- R1 preflight had 119 tracked modifications and 1,623 untracked paths. The current R1 work adds one tracked test modification and four R1 QA files; this manager report is one further untracked deliverable. No staged files, branch change, commit, reset, stash, deletion, or cleanup was performed.

## Remaining blockers and governed decisions

- Bitstamp official documentation and applicable data-use rights are not verified; do not persist or use these observations for model research or validation until rights are established.
- `is_external_network_permitted()` remains false because no licensed/cleared provider is configured. Application startup does not autonomously connect. No policy gate was changed or bypassed.
- The observed feed delay exceeds the 60-second threshold. No freshness claim or historical candle repair is made.
- No complete actual-trade-to-running-browser pass, long soak, or prospective data collection was performed.

1. **Research Experiment:** `INCONCLUSIVE`
2. **Prospective Evidence:** `NOT_STARTED`
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`
4. **Live Trading:** `DISABLED`

**Acceptance:** `PARTIAL_PASS` for the bounded technical path and deterministic contracts only. This does not authorize live operation, data persistence, model validation, model promotion, or trading.
