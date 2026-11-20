# BTCognitive V32.50 — Runtime, Forecast Overlay, and UI QA

**Assessment date:** 2026-10-26  
**Release verdict:** `FAIL`  
**Research experiment:** `INCONCLUSIVE`  
**Prospective evidence:** `NOT_STARTED`  
**Model authorization:** `OFFLINE_RESEARCH_ONLY`  
**Live trading:** `DISABLED`

## Executive decision

The Terminal now renders the real API directional classifier in a default-on chart overlay, displays raw classifier probabilities and provenance, and reports stale, delayed, timeout, and evidence-unavailable states. A responsive grid sizing defect was corrected. A delayed-forecast rendering defect and inaccurate evidence-blocked wording were also corrected. A measured exact-request duplication path for the analytical What-If panel now deduplicates identical in-flight calculations without caching completed results.

Release is **FAIL** because the protected `data/raw/ohlcv.parquet` file no longer matches its pre-QA SHA-256. The mismatch was detected after the broad test run; its exact writer could not be attributed. QA stopped the isolated API process, verified port 8102 closed, and did not restore, rewrite, or otherwise modify the protected file. The remaining chart-marker alignment, verified tournament evidence, active-attempt monitoring, and performance comparison gates are also unresolved.

The full suite is not a clean release signal: it completed with 1,604 passed, 51 failed, and one deselected. The suite ran while the normal-app QA API was active and source edits were being made; the protected-data failures show the changed parquet hash. Do not interpret all other broad-suite failures as introduced by V32.50 or as pre-existing without a separate clean, isolated rerun.

## Implemented changes

- [web/app.js](../../web/app.js): reads the nested `directional_forecast` model response; renders direction, horizon, raw probabilities, model ID, generated timestamp, freshness, governance, and explicit status/retry details. No directional price path is fabricated. Delayed output retains its supplied direction/probabilities but is labeled historical-only; stale output does not display a current direction. Probability rendering now guards finite values. Forecast marker sets replace prior markers, and marker-update errors are logged.
- [web/app.js](../../web/app.js): makes Analyse outcomes distinguish `BACKTEST EVIDENCE UNAVAILABLE` from `NO QUALIFYING SETUP`; stage progress, elapsed time, request ID, and backend timing remain visible. Analyse remains one action; Enter remains separate.
- [web/app.js](../../web/app.js): deduplicates identical concurrent What-If POST calculations by the exact endpoint and serialized payload. It does not reuse completed results.
- [web/styles.css](../../web/styles.css): changes the responsive workstation grid track to `minmax(0, 1fr)` and constrains the mobile forecast overlay to a scrollable 190 px height.
- [web/index.html](../../web/index.html): cache-busts the modified app and stylesheet.
- [engine/forecast_engine_15m.py](../../engine/forecast_engine_15m.py), [engine/regime_strategy_tournament.py](../../engine/regime_strategy_tournament.py), and [api/routes_tournament.py](../../api/routes_tournament.py): retain source-candle freshness semantics and expose integrated stage timing and explicit non-executed tournament-arm state.
- [tests_frontend.js](../../tests_frontend.js), [tests/test_v32_48_integrated_analyse_and_tournament.py](../../tests/test_v32_48_integrated_analyse_and_tournament.py), and [tests/test_v32_50_chart_forecast_runtime.py](../../tests/test_v32_50_chart_forecast_runtime.py): add/extend UI, runtime, and source-granularity coverage.

## Normal-app browser evidence

The test used the normal `api.server:app` on isolated port 8102 and the Terminal frontend. The simulator attempt ledger was redirected to the session-only file `v32_50_attempts.jsonl`. Coinbase REST supplied the chart window; no live trading or real capital was used.

One browser Analyse request sent 349 closed `BTC-USD` hourly candles with source `COINBASE_EXCHANGE_REST`, timeframe `1h`, and `auto_tournament=true`. It returned HTTP 200. The final captured browser request took 187 ms; the UI reported a 130.5 ms server total for that single run. Two candidates passed preliminary screens, but the registered verified walk-forward evidence did not match and the required fresh three-arm inputs were unavailable. The tournament was therefore tagged `NOT_RUN_UNVERIFIED_EVIDENCE`; no winner was presented, the button returned to enabled, and the UI displayed `BACKTEST EVIDENCE UNAVAILABLE`. The isolated attempt view remained `0 / 0 eligible attempts`. This is a valid abstention/evidence blocker, not a successful backtest.

