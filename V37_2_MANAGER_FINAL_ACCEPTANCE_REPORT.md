# BTCognitive V37.2 — Manager Final Acceptance Report

**Assessment date:** 2026-11-04  
**Project posture:** `ANALYSIS_ONLY`  
**Default mode:** `OFFLINE_RESEARCH_ONLY`  
**Branch / HEAD:** `milestone/v35.3-critical-remediation` / `25d483f4c3646661b57311de9d0b53d2be881adb`

## Executive decision

| Acceptance area | Decision | Basis |
|---|---|---|
| Application | `APPLICATION_PARTIALLY_FUNCTIONAL` | Focused synthetic API contracts pass and two data-integrity defects were corrected. Full runtime/browser acceptance and route ownership authorization remain unresolved. |
| Browser | `BROWSER_QA_PARTIAL` | Browser automation could not load the loopback fixture; external script dependencies prevented the app from rendering. No browser screenshots or completed UI E2E run exist. |
| Live data | `LIVE_DATA_UNAVAILABLE` | The one-time Bitstamp request was withheld because current public-data terms could not be established. No market-data request was sent. |
| Research/backtest | `INSUFFICIENT_DATA` / `RESEARCH_VALIDATION_BLOCKED` | Historical inputs are not admissible for this evaluation; no historical backtest or model-performance metric was produced. |
| Research experiment | `INCONCLUSIVE` | This milestone verifies selected application contracts; it does not establish a model or strategy result. |
| Prospective evidence | `NOT_STARTED` | No prospective observations were collected or evaluated. |
| Model authorization | `OFFLINE_RESEARCH_ONLY` | No model was promoted or authorized. |
| Live trading | `DISABLED` | No broker, order, or execution capability was enabled or used. |

This is not a release or research-validation pass. The evidence supports only the scoped synthetic checks and source/integrity findings documented below.

## Specialist assignments and outcomes

| Specialist | Assigned scope | Outcome |
|---|---|---|
| Agent 1 — Live market-data and provenance | Conditional Bitstamp public-data integration, timestamp/freshness and source review | Did not send the request because the prerequisite current-terms/permission check was unresolved. Reviewed local provenance metadata only; the minute CSV remains unverified. |
| Agent 2 — Quantitative analysis and backtesting | Research pipeline, causal alignment, outcome contracts, historical backtest admissibility | Mapped the pipeline and found no admissible dataset/contract basis for a historical replay. No training, replay, tuning, or metrics. |
| Agent 3 — Backend/API integration QA | Synthetic API contract checks and backend defect reproduction | Reproduced and documented BTCUSDT being accepted against a BTC-USD cache; the manager restricted the endpoint to BTCUSD and added a regression. |
| Agent 4 — Frontend/browser QA | Frontend cleanup review and real-browser acceptance | Frontend tests and syntax checks passed. Browser E2E remained partial because the local fixture was unreachable and external CDN scripts did not initialize the application. |
| Agent 5 — Regression/security/quality | Tests, security/config review, protected-asset integrity | Identified a static user-position/manual-journal ownership gap. Its first pytest attempt used a missing interpreter; the manager reran focused tests using `.venv_win`. |

The manager coordinated integration, made the limited backend changes listed below, reran the relevant tests, and rechecked protected hashes. No child agents were created.

## Defects resolved

### BTCUSD instrument identity

`api/market_monitor_routes.py::market_candles` accepted `BTCUSDT` even though its local fallback represented and labeled BTC-USD. The endpoint now rejects unsupported `BTCUSDT` requests before market-data access. The existing synthetic regression asserts rejection and fails if the dashboard/data-access path is reached. No separate BTC-USDT source was added.

### Fabricated position-risk context

Both list and detail paths in `api/routes_user_positions.py` supplied fixed `0.45`/`0.55` directional probabilities and a `MOMENTUM_TRENDING`/`MODERATE` regime without corresponding model or regime outputs. These arguments were removed. The risk copilot now receives no forecast/regime input from these routes and returns empty context rather than unsupported directional alerts. A synthetic regression tests both handlers with a mocked quote path.

No frozen research contract, data ledger, model, protected dataset, or trading control was modified.

## Changed and delivered files

### Code/test changes made during V37.2

