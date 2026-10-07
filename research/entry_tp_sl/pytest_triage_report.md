# Pytest Triage — G0

**Status: ROOT CAUSE IDENTIFIED; GLOBAL SUITE STILL FAILS/TIMES OUT. No tests were skipped or removed.**

## Runtime and collection

- Selected runtime: CPython 3.13.14, Windows x64; pytest 8.4.1, pluggy 1.6.0.
- `pytest.ini`: `testpaths=tests`, excludes `venv`, `.venv`, `.git`, `web`, `archive`, `scratch`, `experiments`; only registered marker before G0 was `network`.
- Pytest plugins in the selected environment: `anyio 4.13.0`, `pytest-asyncio 0.23.7`. `pytest-timeout`, xdist, randomly, Hypothesis, and jsonschema were absent from the selected environment at audit time.
- Collection: 689 test nodes. The prior unbounded full run stalled at approximately 73%.
- `tests/test_range_failure_modes.py` was the apparent 73% node by order; it passes in isolation (3 tests, 3.33s) and is not the culprit.
- The adjacent sequence `test_quantitative_suite_v3.py`, `test_range_database_integration.py`, and `test_range_failure_modes.py` passes in isolation with SQLite redirected to a temporary DB (9 tests, 6.52s).

## Reproduced timeout

A temporary copy of `pytest-timeout 2.4.0` was installed under the system temp directory only; it was not added to the project interpreter. The bounded command was:

```powershell
python -m pytest -vv --timeout=60 --timeout-method=thread -o faulthandler_timeout=25 --tb=short
```

Exact timed-out node:

```text
tests/test_candle_manager.py::test_candle_state_manager_forming_vs_closed
```

The stack shows:

```text
CandleStateManager.process_tick
  -> _generate_prediction_on_closed_candle (api/candle_manager.py)
  -> for each pending row: update_prediction_outcome (backtest/market_memory.py)
  -> pandas.read_csv(experiments/results/market_memory.csv)
```

Measured ledger state at triage: `market_memory.csv` is 2,788,437 bytes with 5,398 rows; 5,377 rows satisfy the caller's pending predicate. One standalone CSV read takes about 0.077s. The caller loops over those pending rows and invokes `update_prediction_outcome` for each; that function scans and rewrites the entire CSV every time. This creates quadratic I/O (thousands of full-file reads and rewrites) and explains the timeout. This is a production/shared-storage performance defect, not a bad assertion in the test.

## Quarantine handling

The test is tagged `pytest.mark.quarantined` with its reason registered in `pytest.ini`. **The marker does not deselect it**: root pytest defaults are unchanged, no skip was added, and the normal full suite continues to expose the failure. A separate selection such as `pytest -m quarantined` is available for diagnosis; excluding it must never be represented as a passing full-suite gate. Fixing the shared CSV update path is outside this G0 task's no-production-change constraint, so G0 remains blocked until an approved fix and full-suite rerun.

## Independent G0 suite

Run without collecting the legacy suite:

```powershell
python -m pytest -q --timeout=30 tests/entry_tp_sl
```

Results from that command are recorded separately in `G0_FOUNDATION_INTEGRITY.md`.
