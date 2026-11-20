# BTCognitive V32.51 — Safe Feature QA and Data-Integrity Follow-Up

**Run ID:** `20261027_072352_0530`  
**Run start:** `2026-10-27T07:22:55.4741664+05:30`  
**Repository:** `C:\Projects\BTCognitive\BTCognitive`  
**Branch / HEAD:** `main` / `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Release verdict:** **FAIL**  
**Integrity incident:** **OPEN — root cause and authoritative data-source/recovery decision unresolved**

## Executive decision

This was a deliberately constrained V32.51 QA pass. It captured the repository and protected-data baseline, performed read-only writer/source tracing, and ran only checks whose code paths were inspected and isolated from the protected market parquet. No application server or browser session was started, reused, stopped, or reconfigured. No source code or pre-existing user file was edited, reverted, removed, or overwritten. The only new files are this run's QA artifacts under `research/reports/v32_51/`.

The five protected files matched their V32.51 start-of-run hashes at the end of the run. This **does not resolve** the prior integrity incident: `data/raw/ohlcv.parquet` already began this run at `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`, not at the previously recorded `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c`. The actual writer remains unknown. The integrity gate remains **FAIL**.

The application is not “fully tested.” Browser/API integration, market-data mutation paths, tournament evidence, entry/monitor lifecycle, research/journal interactions, and performance budgets were not exercised. This is due to the open data-integrity incident, the absence of an API listener on the previously used QA ports, and the lack of verified fixture-root overrides for the relevant tests.

## Phase 1 — baseline and safety boundary

### Git and workspace

- Initial Git state was captured before tests in [the timestamped run directory](./20261027_072352_0530/).
- The baseline had **453 dirty/untracked paths: 46 tracked modifications and 407 untracked paths**. These include existing API/engine changes, ledgers, user data, reports, and extensive screenshots. They were preserved.
- The final comparison found no missing baseline paths and no changed status for any baseline path. There were 16 additional Git-visible paths, all under this run's QA report directory; some generated CSV deliverables are locally present but ignored by Git.
- The initial tracked diff was preserved as `baseline_worktree.diff`; baseline and final status are separately captured. Git emitted line-ending warnings while reading diffs; no source file was rewritten by this QA.
- No branch creation, commit, push, reset, checkout, stash, clean, source edit, or deletion occurred.

### Processes, ports, services, and collectors

The initial read-only capture includes all listeners and matching process command lines. Relevant observations:

- No listener on **8096** or **8102**; no API process was available. The shared browser attachment referenced those URLs, but this run did not interact with those pages.
- Port **9222** was already owned by headless Chrome PID 23872 before test execution. It was not used or stopped.
- Other pre-existing listeners included Windows system services, MySQL on 3306, and Ollama on 11434. They were left untouched.
- No matching prospective/shadow worker, ingestion CLI, FastAPI/uvicorn process, or BTCognitive scheduled task was visible.
- `data/.prospective_shadow_runner.lock` exists as pre-existing untracked data and records PID 31676 from 2026-10-23. That PID is not running; the lock and status file were not modified. `data/.prospective_worker.lock` is absent. The old shadow status telemetry is not evidence of a currently active collector.
- The only application-related process started by this run was the bounded, single-file pytest process; it exited successfully. No application service was started. Test process and output are recorded in the run artifacts.

### Active API/data-source configuration

No API process or active runtime configuration was observable. Source inspection found development mode as the code default if `BTC_ENVIRONMENT`/legacy `ENVIRONMENT` are unset. The frontend is served from `web/` by the normal API application. Runtime data paths in collector code default to repository `data/raw/ohlcv.parquet` unless a constructor override is supplied. No override was verified for the broader integration-test groups, so they were not run.

## Protected-file integrity

Start and end SHA-256, sizes, and modification times are recorded in [protected_file_integrity.json](./protected_file_integrity.json). All five remained stable **during this V32.51 run**:

| Protected path | V32.51 start/end SHA-256 | Size | Within-run result |
|---|---|---:|---|
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | 3,385 | unchanged |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | unchanged |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | 12,744 | unchanged |
| `data/raw/ohlcv.parquet` | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` | 2,329,745 | unchanged this run; **prior mismatch remains open** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | 2,284,681 | unchanged |

The backup's hash differs from both the historical pre-incident hash and the current primary parquet. It was not treated as an authorized recovery source.

## Read-only protected-parquet writer investigation

The investigation was source-level only. It did not invoke any writer, sync method, worker CLI, API route, or scheduled job.

