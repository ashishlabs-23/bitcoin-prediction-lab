# BTCognitive V37.4-R2 — Application Network Gate and Integration Readiness

**Review date:** 2026-11-04  
**Disposition:** `BLOCKED_PENDING_OWNER_AND_LEGAL_APPROVAL`  
**Scope:** Read-only review of the active data-mode gate, FastAPI/feed lifecycle, API/frontend contract, and directly relevant tests. No provider was contacted; no source, test, settings, prior report, or protected data was changed.

## Decision

The Bitstamp collector and 1-minute display path exist, but **normal application startup cannot start it**. The authoritative `is_external_network_permitted()` implementation returns `False` for every data mode, explicitly because no licensed/cleared provider is configured. `provider` is a recognized mode name, not permission: its status contract still reports `provider_configured=False`, and it does not enable networking ([`engine/data_mode.py`](engine/data_mode.py#L20-L40), [#L100-L123](engine/data_mode.py#L100-L123), [#L152-L176](engine/data_mode.py#L152-L176)).

There is **no currently approved runtime configuration or environment flag that grants Bitstamp network access**. Setting `BTC_DATA_MODE=provider` or `DATA_MODE=provider` only selects the provider lane; it does not clear rights or make the network gate true. Do not invent or set a separate flag to work around that policy.

Safe now: deterministic/offline operation, truthful unavailable responses, and the isolated in-memory feed/API/chart path exercised with fixtures. Blocked: live provider connection, operational live-data readiness, any claim of cleared data rights, durable retention, redistribution, or model-research use.

## Gate and approval conditions

The mode contract defaults pytest to `fixture` and ordinary local execution to `offline_research`; both deny outbound calls. `provider` also denies them, and `assert_no_external_network()` fails before transport in the restricted state ([`engine/data_mode.py`](engine/data_mode.py#L71-L123)). The status payload hard-codes `provider_configured=False`; in provider mode it reports `PROVIDER_NOT_CONFIGURED` and `UNAUTHORIZED` rights status ([`engine/data_mode.py`](engine/data_mode.py#L152-L176)).

The prior source/licensing review says Bitstamp's official WebSocket documentation and substantive terms were unavailable, and explicitly treats Bitstamp as provisional rather than rights-cleared. It requires owner/legal review before raw-event retention, model research, commercial use, or redistribution ([`V37_4_EXCHANGE_SOURCE_AND_LICENSING_REPORT.md`](V37_4_EXCHANGE_SOURCE_AND_LICENSING_REPORT.md#L8-L16), [#L31-L34](V37_4_EXCHANGE_SOURCE_AND_LICENSING_REPORT.md#L31-L34)). The R1 acceptance likewise records that rights remain unverified and automatic startup remains blocked ([`V37_4_R1_MANAGER_ACCEPTANCE_REPORT.md`](V37_4_R1_MANAGER_ACCEPTANCE_REPORT.md#L8-L12)).

Before any network enablement, the owner/legal decision must document the selected provider and exact permitted purposes—including live collection/display, retention duration and location, research/model training or validation, commercial use, and redistribution as applicable—and verify the provider's official protocol, data terms, and recovery/freshness guarantees. Approval for one purpose must not be inferred to cover another. A dated approval/provenance record and an explicit provider-specific allow decision in the authoritative gate are needed. That approval is **not present in the inspected code or reports**. A future configuration must preserve `OFFLINE_RESEARCH_ONLY` model authorization, analysis-only operation, and disabled trading.

## FastAPI lifecycle, worker duplication, and shutdown

`api.server.lifespan()` first verifies the scientific contract/readiness, initializes shared services, and forces `live_engine.is_running = False`. It only constructs the default `BitstampTradeFeed` when `is_external_network_permitted()` returns true; today that branch is unreachable under the authoritative implementation. It then calls `start()` synchronously and catches startup exceptions ([`api/server.py`](api/server.py#L129-L195)).

**Important gate edge:** an already-populated `app.state.bitstamp_trade_feed` skips the permission check and is started. The R1 lifecycle test deliberately injects a fixture subclass this way; it proves the fake feed's start/route/stop integration, not authorized live startup ([`api/server.py`](api/server.py#L166-L195), [`tests/test_v37_4_r1_api.py`](tests/test_v37_4_r1_api.py#L12-L29), [#L47-L95](tests/test_v37_4_r1_api.py#L47-L95)). This dependency-injection seam must not be treated as production authorization. Before approval, no real feed should be injected. After approval, the gate must apply to every start path, including injected instances.

`BitstampTradeFeed.start()` is idempotent only for a single instance while its thread is alive; it creates a daemon thread and returns without waiting for a successful connection ([`engine/market_data_feed.py`](engine/market_data_feed.py#L482-L496)). There is no process-wide singleton, inter-process lock, or worker election. Multiple Uvicorn/application workers each running their own lifespan can therefore create duplicate WebSocket connections and independent in-memory histories after the gate is enabled. The current `uvicorn.run()` invocation does not configure multiple workers itself, but deployment configuration is external to this code ([`api/server.py`](api/server.py#L353-L356)). A gated launch needs either one designated ingestion worker or an explicit shared ownership mechanism; per-instance idempotency is insufficient for multi-worker deployment.

Shutdown is wired into the lifespan `finally`: it cancels/awaits the research alert task, calls `trade_feed.stop()`, then closes the shared HTTP client ([`api/server.py`](api/server.py#L204-L224)). Feed stop signals its asyncio event and joins the thread for at most five seconds; the connection loop polls receives with a one-second timeout, exits the WebSocket context, and can wake promptly from reconnect backoff ([`engine/market_data_feed.py`](engine/market_data_feed.py#L498-L515), [#L714-L774](engine/market_data_feed.py#L714-L774)). However, `stop()` does not report whether the thread remained alive after the timeout and marks the state disconnected regardless. A real network shutdown/restart was not exercised; require a bounded join/alive assertion and lifecycle test before claiming operationally graceful shutdown.

## Credentials and data handling

The collector uses the public `wss://ws.bitstamp.net` URL and subscribes to `live_trades_btcusd`; the shown protocol sends no exchange key, authorization header, or trading request ([`engine/market_data_feed.py`](engine/market_data_feed.py#L423-L435), [#L714-L740](engine/market_data_feed.py#L714-L740)). No Bitstamp credentials are required by this path, and no secret values were accessed or recorded. The feed keeps observations and candles in bounded in-memory structures; there is no persistence in this collector ([`engine/market_data_feed.py`](engine/market_data_feed.py#L455-L480), [`api/candle_manager.py`](api/candle_manager.py#L49-L129)).

The constructor accepts a configurable `ws_url`, while connection exceptions are copied into `last_error` and that snapshot is included in the normalized API response ([`engine/market_data_feed.py`](engine/market_data_feed.py#L441-L450), [#L748-L756](engine/market_data_feed.py#L748-L756), [`api/market_monitor_routes.py`](api/market_monitor_routes.py#L728-L746)). The current public URL has no credential, but if a future adapter ever uses credential-bearing URLs or private endpoints, exception text must be sanitized before exposing it; credentials must never be embedded in URLs, logs, API responses, or frontend code. Existing application API keys are unrelated user-role credentials, not Bitstamp authorization ([`config/security.py`](config/security.py#L60-L80)).

## API/frontend readiness

The existing `/market/candles` and `/api/market/candles` route supports `interval=1m`, reads only `request.app.state.bitstamp_trade_feed`, and returns explicit unavailable data if no feed is configured ([`api/market_monitor_routes.py`](api/market_monitor_routes.py#L282-L312), [#L539-L619](api/market_monitor_routes.py#L539-L619)). It validates venue/symbol/interval, OHLCV, timestamps, freshness, and gaps. With 20 consecutive closed valid candles, it invokes existing structure/momentum components only; output remains `UNVALIDATED`/`STALE`, not a directional forecast or trading signal ([`api/market_monitor_routes.py`](api/market_monitor_routes.py#L679-L712)).

The active `web/app.js` chart polls this REST route every five seconds for `1m`, validates source and candle fields, propagates unavailable/stale/disconnected states, and labels Bitstamp observations as Bitstamp ([`web/app.js`](web/app.js#L1141-L1207), [#L1260-L1291](web/app.js#L1260-L1291), [#L2667-L2860](web/app.js#L2667-L2860)). This is polling, not a pushed live stream. The server `/ws` endpoint currently handles connection acknowledgement and ping/pong, with no Bitstamp broadcast wiring ([`api/server.py`](api/server.py#L295-L339)). Thus the API/frontend contract is **fixture-tested and structurally integrated**, but live updates are unavailable until the network and rights gates are cleared; no full running-app/browser live path was established in R1 ([`V37_4_R1_MANAGER_ACCEPTANCE_REPORT.md`](V37_4_R1_MANAGER_ACCEPTANCE_REPORT.md#L28-L43)).

## Test evidence and limits

Executed, without contacting a provider:

- `.\.venv_win\Scripts\pytest.exe -q -p no:cacheprovider tests\test_v37_4_r1_trade_feed.py tests\test_v37_4_r1_api.py tests\test_v37_4_r1_frontend.py tests\test_v32_64_data_lane_separation.py::test_01_data_mode_parsing_and_fail_closed tests\test_v32_64_data_lane_separation.py::test_06_transport_guard_blocks_network tests\test_v32_64_data_lane_separation.py::test_08_provider_mode_fails_closed`
  - **17 passed; 1 setup error.** All R1 feed/API/frontend tests and the mode-parsing and transport-block tests passed. The provider-mode test did not reach its assertions: its `TestClient` fixture failed during startup because the scientific startup gate could not find `results/freeze/repaired_scientific_contract_manifest.json` under the temporary test DB path. This is not a provider-network attempt or evidence that the provider-mode route test passed.
  - The protected-file guard reported `PASS`; before/after manifest SHA-256 remained `d424b3c0dd43a0b4a91735a2050fd43315edd341d3f146655aad6698ec3ce031`.
- The isolated tests cover timestamp/receipt lag, duplicate handling, reconnect backoff with a mocked connection, injected-feed lifespan start/stop, route identity/unavailability, the descriptive-engine contract, and chart display ([`tests/test_v37_4_r1_trade_feed.py`](tests/test_v37_4_r1_trade_feed.py#L34-L90), [#L232-L266](tests/test_v37_4_r1_trade_feed.py#L232-L266), [`tests/test_v37_4_r1_api.py`](tests/test_v37_4_r1_api.py#L47-L153), [`tests/test_v37_4_r1_frontend.py`](tests/test_v37_4_r1_frontend.py#L6-L145)).
- Prior R1 evidence reports that received Bitstamp events were roughly 226 seconds behind receipt and correctly stale under the 60-second threshold; no real app/browser integration or long soak was completed ([`V37_4_R1_MANAGER_ACCEPTANCE_REPORT.md`](V37_4_R1_MANAGER_ACCEPTANCE_REPORT.md#L8-L12), [#L28-L43](V37_4_R1_MANAGER_ACCEPTANCE_REPORT.md#L28-L43)).

The executed tests do **not** prove automatic feed construction, authorized real-connection startup, cross-worker deduplication, or real socket shutdown. No provider, app network path, or live feed was started in this review.

## Minimum gated corrections after approval

1. Record owner/legal approval for the specific Bitstamp collection and use purposes, plus verified official terms/protocol/recovery evidence. Until then keep the authoritative gate false.
2. Add provider-specific approval/configuration to the existing data-mode contract; `provider` alone must remain insufficient. Do not add a bare boolean environment bypass.
3. Enforce the network gate immediately before every `start()` call, including an injected feed; add tests proving no connection attempt in fixture/offline/unapproved-provider modes.
4. Ensure only one designated ingestion worker owns the feed (or implement an explicit, tested cross-process ownership strategy); expose connection readiness separately from the non-blocking `start()` return.
5. Verify shutdown by asserting the thread has exited within its bound; sanitize transport errors before API exposure.
6. After approval only, test the real lifespan-to-API-to-frontend path under the approved scope, with explicit stale/unavailable behavior. Keep the 1-minute output descriptive/unvalidated until separately governed evidence supports any stronger claim.

**Research experiment:** `INCONCLUSIVE` — integration tests are deterministic; live authorization and operational verification are blocked.  
**Prospective evidence:** `NOT_STARTED` — no qualifying prospective accumulation established here.  
**Model authorization:** `OFFLINE_RESEARCH_ONLY`.  
**Live trading:** `DISABLED`.
