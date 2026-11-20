# BTCognitive V35.4 Acceptance Matrix

**Audit date:** 2026-11-03  
**Repository state audited:** `milestone/v35.3-critical-remediation` at `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Scope:** Evidence-based acceptance status; no code edits authorized or made.

## Acceptance results

| ID | Requirement | Evidence / test | Result | Remaining gate |
|---|---|---|---|---|
| A-01 | Preserve branch, commit, and user worktree | Branch/HEAD recorded; 92 tracked modified and 315 untracked paths; 0 staged at audit start/end before report creation | **PASS - PRESERVED** | Reports add five new untracked documentation files only. No user file was intentionally changed. |
| A-02 | Verify protected source data without mutation | `data/raw/ohlcv.parquet`: 42,326 hourly rows, 2022-01-01 through 2026-10-30; no timestamp gaps/duplicates/order errors or OHLCV invalids; hash matches test constant | **PASS - BASIC INTEGRITY** | This does not establish provider freshness or model-evaluation provenance. |
| A-03 | Enforce data-mode network restriction | [`is_external_network_permitted`](./engine/data_mode.py#L100) returns false, while provider fetch directly invokes PowerShell/httpx | **FAIL** | Guard before every network/process call and prove block-before-side-effect. |
| A-04 | Provider error has no fallback | Mocked failure tests 12, 13, 15 assert 503 and no local/Coinbase substitution | **PASS - MOCKED ERROR PATH** | Test actual central network guard without making a real external request. |
| A-05 | Candle retrieval and validation | Mock tests cover empty, malformed dictionary, duplicate, gap, invalid OHLC, stale and provider failure; success test uses a mock payload | **PARTIAL** | Add incomplete-candle and full API response tests. No real Bitstamp request performed. |
| A-06 | Cached candle route reports valid freshness | Hourly cache endpoint labels existing Bitstamp file `LIVE` without using the service freshness/validation path; frontend accepts it as ready | **FAIL** | Fresh/stale/corrupt cache tests; route and UI must expose stale/unavailable distinctly. |
| A-07 | One complete UI-to-API analysis is reproducible | Frontend submits closed candles; API normally obtains its own provider data; no full integration run | **NOT ESTABLISHED** | Controlled offline integration harness, explicit snapshot identity, and response contract. |
| A-08 | Correct response serialization and rendering | Backend provenance includes submitted and analyzed counts/hashes; frontend stores and renders the response object; generic dict response lacks a declared response schema | **PARTIAL** | Schema validation and malformed-response failure test. |
| A-09 | Invalid/incomplete candle handling | Invalid OHLC/gap/duplicate and downstream stale cases have mocks; incomplete candle lacks a dedicated test | **PARTIAL** | Add explicit candle-close boundary and invalid numeric cases at the service and endpoint boundary. |
| A-10 | Model exception and missing model output fail explicitly | No dedicated integration test identified | **NOT ESTABLISHED** | Add injected exception, `None`/missing output, and serialization tests; ensure visible non-success response. |
| A-11 | Calibration is unavailable unless validated | Explicit false flag is tested in uncertainty unit tests, but default is `True`; fixed multiplier path and C2 hardcoded results remain. Embedded `7/100` prospective status conflicts with the current ledger. | **FAIL** | Keep C2 disabled and suppress its interval/coverage output; default unknown source and missing calibration provenance to unavailable. |
| A-12 | Correct registered Standard HAR identity | Registry target/horizon/features are present; referenced joblib artifact absent and hash is a placeholder | **FAIL / BLOCKED** | Recover exact frozen artifact and provenance before attributing any score. |
| A-13 | OOS accuracy of registered Standard HAR | No exact registered forecasts or verified matched evaluation | **NOT ESTABLISHED** | Report QLIKE/MAE/RMSE, improvement, DM/HLN, Holm, CI, dates, n, exclusions, and regimes only after reproducible evaluation. |
| A-14 | Comparable model benchmarks | Existing claimed metrics are not tied to identical exact model/data/origins; prior alignment/purge issues | **NOT ESTABLISHED** | Same causal data, target, forecast origins, and horizon treatment across all predeclared models. |
| A-15 | Directional accuracy not conflated with volatility accuracy | Registry separates 168h variance from 1h return sign; V35.4 report reports no directional score | **PASS - CLAIM BOUNDARY** | Any separate directional evaluation requires its own targets, predictions, and OOS protocol. |
| A-16 | Regime classifier OOS usefulness established | Deterministic 200-bar threshold rules inspected; no matched OOS utility analysis | **NOT ESTABLISHED** | Pre-register regime mapping and test incremental value/transition behavior without holdout tuning. |
| A-17 | C2 prospective coverage and effective n sufficient | Embedded historical coverage is retrospective; its `7/100` ledger status is stale; current ledger has 10 seven-day records, 5 resolved, 5 pending, and 9 adjacent overlaps | **FAIL - INSUFFICIENT** | Continue frozen protocol; determine effective n and precision only from eligible resolved non-overlapping blocks. Keep C2 disabled. |
| A-18 | Reported historical results remain auditable | V35.3/V35.2 reports and artifacts read without overwrite; prior claims are labeled historical/unverified in V35.4 reports | **PASS - PRESERVED** | Any amendment must be dated and additive; do not rewrite historical conclusions. |
| A-19 | Test totals are consistent and sourced | 320/75 is categorized Python runner output; 343/77 is an aggregate including separately run checks; AST inventory is discovery only | **PARTIAL - RECONCILED** | Capture runner command, collected/deselected counts, and separate suite counts in future execution artifacts. |
| A-20 | Current full-suite health established | Historical full log excerpt has failure markers and no final summary; focused suite only | **NOT ESTABLISHED** | Run governed full suite only after confirming runner side effects and output paths; preserve existing artifacts. |
| A-21 | No trading or production authorization enabled | Registry/provenance state remains offline research-only; no code or model changes made | **PASS - MAINTAINED** | Keep production serving locked and live trading disabled. |

## Test execution record

| Command / record | Result | Interpretation |
|---|---|---|
| `.venv_win\Scripts\python.exe -B -m pytest -p no:cacheprovider -q tests/test_v33_8_failure_injection.py tests/test_market_monitor_routes.py tests/test_v35_model_registry_and_variance.py tests/test_uncertainty_service.py` | **29 passed** | Focused tests only; does not establish the full pipeline. |
| `node tests_frontend.js` | **All Frontend Unit Tests Passed Successfully** | The script did not emit a count of individual assertions/cases. |
| `artifacts/v35_3_regression_summary.json` | **320 passed / 75 categorized Python files** | Historical categorized regression summary; not a newly run V35.4 full suite. |
| V35.3 adversarial verification report | Documents **12 cases passed** | Separate run; not rerun in V35.4. |
| `full_test_run_current.log` | Partial progress with failure markers, no final summary | Cannot infer final pass/fail totals or current broad-suite health. |
| `artifacts/test_inventory.csv` | 363 test files / 1,704 AST-discovered test-like functions | Discovery inventory, not pytest collected count. |

## Required final milestone decisions

| Decision | V35.4 disposition |
|---|---|
| Research experiment | **INCONCLUSIVE** |
| Prospective evidence | **COLLECTING; NOT SUFFICIENT FOR CONFIRMATORY EVALUATION** |
| Model authorization | **OFFLINE_RESEARCH_ONLY** |
| Live trading | **DISABLED** |
| Registered Standard HAR OOS accuracy | **NOT ESTABLISHED** |
| End-to-end analysis acceptance | **NOT ESTABLISHED** |

## Scope and change record

The user selected **reports only**. This acceptance matrix records findings and gates; it does not authorize or apply code remediation. No code, model, frozen protocol, prospective record, statistical gate, branch, or commit was changed.