| Writer or path | Evidence and scope |
|---|---|
| `ProspectiveEvidenceWorker.sync_live_candles` | `engine/prospective_worker.py` imports `DEFAULT_OHLCV_PATH` from `engine.har_24h_features`; its constructor accepts `ohlcv_path` but defaults to that repository path. With valid closed Coinbase candles, the method merges and atomically replaces the configured parquet. The `--once` default enables live candle sync. |
| `ShadowFeedRunner.sync_candles_to_storage` | `engine/shadow_feed_runner.py` defines `DEFAULT_OHLCV_PATH` as repository `data/raw/ohlcv.parquet`; the constructor allows an explicit path override. CLI single-shot and loop modes sync by default unless `--no-sync` is supplied. |
| General ingestion CLI | `data/ingest.py::save_raw(df, name)` writes `DATA_RAW_DIR/<name>.parquet`; its `__main__` dataset tuple calls it with `name="ohlcv"`. This is a direct write path when the CLI runs. |
| Historical ingestion CLI | `data/ingest_real_historical.py::download_binance_history` writes its module-level `OHLCV_PATH` directly. |
| Coinbase gap-backfill CLI | `scripts/backfill_coinbase_data_gaps.py::execute_backfill(apply_to_main=True)` writes `data/raw/ohlcv.parquet`; its `__main__` invokes that default. |
| Generic parquet export | `engine/feature_store.py::FeatureStore.export_to_parquet` accepts an arbitrary caller-supplied output path. The discovered test caller supplies a temporary path; no production call site to the protected path was found in the repository search. |
| API startup / data readers | `api/server.py` initializes `FeatureCache`; `engine/feature_cache.py::initialize` reads the protected parquet and computes features in memory. `api/routes_tournament.py`, `api/routes_research.py`, and `engine/forecast_engine_15m.py` also contain reads. The API lifespan starts a research-alert evaluator but has no direct protected-parquet writer. |
| Separate 15m ingestion | `engine/coinbase_15m_adapter.py`, used by the forecast and 15m market route, writes `data/raw/coinbase_15m.parquet` by default, not the protected hourly parquet. This route can mutate that separate cache and was not invoked. |

Entrypoints and invocation references were found in `README.md`, `docs/PROSPECTIVE_WORKER_RUNBOOK.md`, `scripts/run_prospective_worker.ps1`, and worker `__main__` blocks. The scheduled-task check found no matching task in this environment. No matching worker process was visible; the shadow lock PID is stale. Those facts narrow potential mechanisms but cannot prove which process wrote the primary parquet on 2026-10-26. No root cause or authoritative recovery decision exists.

## Test execution and results

Tests were run serially. No full-suite or API/browser group was started.

| Command | Result | Duration / notes |
|---|---|---|
| `node --check web\app.js` | PASS, exit 0 | 267 ms |
| `node tests_frontend.js` | PASS, exit 0 | 450 ms; formatters, API client caching/deduplication/429, endpoint resolution, and source-contract assertions; this is not browser QA |
| In-memory `ast.parse` over modified and untracked Python source | PASS, 87 files, 0 syntax errors | 5,213 ms; no imports/execution or bytecode writes |
| In-memory `compile(source, filename, "exec")` over modified and untracked Python source | PASS, 87 files, 0 errors | 1,549 ms; no imports/execution or bytecode writes |
| `.venv_win\Scripts\pytest.exe -q -p no:cacheprovider --basetemp "<run-dir>\pytest_tmp" tests/test_v32_50_chart_forecast_runtime.py` | PASS, **2 passed**, exit 0 | pytest-reported 0.72 s; command wrapper wall time 129.739 s including interpreter/import startup. `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPYCACHEPREFIX=<run-dir>\pycache`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. The test module only exercises the source-interval freshness helper; no API, network, parquet, or ledger access. Protected hashes matched before/after. |

Exact logs and JSON result records are in the timestamped run directory. Node and Python checks were also verified not to call application APIs or write protected paths. No test-generated bytecode/cache was written into the repository.

### Why broader suites and browser tests were not run

The focused V32.43–V32.50 tests use `TestClient(app)` and some test paths directly read protected files or start application logic with repository-default data paths. Other tests invoke workers whose default `ohlcv_path` targets the protected parquet. Their full integration graph and path overrides were not proven disposable. In accordance with the safety gate, those suites were skipped rather than relying on test names, expected failures, or post-run hashes.

