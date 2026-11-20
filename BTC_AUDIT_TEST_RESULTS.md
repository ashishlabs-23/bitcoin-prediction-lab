# BTCognitive Audit Test Results

**Date:** 2026-11-05  
**Decision status:** Full Python suite **FAIL**; milestone **BLOCKED**.

## Commands and outcomes

| Command | Result |
|---|---|
| `.venv_win\Scripts\python.exe -m pytest -q tests\test_longitudinal_integrity.py tests\test_longitudinal_monitor.py tests\test_served_journal_client_and_ui.py tests\test_decoupled_analysis_bollinger_bounds.py tests\test_standard_har_identity.py tests\entry_tp_sl\test_pit_timing_provenance.py` | **26 passed** in 4.28s. Protected-file guard passed. |
| `.venv_win\Scripts\python.exe -m pytest -q tests\test_longitudinal_integrity.py tests\test_longitudinal_monitor.py tests\test_tournament_startup_isolation.py tests\test_v12_strategy_tournament.py tests\test_v32_43_strategy_tournament_and_smart_entry.py tests\test_v32_48_integrated_analyse_and_tournament.py tests\test_v13_strategy_overlay_and_chart.py tests\test_arena_runner.py tests\test_arena_runner_v3.py tests\test_observatory.py tests\test_terminal_routes.py tests\test_v18_disabled_gates_and_forecast_research.py tests\test_agent_a_security_regression.py tests\test_v35_4_1_analysis_integrity.py tests\test_served_journal_client_and_ui.py tests\test_decoupled_analysis_bollinger_bounds.py tests\test_standard_har_identity.py tests\entry_tp_sl\test_pit_timing_provenance.py` | **134 passed**, 1 Pydantic deprecation warning, in 38.54s. Protected-file guard passed with identical before/after manifest digest. |
| `.venv_win\Scripts\python.exe -m pytest --collect-only -q` | **1,971/1,972 collected; 1 deselected** by `pytest.ini` marker policy; collection exit code 0. |
| `.venv_win\Scripts\python.exe -m pytest -q` | **1,696 passed, 273 failed, 2 errors, 1 deselected, 10 warnings**, completed in 8:28:21. No exclusions beyond configured `-m "not network"`. |
| `.venv_win\Scripts\python.exe -m pytest -q tests\test_tournament_startup_isolation.py tests\test_v37_4_r1_app_integration.py` | **6 passed, 2 failed, 1 warning** in 39.68s. Both failures are in fixture integration, described below. |
| `.venv_win\Scripts\python.exe -m pytest -q tests\test_v32_64_data_lane_separation.py::test_11_protected_artifacts_bit_level_invariance` | **1 failed**: stale expected OHLCV hash `c007cd...` vs actual unchanged `ba06fb...`. No test or dataset change. |
| `npm test -- --runInBand` | **Passed**; frontend test script completed successfully. |
| `npm run check --silent` | **Passed**; JavaScript syntax checks completed. |
| `npm run build` | **Passed**; asset/syntax smoke checks and frontend tests completed. |
| `git diff --check` | No diagnostics in the manager's scoped owned-path check. Independent QA found 12 whitespace diagnostics in pre-existing/unrelated paths: 5 in `README.md`, 1 in `engine/price_forecast_engine.py`, 2 in `research/post_repair_block_builder.py`, and 1 each in four `research/reports/post_repair_*.md` files. |

## Full-suite details

The exact command was `.venv_win\Scripts\python.exe -m pytest -q`. Pytest read repository `pytest.ini`, which configures `-m "not network"`; one network-marked test was deselected, not run. The two setup errors were:

- `tests/test_stage12_causal_validation.py::test_prospective_manifest_and_frontier_chronology` - Stage 12 manifest missing under the test's temporary `results` path.
- `tests/test_stage12_causal_validation.py::test_strictly_causal_conformal_calibration_metrics` - required HAR artifact missing under the test's temporary path (`FileNotFoundError`).

Failures span runtime/API contracts, protected-file and model-integrity checks, regime/forecast expectations, persistence/permissions, research validations, and other legacy suites. The run did not include a comparable clean baseline, so the 273 failures cannot all be attributed to this remediation. Exact complete output is retained at:

`C:\Users\Ashish\AppData\Local\Temp\1793849327881-copilot-tool-output-38616-55109959-a78e-4e9b-9c26-692f14be0d12.txt`

The R1 hash failure is exact and reproducible:

```text
tests/test_v32_64_data_lane_separation.py::test_11_protected_artifacts_bit_level_invariance
Expected: c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f
Actual:   ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057
```

Another full-suite failure, `tests/test_v32_23_forecast_smart_entry_recovery.py::test_v32_23_har_artifact_sha256_matches_authoritative_manifest`, reported expected `None` against actual HAR-RS-DOW artifact digest `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b`. This assertion was not changed; Standard HAR and HAR-RS-DOW remain distinct.

## Fixture integration and runtime limits

The isolated startup tests pass with SQLite, Parquet, and non-loopback networking guarded. The two R1 fixture integration failures were:

- `test_local_fixture_observation_lifespan_route_and_existing_chart` expected `ACTIVE` but received `DATA_UNAVAILABLE`.
- `test_normal_lifespan_without_network_permission_is_unavailable` expected a `BitstampTradeFeed` object but received `None` when network permission was denied.

The deterministic local fixture integration did not reach its existing-chart assertion in the first test. No browser QA was completed. No exchange/provider or external network was contacted.

The four formerly reported focused failures are resolved in the expanded focused run: fixture startup/ArenaRunner lazy initialization, blocked health status contract, unavailable observatory summary shape, and corrected Standard-HAR vs HAR-RS-DOW identity expectation.

## Protected-file integrity event

The full-suite protected-file guard reported:

```text
PROTECTED_FILE_HASH_GUARD: FAIL
models\checkpoints\meta.pt
models\checkpoints\regime.pt
BEFORE_MANIFEST_SHA256=d4cb2feaf092117d74edf35339025b80e3e0c4e2404aa56c17a2412779d3c308
AFTER_MANIFEST_SHA256=61ac0794c0e5cb1322db4660f7b7e27c0097420d0ea2de1e303f2d0fb5152d70
```

Those two files had no individual pre-suite hashes in the preflight record. The current hashes and metadata are captured in `BTC_WORKTREE_BASELINE.json`; no content was inspected, and neither file was restored. Other inventoried protected artifacts still match the saved preflight hashes. Treat both checkpoint artifacts as integrity-unresolved until owner review.

No SQLite WAL/SHM/journal sidecars were found in the QA scan locations. QA observed the pre-existing `data/.prospective_shadow_runner.lock`.
