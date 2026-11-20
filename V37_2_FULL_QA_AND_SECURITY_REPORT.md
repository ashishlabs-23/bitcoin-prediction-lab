# V37.2 Full QA and Security Report

**Assessment date:** 2026-11-04  
**Branch:** `milestone/v35.3-critical-remediation`  
**HEAD:** `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Scope:** Read-only application/security audit and safe QA feasibility check. This report is the only file intentionally created for this task.

## 1. Executive outcome

- **QA:** No tests executed. The focused pytest command could not start because the configured `venv` interpreter points to a Python 3.12 executable that is absent. No test pass is claimed.
- **Security:** A medium-severity authorization/ownership gap was identified in the user-position and manual-journal API routes. CORS is origin-configured but is not authentication. Effective deployment configuration was not verified.
- **Runtime and network:** Execution disablement, external-network guards, and generic error handling are source-confirmed only. No server, provider request, external network, live market data, or protected holdout observation was accessed.
- **Research boundary:** No model, trading, or research authorization was inferred from application status or synthetic test fixtures.

## 2. Scope and safety

The review was limited to source/configuration inspection, repository status snapshots, integrity-only SHA-256 checks against the V37.0 manifests, and an attempted focused pytest command. The source review did not probe endpoints or reproduce an exploit. No source or test files were changed. Protected files were streamed only to compute integrity hashes; no protected observations were parsed, analyzed, or used.

The command that was considered for focused testing excluded `test_btcusdt_candle_request_is_reproducibly_mislabeled_as_btcusd`: its valid BTC-USD/1h route path can read `data/providers/bitstamp/BTCUSD_1h.parquet` (`api/market_monitor_routes.py:351-364`). That would violate the no-protected-observation-read constraint. The remaining selected tests use mocked responses, synthetic payloads, and in-process FastAPI `TestClient` requests. The pytest session-level conftest also redirects its SQLite databases to a new disposable temp directory, blocks non-loopback socket connections and protected writes, and compares protected-file hashes (`tests/conftest.py`).

## 3. Baseline, integrity, and status races

### Git baseline

At the initial snapshot:

- `git status --short --untracked-files=all`: **1,721 entries** — **116 modified**, **1,605 untracked**, **0 staged**.
- Sorted status-list SHA-256: `ccf84cc2bb86a1bc6792fc87a53b9e7383ea1ec5189e2408f1067bdf8b69b5b8`.
- `git ls-files 'V37_0*'` returned no tracked V37.0 files; the V37.0 reports and related material are local untracked artifacts.

Immediately before creating this report, status contained **1,722 entries**. The pre-write V37-related sample included `V37_2_FRONTEND_AND_BROWSER_QA_REPORT.md` and `V37_2_LIVE_DATA_AND_PROVENANCE_REPORT.md`, which were not part of this task. Since other agents may create reports concurrently, the difference between snapshots and the authorship/timing of individual status changes cannot be attributed from these snapshots. This report does not inspect or reconcile other agents’ files.

### V37.0 integrity manifests

The available V37.0 baseline manifests were read as integrity metadata only. Both checks were performed before test execution was attempted:

| Manifest | Expected | Matched | Missing | Mismatched |
|---|---:|---:|---:|---:|
| `initial_protected_assets.tsv` | 213 | 213 | 0 | 0 |
| `initial_protected_hashes.tsv` | 39 | 39 | 0 | 0 |

These are byte-integrity comparisons, not data inspection. The same two checks are to be repeated at the end of this audit; results are recorded in the closeout section below.

### Prior V37.1 status

`V37_1_APPLICATION_RUNTIME_REPORT.md` states that the application was intentionally not started because imports/startup can read protected OHLCV data; the guarded attempt aborted before opening that data or binding a port. It classifies application status as `APPLICATION_PARTIALLY_FUNCTIONAL`, research validation as `RESEARCH_VALIDATION_BLOCKED`, prospective evidence as `NOT_ESTABLISHED`, model authorization as `OFFLINE_RESEARCH_ONLY`, and live trading as `DISABLED`. Those runtime statements are historical V37.1 findings, not new runtime verification by this audit.

## 4. Test accounting

`pytest.ini` sets `addopts = -m "not network"`; the default suite configuration excludes tests marked `network`. No network-marked test was run.

The following focused command was attempted:

```text
.\venv\Scripts\python.exe -m pytest tests\test_security_auth.py tests\test_v37_2_backend_contracts.py -q -k 'not btcusdt'
```

It exited with code **103** before pytest started:

```text
No Python at '"C:\Users\PC\AppData\Local\Programs\Python\Python312\python.exe'
```

| Measure | Result |
|---|---:|
| Pytest collection reached | No |
| Tests discovered by this command | 0 |
| Tests executed | 0 |
| Tests skipped/deselected by pytest | 0 |
| Test assertion failures | 0 |
| Command/environment failures | 1 |

The source files contain five unit cases in `tests/test_security_auth.py` and seven backend-contract cases in `tests/test_v37_2_backend_contracts.py`; one backend case was excluded in the attempted selector because it can read the local Bitstamp Parquet file. These are source counts, **not** pytest discovery results. No retry was made. Integration tests importing `api.server`, application startup, browser tests, and the broad suite were not run. The broad suite was not established as safe given the 1,700+ pre-existing worktree entries, the known startup reads, and tests that may interact with persistent research state. There is no current V37.2 test pass or end-to-end acceptance claim.

## 5. Security and application findings

The following findings are source/configuration review only; they are not runtime-confirmed.

### 5.1 Authorization and ownership gap — Medium

`api/server.py:250-251` registers `api.routes_user_positions` and `api.routes_manual_journal`. The reviewed route handlers do not apply authentication or ownership checks:

- Position list/detail and open/partial-exit/close handlers: `api/routes_user_positions.py:119-123, 173-176, 196-220, 233-245, 257-268`.
- Journal list/detail and entry/exit/adjust handlers: `api/routes_manual_journal.py:79-88, 127-136, 98-115, 139-153, 162-174`.

The shared tracker/journal implementations can return records based on caller-supplied user identifiers (or without one) and allow record operations by identifier without an authenticated-principal ownership check. This can expose or alter user-entered position and journal records where these routes are reachable. It is an application privacy/integrity issue; these routes are not evidence of broker order execution.

**Remediation direction:** require authentication, derive identity from the authenticated principal instead of request fields, and enforce per-record ownership for reads and mutations before exposing these routes.

### 5.2 CORS is not an authorization control

`config/security.py:97-101` defines an explicit environment-configured origin list, and `api/server.py:229-235` enables credentials for CORS. This is not a substitute for route authentication. The effective production origin values and any upstream deployment controls were not verified.

### 5.3 Execution disablement

Source indicates fail-closed execution settings: `config/security.py:36` declares trading disabled; `api/server.py:161,186` sets the live engine to stopped; and the arena paper-trade POST handlers return `DISABLED` (`api/routes_arena.py:155-187`). V37.1 additionally records that health flags declare `live_trading_enabled`, `order_submission_enabled`, and `trading_enabled` false. This audit did not start the app or verify those values over HTTP. No order placement or broker execution was attempted.

### 5.4 Outbound network gates

The current data-mode implementation reports external networking disabled (`engine/data_mode.py:100-121`). `api/market_drivers.py:60-61` checks `assert_no_external_network` before outbound HTTP; the reviewed Coinbase/Bitstamp access paths also guard provider access. These are source-confirmed boundaries. No provider request, external target, or network-marked test was used; runtime enforcement was not independently exercised.

### 5.5 Configuration and error handling

The application has configured security middleware and the global unhandled-exception handler returns a generic response; HTTP error details are sanitized (`api/security_middleware.py:213-229`). Source inspection does not establish the deployment’s effective secrets, CORS allowlist, host policy, proxy/access-control configuration, or runtime error behavior.

### 5.6 No-fabrication / unavailable-value controls

Existing focused tests include assertions for `DATA_UNAVAILABLE`, null market/forecast values, empty candles/drivers, and sanitized provider errors (`tests/test_workstream4_qa_contracts.py`; `tests/test_v37_2_backend_contracts.py`). The V37.1 report also records that market observations and cache freshness remained unverified. These controls were **not executed in this audit**, and no synthetic output is represented as observed market data.

## 6. Separate application and research classification

### Application

- **Classification:** `APPLICATION_PARTIALLY_FUNCTIONAL` per V37.1; runtime remains **NOT VERIFIED** in this audit.
- **Security disposition:** authorization/ownership gap identified in position and journal APIs; deployment exposure is not established, but the code-level gap should be resolved and regression-tested before declaring API security acceptance.
- **Execution/network disposition:** source states disabled/blocked; no runtime claim.
- **QA disposition:** no tests executed because the configured interpreter could not start.

### Research

- **Research validation:** `RESEARCH_VALIDATION_BLOCKED` (V37.1 status; not changed or re-evaluated here).
- No historical replay, training, tuning, calibration, model selection, performance calculation, or holdout analysis was performed.
- **Prospective evidence:** `NOT_STARTED` / `NOT_ESTABLISHED`.
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`.
- **Live trading:** `DISABLED`.