- [api/market_monitor_routes.py](./api/market_monitor_routes.py) — BTCUSD-only candle request allowlist. This change is documented in the backend QA report.
- [api/routes_user_positions.py](./api/routes_user_positions.py) — removed injected unsupported forecast/regime values.
- [tests/test_v37_2_backend_contracts.py](./tests/test_v37_2_backend_contracts.py) — synthetic candle identity and position-context regressions.

`api/routes_user_positions.py` was already an untracked worktree file at the V37.2 baseline; it was preserved and edited in place. No unrelated pre-existing changes were reverted.

### V37.2 deliverables

- [V37_2_LIVE_DATA_AND_PROVENANCE_REPORT.md](./V37_2_LIVE_DATA_AND_PROVENANCE_REPORT.md)
- [V37_2_ANALYSIS_AND_BACKTEST_REPORT.md](./V37_2_ANALYSIS_AND_BACKTEST_REPORT.md)
- [V37_2_BACKEND_QA_REPORT.md](./V37_2_BACKEND_QA_REPORT.md)
- [V37_2_FRONTEND_AND_BROWSER_QA_REPORT.md](./V37_2_FRONTEND_AND_BROWSER_QA_REPORT.md)
- [V37_2_FULL_QA_AND_SECURITY_REPORT.md](./V37_2_FULL_QA_AND_SECURITY_REPORT.md)
- [V37_2_MANAGER_FINAL_ACCEPTANCE_REPORT.md](./V37_2_MANAGER_FINAL_ACCEPTANCE_REPORT.md)

The full QA report’s final manager reconciliation supersedes its earlier agent-only note that no tests had run.

## Verification evidence

| Command | Result |
|---|---|
| `.\.venv_win\Scripts\pytest.exe tests\test_v37_2_backend_contracts.py -q` | **8 passed** in 2,662.37s. Includes the BTCUSDT fail-before-data-access case and the no-fabricated-position-context regression. Protected-file guard passed for 1,848 files with identical before/after manifest SHA-256. |
| `.\.venv_win\Scripts\pytest.exe tests\test_security_auth.py tests\test_route_authorization.py -q` | **8 passed** in 224.69s; one Pydantic deprecation warning. Protected-file guard passed for 1,848 files with identical before/after manifest SHA-256. |
| `.\.venv_win\Scripts\pytest.exe tests\test_workstream4_qa_contracts.py tests\test_entry_contracts_and_resolver.py tests\test_live_block_resolver.py tests\test_post_repair_outcome_resolver.py tests\entry_tp_sl -q` | **118 passed** in 14.55s. |
| `npm test` | **Passed**; script reports `All Frontend Unit Tests Passed Successfully!` but emits no numeric test count. |
| `npm run check` | **Passed**; frontend syntax check. |
| Targeted whitespace checks | **Passed** for `api/market_monitor_routes.py`, the changed Python sources/tests, and V37.2 reports (retaining intentional Markdown hard breaks). The unscoped `git diff --check` also reports pre-existing trailing whitespace in unrelated dirty files including `README.md`, `engine/price_forecast_engine.py`, and `research/post_repair_block_builder.py`; those were not changed. |

The full test suite was not run. Some application startup/tests can access protected market data or persistent research state. The focused backend test took approximately 44 minutes, and the real-browser environment did not reach a state where UI acceptance could be completed. The V37.2 agent's initial pytest invocation used a nonexistent `.\venv` interpreter and executed zero tests; the passing pytest results above are from the subsequent `.venv_win` runs.

## Live-data and provenance outcome

- **Bitstamp request:** `GET https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=60&limit=10&exclude_current_candle=true` was authorized conditionally but **not sent** because current public-data terms/permission could not be established.
- **Requests made for live market data:** 0. No other provider, authenticated endpoint, account API, websocket, or order route was used.
- **Freshness:** no live candle was received, so live freshness, completeness, timestamp semantics, OHLC relationships, duplicate/missing bars, and volume were not measured.
- **Local metadata:** the recorded Bitstamp 1h cache was about 20h38m past its metadata-reported close at the inventory time, exceeding the service's two-hour threshold. The minute CSV's source authenticity, timestamp role, and availability time remain unverified. These are metadata claims, not row-level validation.
- **Data-use terms:** the report records why local rights notes could not substitute for current authoritative terms. No public redistribution or license conclusion is made.

