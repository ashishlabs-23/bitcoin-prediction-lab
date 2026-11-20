# BTCognitive V35.4.3 Test Isolation Report

## Isolation controls inspected

`tests/conftest.py` sets `SQLITE_DB_PATH`, `MEIE_DB_PATH`, `RESULTS_DIR`, and `DATA_PROCESSED_DIR` to disposable operating-system temporary paths before application modules are imported. It initializes the test database there, blocks SQLite connections into protected paths, blocks non-loopback socket connections, rejects protected-file writes and protected parquet writes, and compares a SHA-256 inventory before and after a completed pytest session.

`tests/test_database_isolation.py` verifies that the market-memory, feature-store, and MEIE stores resolve beneath the disposable test root; verifies canonical database connections are blocked; and verifies socket and protected-ledger writes fail. This safeguard was exercised by the completed focused run below.

Static searches found SQLite/ledger references in 29 test files and write-like file APIs in 89 test files. These are search-result counts, not a claim that every matched test writes protected state. Several legacy tests explicitly target canonical paths; the global SQLite guard should fail those attempts closed. The full test suite was not run, and the complete behavior of every legacy test is therefore not certified.

## Validation evidence

| Command | Result |
|---|---|
| `.\.venv_win\Scripts\python.exe -m pytest -vv -s --tb=short tests\test_v35_4_1_analysis_integrity.py tests\test_database_isolation.py` | Completed: **29 passed, 0 failed, 1 warning**, 696.51 seconds. Protected-file guard: **PASS**, 1,848 files; before/after manifest SHA-256 both `d424b3c0dd43a0b4a91735a2050fd43315edd341d3f146655aad6698ec3ce031`. This run predates the final missing-venue fallback change. |
| `node tests_frontend.js` | Completed successfully. All 15 named frontend test sections printed `PASSED`; the script does not report an individual assertion count. |
| `node --check web\app.js` | Completed successfully with exit code 0. |
| `.\.venv_win\Scripts\python.exe -m pytest -vv -s --tb=short tests\test_fail_closed_data_contracts.py tests\test_v12_strategy_tournament.py` | Started but was stopped after 1,342 seconds without a pytest summary. **No collected/pass/fail count is claimed.** |

The last run also included a new test for missing regime-venue provenance. Because the run did not complete, that test is not counted as passed. A standalone import probe was also stopped due prolonged module import; it produced no test result. The unsuccessful probe did not make an external request. The current source fallback is visible as `regime.get("venue") or "UNAVAILABLE"` but still needs a completed runtime test.

## API/integration scope

The focused route test posts through FastAPI's `/api/tournament/analyse` endpoint with a fixed 220-row deterministic test fixture. It asserts the request snapshot hash, submitted/analyzed candle counts, source, freshness, and offline authorization. The route's `analyse_current_market` function is monkeypatched in that test. Consequently:

- The test proves the API validates and hands the submitted candles to the analysis function without fetching a second snapshot.
- It does not prove the real analysis engine completed on observed local BTCUSD data.
- The fixture is synthetic deterministic test data, not empirical market evidence.
- Complete browser-to-real-engine integration was **NOT RUN**.

## Exclusions and state protection

- No full repository suite, background collector, prospective worker, or live application workflow was run.
- No external provider request was made by the completed focused test run; non-loopback sockets were blocked by the test harness.
- The completed run's whole-inventory guard passed. A subsequent revalidation attempt did not finish, so it has no guard summary; individual protected-file hashes were rechecked afterward and matched the forward baseline. See `V35_4_3_FORWARD_INTEGRITY_BASELINE.md`.
- The Standard HAR artifact remains absent. No model was reconstructed or evaluated.

## Assessment

Database isolation and protected-file hash checks are evidenced for the completed focused run. The current final API venue change is not Python-test-verified, and full test-suite isolation remains unverified. Do not treat this report as certification of the complete repository test suite.