No normal API listener was present at 8102 (or 8096), and the available 9222 Chrome instance pre-existed this run. No browser session was opened or controlled. Therefore actual route response bodies, page behavior, pointer/keyboard retry, responsive CSS viewport, and console/network traces are **NOT_RUN**, not passes.

## Prior 51-failure triage limitation

The V32.50 summary reports **51 failed** in the broad suite, but the complete output containing those 51 test IDs was not retained in the workspace. The available `failing_tests.log` and `full_test_run_current.log` are from 2026-10-20 and show older runs, not V32.50. `.pytest_cache/v/cache/lastfailed`, timestamped 2026-10-26 23:17, contains **57** IDs; it is not sufficient evidence to reconcile the 51 reported failures. The 57 entries were preserved, but none were blindly rerun because several test paths read protected files, use repository-default data, or invoke API lifespan code. See [failure_triage.csv](./failure_triage.csv): each cache-only ID is explicitly marked unreconciled and not retested. Thus the requirement to map and retest all 51 failures is **BLOCKED**; no failure is waved away as baseline or flake.

## Feature QA status

See [feature_matrix.csv](./feature_matrix.csv) for the feature-level register. This run verified static code/source contracts and the isolated forecast freshness helper; it did not reproduce a user-visible defect. No code change was made.

Current critical blockers:

1. **P0 — protected-data root cause:** exact process/writer is unknown; no recovery authority. Release gate remains FAIL.
2. **P0 — live integration path not exercised:** normal API absent; API/browser acceptance, app health/offline behavior, forecast retry pointer interaction, navigation, and responsive layouts are not verified in V32.51.
3. **P1 — prior full-suite failures:** claimed 51 cannot be reconciled to 57 cached IDs; failure-by-failure retest is blocked by data-path safety.
4. **P1 — no current performance profile:** no app/browser/API stages measured this run. Prior V32.50 timings are non-comparable observations only.
5. **P1 — active attempt and monitor:** no disposable seeded attempt/API path was constructed; lifecycle and immutable snapshot behavior remain unverified here.
6. **P1 — dead-file deletion gate:** no candidate met a proof-of-deadness standard. Dirty/untracked files and research artifacts were excluded from deletion. No file was deleted.

## Runtime measurement

[performance.csv](./performance.csv) records the current QA command timings separately from historical V32.50 product observations. No new application p50/p95/max value was measured. Previous terminal/forecast/What-If samples are non-comparable or under load; they do not prove a performance improvement or target pass. No optimization was attempted.

## Dead-file audit and cleanup

[dead_file_audit.csv](./dead_file_audit.csv) documents the protected-data writer paths inspected and the explicit keep rationale. The baseline includes 407 untracked paths, many of which are ledgers, source, reports, screenshots, and other user artifacts. They are ineligible for deletion under the task's preservation rule. No source file was proven dead through the required exhaustive static/dynamic/build/docs/runtime reference checks. Cleanup is therefore a **no-op**, not a claim that every repository file was proven live.

[deleted_file_manifest.csv](./deleted_file_manifest.csv) contains only its header: no file was removed. Existing reports, V32.50 artifacts, generated screenshots, lock files, and user data were not cleaned up.

## Deliverables and browser evidence

- [Machine-readable QA summary](./qa_summary.json)
- [Feature matrix](./feature_matrix.csv)
- [Performance record](./performance.csv)
- [Prior failure triage](./failure_triage.csv)
- [Dead-file audit](./dead_file_audit.csv)
- [Deleted-file manifest](./deleted_file_manifest.csv)
- [Protected-file integrity and writer investigation](./protected_file_integrity.json)
- [Timestamped run evidence, logs, initial/final status, and diff](./20261027_072352_0530/)
- [Browser availability record](./browser_traces/browser_status.json)
- [Screenshot capture status](./screenshots/capture_status.json)

No V32.51 screenshots or browser network traces were captured because the app service was absent and the shared browser/CDP process was pre-existing. Prior V32.50 screenshots and trace artifacts remain untouched and are not represented as V32.51 evidence.

## Governed decision

- **Research experiment:** `INCONCLUSIVE` — software checks do not establish forecasting skill.
- **Prospective evidence:** existing telemetry says `COLLECTING` but is dated 2026-10-17 and was not revalidated; current status is unverified.
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`.
- **Live trading:** `DISABLED`.
- **Validated trading edge:** none claimed. Software QA, code tests, historical replay, and backtests do not validate a profitable trading edge.