## 7. Governed decisions

- **Research experiment:** `INCONCLUSIVE` — this was an application QA/security audit, not a research experiment.
- **Prospective evidence:** `NOT_STARTED`.
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`.
- **Live trading:** `DISABLED`.

## 8. Closeout integrity and status

The final repository snapshot was:

- Branch: `milestone/v35.3-critical-remediation`
- HEAD: `25d483f4c3646661b57311de9d0b53d2be881adb`
- `git status --short --untracked-files=all`: **1,723 entries**, **0 staged**.
- Sorted status-list SHA-256: `6b5537abf33d6fb81b38fe52cb65f6429dc70d8a936fbfbfd7991b5a31152917`.
- This report exists as an untracked file. The final V37-related status sample also contained two V37.2 reports created by other workstreams.

The status count changed from 1,721 at the initial snapshot to 1,722 immediately before this report was created, then 1,723 at closeout. The report itself accounts for its own new untracked entry between the latter snapshots; attribution of the preceding concurrent status change is not established. No status entries were staged by this task.

The V37.0 asset/source hash checks **passed at the start** (213/213 and 39/39). No end-of-task hash recheck was performed: V37.2 report artifacts from other workstreams appeared during the audit, indicating concurrent file creation. In accordance with the instruction not to compare files concurrently with agents, a second comparison was not considered safe. No protected observations were parsed or analyzed, and the final check result is therefore **not available**, not assumed to match.

## 9. Manager final reconciliation

This section supersedes the agent-only test and integrity status above. The initial focused-test attempt used an unavailable `.\venv\Scripts\python.exe` and executed zero tests. The manager reran focused checks using the configured `.venv_win` interpreter; the test results below are actual executions, not source counts.

### Completed validation

| Command | Result |
|---|---|
| `.\.venv_win\Scripts\pytest.exe tests\test_security_auth.py tests\test_route_authorization.py -q` | **8 passed** in 224.69s; one Pydantic deprecation warning. Protected-file guard passed (1,848 files, identical before/after manifest SHA-256). |
| `.\.venv_win\Scripts\pytest.exe tests\test_v37_2_backend_contracts.py -q` | **8 passed** in 2,662.37s, including BTCUSD-only rejection and the no-fabricated-position-context regression. Protected-file guard passed (1,848 files, identical before/after manifest SHA-256). |
| `.\.venv_win\Scripts\pytest.exe tests\test_workstream4_qa_contracts.py tests\test_entry_contracts_and_resolver.py tests\test_live_block_resolver.py tests\test_post_repair_outcome_resolver.py tests\entry_tp_sl -q` | **118 passed** in 14.55s. |
| `npm test` | **Passed**; frontend test script reported `All Frontend Unit Tests Passed Successfully!` (script emits no numeric test count). |
| `npm run check` | **Passed**; JavaScript syntax check. |
| Targeted whitespace checks | **Passed** for the changed Python sources/tests and V37.2 reports (retaining intentional Markdown hard breaks). The unscoped `git diff --check` reports pre-existing trailing whitespace in unrelated dirty files including `README.md`, `engine/price_forecast_engine.py`, and `research/post_repair_block_builder.py`; those were not changed. |

The full test suite was not run. Application startup and some tests can load protected market observations or interact with persistent research state, and the targeted API contract run itself took 44m22s. No browser E2E pass is claimed; the browser report records the local-fixture and external-script blockers.

### Manager integration defect and correction

In addition to the BTCUSDT/BTC-USD identity defect documented in the backend report, final review found that `api/routes_user_positions.py` supplied hard-coded `0.45`/`0.55` directional probabilities and a fixed `MOMENTUM_TRENDING`/`MODERATE` context to both position risk endpoints. No corresponding model or regime result was supplied by those routes. The manager removed these fabricated arguments; without actual inputs the copilot now serializes empty forecast/regime contexts and does not issue those unsupported conflict alerts. A synthetic regression verifies both handlers omit the inputs while replacing the quote path, so it performs no provider request.

The static authorization/ownership gap in position and manual-journal routes remains unresolved. Remediation requires an authenticated-principal/ownership contract and deployment exposure decision; this milestone did not invent an identity mapping or weaken route behavior without that contract.

### Final integrity and repository state

The final V37.0 baseline recheck found:

| Manifest | Expected | Matched | Missing | Mismatched |
|---|---:|---:|---:|---:|
| Protected assets | 213 | 213 | 0 | 0 |
| Protected source hashes | 39 | 39 | 0 | 0 |

Final measured asset bytes matched both length and SHA-256. These checks do not imply that protected observations were admissible for research; none were opened for this milestone's backtest evaluation.

At the last captured pre-manager-report Git snapshot: branch `milestone/v35.3-critical-remediation`, HEAD `25d483f4c3646661b57311de9d0b53d2be881adb`, 1,725 status entries, and zero staged entries. This snapshot includes pre-existing worktree content, V37.2 workstream reports, the synthetic contract test, and the manager's uncommitted changes. The final acceptance report adds one new untracked file. No branch, commit, push, reset, stash, or discard operation was performed.

### Final disposition

- Application: `APPLICATION_PARTIALLY_FUNCTIONAL`; targeted synthetic API contracts pass, but production browser/runtime acceptance and route ownership authorization are not cleared.
- Browser: `BROWSER_QA_PARTIAL`; no rendered-browser pass or screenshots.
- Data: `LIVE_DATA_UNAVAILABLE`; current terms were not established, so the one-time Bitstamp request was not sent.
- Research: `INSUFFICIENT_DATA` and `RESEARCH_VALIDATION_BLOCKED`; no admissible historical backtest or forecast performance estimate.
- Experiment: `INCONCLUSIVE`; prospective evidence `NOT_STARTED`; models `OFFLINE_RESEARCH_ONLY`; live trading `DISABLED`.