Details and the source-by-source classification are in [V37_2_LIVE_DATA_AND_PROVENANCE_REPORT.md](./V37_2_LIVE_DATA_AND_PROVENANCE_REPORT.md).

## Analysis and backtest decision

The entry/exit pipeline, feature construction, resolver, barrier logic, walk-forward path, forecast registry, and their test status are mapped in [V37_2_ANALYSIS_AND_BACKTEST_REPORT.md](./V37_2_ANALYSIS_AND_BACKTEST_REPORT.md).

No historical backtest was run. The available minute CSV is `UNVERIFIED` for source authenticity, event timestamp role, and historical availability; Coinbase and Bitstamp histories are separate and must not be silently concatenated. Frozen execution semantics also remain unresolved for signal/fill timestamp mapping, entry-gap behavior, opening-gap/dual-touch precedence, incomplete horizons/missing bars, cost treatment, and A1 reclaim timing. Holdout custody is not independently established.

Accordingly:

- Backtest classification: `INSUFFICIENT_DATA / HISTORICAL_RESEARCH_INCOMPLETE`.
- Historical strategy/model metrics: **NOT ESTABLISHED**.
- Synthetic pipeline tests, where used: mechanics-only; not market performance.
- HAR: volatility forecasting only; no directional accuracy or profitability claim.
- Challengers/strategies: not promoted.

## Browser and application findings

Frontend unit/syntax checks passed, but browser acceptance did not. The browser could not access the local fixture; external scripts prevented the React application from initializing. There are no verified screenshots, browser console results from a rendered app, or completed API-backed UI interactions. Therefore responsive layout, rendered unavailable/freshness states, refresh behavior, and visual execution-disabled controls remain unverified.

Application status is only `APPLICATION_PARTIALLY_FUNCTIONAL`: synthetic API contract tests passed, but production app/browser acceptance is incomplete. The backend report contains the endpoint mapping and selected API contract outcomes; it does not establish successful live provider behavior or full application startup.

## Remaining defect and owner decisions

### Static API ownership gap

The security review found that position and manual-journal routes accept caller-supplied user IDs/record IDs without deriving identity from an authenticated principal and enforcing per-record ownership. This is a source-level privacy/integrity concern; actual deployment exposure was not verified. It remains unfixed because the authenticated-principal and account/ownership contract is not established by this milestone. Owner decision is required on identity source, migration of existing records, and route exposure before a safe implementation.

### Other blockers

1. Establish current Bitstamp public-data terms and permission before authorizing a request; then separately verify a completed candle and response provenance if permitted.
2. Resolve and freeze the outstanding timestamp, entry-gap, path precedence, horizon, cost, and reclaim semantics before historical outcome evaluation.
3. Establish admissible historical provenance and holdout custody before reporting performance.
4. Provide a browser environment able to access only the loopback fixture while blocking external origins, and bundle/serve required scripts locally for an actual E2E run.
5. Decide the authenticated-principal/ownership contract for user-position and manual-journal APIs.

These are owner/dependency decisions, not claims that the application passed.

## Integrity and operating boundaries

- V37.0 protected assets: **213/213 matched** (including lengths and SHA-256); missing 0, mismatched 0.
- V37.0 protected source hashes: **39/39 matched**; missing 0, mismatched 0.
- Pytest protected-file guards passed with identical before/after hashes for each of the two relevant test runs.
- No protected market observations were opened for the historical backtest; no prospective ledger, historical result, model registry, manifest, or frozen contract was rewritten.
- Branch and HEAD remained unchanged; no commit, push, branch switch, reset, stash, or discard was performed.
- No persistent ingestion process or server was left running.
- Model authorization remains `OFFLINE_RESEARCH_ONLY`; live trading and order placement remain `DISABLED`.

Final Git status: branch `milestone/v35.3-critical-remediation`, HEAD `25d483f4c3646661b57311de9d0b53d2be881adb`, 1,726 status entries total (116 modified and 1,610 untracked), zero staged entries. This includes the 1,725-entry pre-manager-report snapshot plus this report. No unrelated worktree changes were cleaned up.