The actual forecast endpoint supplied a categorical `UP` classifier for horizon `1h`, model `directional-gbm-1h-v1`, `P(UP)=0.5585`, `P(DOWN)=0.4415`, source granularity 900 seconds, and a 17:15 UTC forecast origin. The chart's latest closed hourly bar was 16:00 UTC. The marker was intentionally not moved onto a mismatched or unclosed chart bar; the overlay visibly says “Marker pending: no matching closed bar.” This prevents time misalignment, but **the required marker-on-latest-closed-bar acceptance remains blocked** for this real response.

The model did not provide a directional price path. The visible persistence baseline and nominal bands remain separately labeled and are not represented as a model path or calibrated uncertainty interval.

The delayed-state regression was exercised with a browser-only response transform: it started from the actual API response and changed only the freshness field to `DELAYED`. The overlay showed the supplied UP direction and probabilities with a `DELAYED (historical)` label, a historical-only notice, and no NaN/undefined output. The browser route was removed and the real forecast request recovered.

A deliberately stalled browser forecast interception exceeded the client's 8-second bound. The UI displayed `REQUEST_TIMEOUT`, retained the last successful timestamp, kept the price chart available, and left Retry usable. After removing the interception, the real endpoint returned HTTP 200 and the overlay recovered. This was a timeout/recovery check, **not** a deterministic 5xx test.

The current actual model response changed between FRESH and DELAYED during QA. The UI exposed each status; delayed output was not treated as a current signal after the fix.

## Responsive browser artifacts

Screenshots were captured from the actual normal-app browser page:

- [Desktop screenshot](./artifacts/v32_50/terminal_desktop_1280x800.png) — PNG 1600×1000 physical pixels.
- [Tablet screenshot](./artifacts/v32_50/terminal_tablet_768x1024.png) — PNG 960×1280 physical pixels.
- [Mobile screenshot](./artifacts/v32_50/terminal_mobile_375x667.png) — PNG 469×834 physical pixels.

The responsive correction was verified at the requested mobile size: the chart no longer expands past the effective page width, and the overlay is bounded to 190 px and scrollable. The integrated browser reported CSS `innerWidth` values that varied from the requested Playwright viewport dimensions (for example 354 for a requested 375 px viewport and 474 for a requested 768 px viewport); therefore the exact 1280/768/375 CSS viewport acceptance is **BLOCKED**, despite the named screenshots and no clipping at the measured effective widths. The mobile forecast overlay is visible; the marker remains pending because of the data-time mismatch above.

## Runtime measurements

See [the performance CSV](./v32_50_runtime_performance.csv), [the browser trace](./artifacts/v32_50/normal_browser_network_trace.json), and [the scenario ledger](./artifacts/v32_50/scenario_ledger.csv).

There is **no defensible before/after optimization claim**. The V32.49 reload observations did not retain raw samples for p50/p95, and the forecast baseline samples mixed cold and warm runs. The separate warm 20-request forecast sample was much faster but is not a like-for-like comparison. One browser Analyse sample and one 5-second What-If observation are insufficient to establish stable p95 performance. The What-If observation was made while the broad pytest suite was consuming resources: 31 requests in 5 seconds, 20 unique payloads, 11 repeated exact payloads, nearest-rank p50 2,402 ms, p95 8,966 ms, max 9,555 ms. It motivated in-flight deduplication, but there was no post-fix browser measurement before the integrity gate stopped QA.

No valid measurements were obtained for 500-candle chart rendering p95, multi-sample cold/warm Terminal TTI, per-arm tournament runtime, verified integrated tournament runtime, Enter persistence, or Research/Journal load. Tournament arms were not run, so the 10-second full-analysis target cannot be judged.

## Tests

Passed:

- `.venv_win\Scripts\pytest.exe tests\test_v32_43_strategy_tournament_and_smart_entry.py tests\test_v32_44_smart_entry_independent_audit.py tests\test_v32_45_workflow_acceptance.py tests\test_v32_46_navigation_and_terminal_consolidation.py tests\test_v32_47_analyse_selection_and_anomaly_monitor.py tests\test_v32_48_integrated_analyse_and_tournament.py tests\test_v32_49_scenario_qa.py tests\test_v32_50_chart_forecast_runtime.py -q` — **118 passed in 26.19 s**. This run preceded the final JavaScript-only What-If deduplication edit.
- `node --check web\app.js` — passed after the final JavaScript edit.
- `node tests_frontend.js` — passed after the final JavaScript edit.
- The same V32.43–V32.50 focused Python suites were run earlier with the V32.50 forecast tests and passed; no Python source changes followed those tests.

Broad suite:

- `.venv_win\Scripts\pytest.exe -q` — **1,604 passed, 51 failed, 1 deselected, 9 warnings in 1,204.74 s**.
- Failures include legacy dataset/schema expectations, scenario endpoint contracts, frontend text contracts, and three protected-file hash assertions. The full run overlapped normal-app QA, resource contention, and source edits; it is not a clean baseline comparison. Do not claim the broad suite passes.

## Protected-data integrity incident

The following four protected files still match their recorded pre-QA hashes. `data/raw/ohlcv.parquet` does not:

| Protected file | Pre-QA SHA-256 | Post-QA SHA-256 | Status |
|---|---|---|---|
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | unchanged |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | unchanged |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | unchanged |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` | **MISMATCH** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | unchanged |

The mismatching parquet's recorded last-write time was 2026-10-26 23:12:20 local time; its post-QA read contained 42,233 rows through 2026-10-26 16:00 UTC. An earlier broad-suite read observed 42,177 rows. The backup is not a byte-identical recovery source and was not used. The API log confirms Coinbase calls occurred during QA, but no file-write event identifies the writer; attribution remains **unknown**. The QA-owned API process was stopped by verified PID 16004, port 8102 was confirmed closed, and no related Python worker remained in the final process check. The protected parquet was not restored or rewritten.

**Read-only follow-up:** Source inspection found that the API lifespan initializes `FeatureCache` by reading the protected parquet and computing in memory; the API's periodic worker evaluates research alerts. The normal Terminal's 15-minute Coinbase adapter writes to the separate `data/raw/coinbase_15m.parquet`, not the protected hourly file. No direct API-startup writer of `data/raw/ohlcv.parquet` was found. Source-level code paths that can write the protected file include the standalone `ProspectiveEvidenceWorker` and `ShadowFeedRunner` (both default to `data/raw/ohlcv.parquet` and atomically replace it), plus explicit ingestion/backfill scripts. No matching scheduled tasks or dedicated worker/ingestion process were visible in the read-only system check; the process search matched its own PowerShell inspection command. Some inspected tests use temporary parquet paths or inject a 503 before the worker writes. These findings narrow possible mechanisms but **do not identify which process wrote the file**; an exited task/process or unobserved process remains possible. A subsequent read-only SHA check confirmed the mismatching file remained stable at `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`, and port 8102 remained closed.

## Blockers and next steps

1. **Data integrity:** owner must investigate the `ohlcv.parquet` hash change and provide an authoritative recovery/source-of-truth decision. Do not restore from the different-hash backup or run further tests that read/write the protected file until resolved.
2. **Chart marker:** supply a model/chart contract that can causally align the 15-minute-origin forecast to a *closed* displayed candle, or retain the explicit pending state. Do not anchor to the still-open 17:00 hourly bar.
3. **Tournament:** provide verified manifest evidence or complete aligned point-in-time inputs for fresh three-arm execution. Until then, the integrated tournament and eligible-entry lifecycle remain blocked.
4. **Entry policy and lifecycle:** the proposal price-deviation threshold is undeclared; Enter and active monitoring were not exercised because no eligible proposal existed.
5. **Performance:** rerun cold/warm measurements with no concurrent full test workload, at least 20 warm samples where practical, and exact requested CSS viewport sizes. Measure comparable before/after request counts and latencies after the integrity issue is resolved.
6. **Regression:** rerun focused and broad suites in a clean, isolated data environment only after owner resolution of the protected-file mismatch.

No validated trading edge is claimed. The classifier remains research-only; prospective evidence remains `NOT_STARTED`; live trading remains disabled.
