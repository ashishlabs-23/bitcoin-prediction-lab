# BTCognitive V35.4.1 Remediation Report

**Date:** 2026-11-03  
**Branch / HEAD:** `milestone/v35.3-critical-remediation` / `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Disposition:** Critical remediation implemented; full milestone acceptance remains **NOT ESTABLISHED**.

## 1. Findings fixed

| Defect | Before | After |
|---|---|---|
| Network policy bypass | The Bitstamp fetch path could start PowerShell or an HTTP client despite external networking being prohibited. | The provider guard blocks before subprocess/socket use. The focused test replaces both entry points with sentinels and verifies neither is called. No external provider request was made in this remediation. |
| Mismatched analysis snapshots | `/api/tournament/analyse` could retrieve a second snapshot rather than analyze the frontend's displayed candles. | The route requires the submitted snapshot, validates source, count, timestamps, closed-candle status, hourly cadence, ordering, duplicates, gaps, OHLCV values and freshness, then analyzes that exact payload and attaches its digest. Missing, invalid, stale or insufficient snapshots fail closed. |
| Stale cache presented as live | The cached hourly route could label cached data `LIVE`. | The local-candle route now reports explicit freshness/unavailability states; stale or invalid cache data is not labeled live. The frontend refuses stale or malformed input and visibly renders request/API errors. |
| Unverifiable calibration / C2 | Unknown calibration provenance could inherit Coinbase defaults; several paths emitted fixed-width bounds, hardcoded coverage/health values, or accepted caller-supplied calibrated status. | C2 health and calibrated bounds/coverage default to unavailable. Relevant API controls reject C2/conformal activation; strategy/risk paths fail closed. Historical register entries remain available as historical evidence, not current registered-model performance. Fixed-multiplier scenario outputs are explicitly unvalidated heuristics. |
| Unsupported Standard HAR claims | UI/API fallback values presented forecast, QLIKE, coverage and health metrics despite the missing registered artifact. | Current forecast status is `NOT ESTABLISHED`; unavailable point forecasts and C2 metrics are null or explicitly unavailable. Historical reports/register contents were not rewritten. |
| Implicit Coinbase provenance | The scenario planner labeled local parquet inputs as Coinbase when source metadata was absent. | Missing source provenance is labeled `LOCAL_PARQUET_UNVERIFIED`/unavailable, not Coinbase. Missing scenario boundaries/volatility fail closed rather than using fabricated C2/default market values. |
| Fabricated intelligence summary | The forecast-intelligence endpoint emitted fixed forecast, reliability, coverage and calibration values without verified inputs. | It now returns explicit offline/unavailable states and no fabricated forecast or calibration metrics. Its health endpoint no longer labels any observed-block count as production validation. |

### Files changed

- **Analysis data path:** `api/market_drivers.py`, `api/market_monitor_routes.py`, `api/routes_tournament.py`, `engine/bitstamp_market_data_service.py`, `engine/coinbase_15m_adapter.py`, `engine/regime_strategy_tournament.py`, `web/analysis_contract.js`, `web/app.js`, `web/index.html`.
- **Calibration and governance:** `api/routes_arena.py`, `api/routes_prediction.py`, `api/routes_research.py`, `api/routes_terminal.py`, `engine/arena_accounts.py`, `engine/arena_evolution.py`, `engine/counterfactual_contract_engine.py`, `engine/decoupled_analysis_engine.py`, `engine/decision_envelope.py`, `engine/forecast_intelligence.py`, `engine/prediction_pipeline.py`, `engine/range_forecast_service.py`, `engine/scenario_contract_engine.py`, `engine/smart_entry_engine.py`, `engine/strategy_selection.py`, `engine/uncertainty_service.py`, `scripts/adversarial_verification_suite.py`.
- **Tests:** `tests/test_forecast_intelligence.py`, `tests/test_range_forecast_service.py`, `tests/test_research_improvement_sprint.py`, `tests/test_scenario_freshness_and_contract_v7.py`, `tests/test_tier0_finite_horizon_verification.py`, `tests/test_uncertainty_service.py`, `tests/test_v33_1_entry_and_analysis_decoupling.py`, `tests/test_v33_7_bitstamp_integration.py`, `tests/test_v33_8_failure_injection.py`, `tests/test_v35_4_1_analysis_integrity.py`, `tests_frontend.js`.

The worktree was already dirty before remediation. Existing modified and untracked files were preserved; no branch, commit, push, reset, stash or clean operation was performed.

## 2. Standard HAR identity and accuracy

The registry identifies `Standard-HAR-v1.0`, target `rv7d_var_ann` (168 hours), artifact path `experiments/results/freeze/standard_har_v1.joblib`, and authorization `OFFLINE_RESEARCH_ONLY`. The exact artifact is absent. Its registry `artifact_sha256` is the placeholder `standard-har-v1-baseline-hash`, not a verifiable SHA-256. No artifact hash could therefore be computed or matched.

**Registered Standard HAR forecast accuracy: `NOT ESTABLISHED`.** No artifact was reconstructed, trained, replaced or promoted, and no score from another model/evaluation was attributed to it.

## 3. Test execution

Focused offline Python command:

```powershell
.\.venv_win\Scripts\pytest.exe -q tests\test_v35_4_1_analysis_integrity.py tests\test_uncertainty_service.py tests\test_range_forecast_service.py tests\test_v33_1_entry_and_analysis_decoupling.py tests\test_v33_8_failure_injection.py tests\test_forecast_intelligence.py tests\test_scenario_freshness_and_contract_v7.py tests\test_research_improvement_sprint.py tests\test_tier0_finite_horizon_verification.py::test_what_if_scenario_api_endpoint
```

**Result:** 66 collected, 66 passed, 0 failed, 0 deselected, 1 existing Pydantic v2 deprecation warning (`AnalyseRequestModel` class-based `Config`). These suites include blocked-network sentinels, exact-snapshot routing, stale-cache rejection, candle failure cases, C2/API-control rejection, missing-calibration behavior, and model exception/missing-output handling. The full repository suite was not run; live provider tests were not run to honor the no-network restriction.

Frontend:

```powershell
node tests_frontend.js
```

**Result:** passed; the script reported “All Frontend Unit Tests Passed Successfully” (it does not report an individual assertion count).

Final Standard HAR API/registry spot check:

```powershell
.\.venv_win\Scripts\pytest.exe -q tests\test_research_improvement_sprint.py::test_research_api_experiments_endpoint tests\test_research_improvement_sprint.py::test_authoritative_registry_includes_challenger
```

**Result:** 2 passed, 1 same Pydantic deprecation warning. The frontend command was also rerun after final edits and passed.

Additional checks:

- `node --check web\app.js` — passed.
- Pylance syntax checks on changed Python implementation/test files — no syntax errors reported.
- Targeted `git diff --check` over remediation files — passed.
- Whole-worktree `git diff --check` reported pre-existing trailing whitespace in unrelated `research/post_repair_block_builder.py` and `research/reports/*`; those files were not edited.

The first focused run exposed tests that relied on stale local parquet data and an outdated registry ID. The scenario tests were changed to use an explicit deterministic test fixture (or assert stale-data rejection); the registry assertion now matches the authoritative `Standard-HAR-v1.0` ID. The final focused run above passed.

## 4. Remaining defects and blocked items

- No full browser-to-real-backend execution was performed. A direct API test proves the submitted candle snapshot is consumed, but live network retrieval is intentionally prohibited.
- The protected parquet used by other scenario paths has no verified exchange provenance. Those results are labeled unverified and remain unvalidated heuristics; they are not the primary analysis request.
- The registered Standard HAR artifact/hash are unavailable, so its forecast and accuracy remain `NOT ESTABLISHED`. Prospective evaluation and model authorization remain blocked.
- Historical research outputs and ledgers remain intact. Historical metrics are not current calibration or registered-model claims.
- The existing Pydantic deprecation warning remains.
- The initial worktree contained a modified `data/prospective_forecast_ledger.jsonl`; it was not edited by this remediation and was preserved. Because no starting hash was recorded, byte-for-byte unchanged status cannot be certified. An earlier test iteration may also have appended to the ignored `experiments/results/market_memory.db`; there is no baseline row count/hash, and no rollback was attempted.
- No statistical acceptance threshold was loosened. C2 risk use was disabled/fail-closed. Live trading and production authorization remain disabled.

## 5. Final repository status

```text
Branch: milestone/v35.3-critical-remediation
HEAD:   25d483f4c3646661b57311de9d0b53d2be881adb
git status --porcelain=v1: 428 entries
  staged: 0
  tracked, unstaged: 105
  untracked: 323
```

The worktree remains dirty; all pre-existing changes were preserved. `data/raw/ohlcv.parquet` and the absent registered model artifact have no status entry. `data/prospective_forecast_ledger.jsonl` remains modified (`M`) in the worktree and was not edited by this remediation. The report itself is untracked (`??`); no commit was created.

**Acceptance decision:** Remediation improves traceability and prevents unsupported calibration/model claims, but the complete V35.4.1 acceptance criteria are **NOT MET** until the exact registered artifact and hash are recovered and the required end-to-end evidence is independently reproduced.
