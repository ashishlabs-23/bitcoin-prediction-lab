# BTCognitive V35.4 Research Gaps and Remediation Ledger

**Audit date:** 2026-11-03  
**Status:** Findings only; no code, model, evidence ledger, or gate changed.

## Finding classifications

| ID | Classification | Priority | Finding and evidence | Root cause | Minimal proposed remediation | Acceptance evidence |
|---|---|---:|---|---|---|---|
| G-01 | **BROKEN** | P0 | Repository data-mode policy says external network is prohibited in all modes ([`data_mode.py`](./engine/data_mode.py#L100)), but [`fetch_raw_bitstamp_ohlcv`](./engine/bitstamp_market_data_service.py#L171) invokes PowerShell/httpx without enforcing it. | The provider adapter does not use the central network-policy guard. | Add a fail-closed guard before any subprocess/socket work. Do not enable provider mode or add credentials. | Restricted-mode test verifies no HTTP client/process starts; API returns explicit unavailable response without fallback. |
| G-02 | **BROKEN** | P1 | [`market_candles`](./api/market_monitor_routes.py#L357) serves an existing hourly Bitstamp Parquet as `LIVE` without applying freshness/integrity checks. Frontend accepts `BITSTAMP` as ready ([`app.js`](./web/app.js#L17776)). | File existence and sidecar provenance are treated as sufficient freshness evidence. | Validate candles and completed-candle age at the endpoint; return `STALE`/`DATA_UNAVAILABLE`; block stale frontend readiness. | Route/UI tests for fresh, stale, corrupt, missing, and gapped snapshots. |
| G-03 | **BROKEN** | P1 | [`decoupled_analysis_engine.py`](./engine/decoupled_analysis_engine.py#L181) defaults absent `source_exchange` to Coinbase. The non-Bitstamp branch returns a hardcoded C2 interval/coverage and `PROVISIONALLY_VALIDATED` status ([line 211](./engine/decoupled_analysis_engine.py#L211), [line 226](./engine/decoupled_analysis_engine.py#L226)). It also hardcodes a `7/100` prospective status at [line 256](./engine/decoupled_analysis_engine.py#L256), which conflicts with the current ledger and is not authoritative. | Unknown provenance is treated as a calibrated source; historical hardcoded values and a stale ledger count are emitted as runtime calibration evidence. | Keep C2 disabled and suppress its interval/coverage output in this milestone. Treat missing/unknown source and calibration provenance as unavailable. | Unknown-source and matched-source calls both remain C2-disabled and return no calibrated interval/coverage claim. |
| G-04 | **BROKEN** | P1 | [`range_forecast_service.py`](./engine/range_forecast_service.py#L153) derives excursion quantiles from fixed multipliers. [`uncertainty_service.py`](./engine/uncertainty_service.py#L48) defaults `conformal_calibrated=True`, and the production range service does not pass verified calibration provenance. | Calibration is represented by a boolean default rather than an identified, versioned calibration object and reproducible sample. | Default to uncalibrated/unavailable absent verified artifact metadata; avoid “calibrated” claims. | Production-path test without calibration artifact produces unavailable status and no coverage percentage. |
| G-05 | **UNVALIDATED** | P1 | Standard HAR registry artifact is absent; its artifact hash is a placeholder ([`authoritative_model_registry.py`](./models/authoritative_model_registry.py#L78)). Its actual OOS losses and all requested uncertainty/statistical comparisons cannot be computed as registered-model performance. | The registry identity is not backed by a recoverable, hash-verified model artifact and evaluation provenance. | Recover the exact artifact and source/training provenance through governed records. Until then, keep accuracy `NOT ESTABLISHED`; do not recreate/promote a model under the same identity. | Matching artifact hash, source and training provenance; frozen origins; independently reproducible OOS evaluation. |
| G-06 | **UNVALIDATED** | P1 | Existing V35.2 QLIKE claims are not bound to the registered model and identical target/origin protocol. Other historical results have target/persistence alignment issues, no 168h purge, or too few disjoint origins. | Historical summaries do not provide a reproducible, leakage-safe, matched comparison for the registered artifact. | Conduct a pre-specified retrospective replay only after artifact identity is established. Use identical data/origins/targets and horizon purge. | Reproduction package includes forecasts, targets, exclusions, hashes, loss vectors, DM/HLN, Holm, and dependent CIs. |
| G-07 | **UNVALIDATED** | P1 | Prospective ledger has 10 seven-day forecasts, 5 resolved and 5 pending; 9 adjacent issue windows overlap. | Overlapping 168-hour targets do not constitute independent confirmatory blocks. | Continue the frozen append-only protocol; never count overlapping outcomes as independent blocks. Assess interval precision and effective sample size. Do not enable C2. | Mature, clean, non-overlapping observations with predeclared acceptance and dependence-aware uncertainty. |
| G-08 | **UNVALIDATED** | P2 | Regime classifier uses fixed deterministic thresholds and 200-bar warmup ([`regime_strategy_tournament.py`](./engine/regime_strategy_tournament.py#L180)); OOS utility, transition behavior, and performance by regime are not established. | Classification logic is not evidence that regimes improve a forecast or risk decision. | Pre-register causal regime labels and evaluate them on matched origins; do not tune thresholds on holdout. | Out-of-sample regime-stability and incremental-value report with adequate effective sample. |
| G-09 | **UNDERDEVELOPED** | P2 | No complete live UI/API analysis trace was performed; the external request is disallowed by policy and the route bypasses that policy. Several failure cases lack dedicated tests. | No isolated integration harness covers full request, serialization, and UI rendering while guaranteeing no external request or persistent side effect. | Add an offline controlled end-to-end test harness and missing failure cases. Keep fixtures deterministic and isolated from protected artifacts. | Test proves request-to-render behavior from known fixture response and explicit errors for every injected failure; no network or protected-file writes. |
| G-10 | **UNDERDEVELOPED** | P2 | Analysis API returns a generic dictionary and frontend stores the response without validating a formal response contract. | There is no shared/validated response schema at the serialization/render boundary. | Define and test an explicit response contract, including unavailable/null model outputs and provenance. | Invalid response rejected with visible error; valid response renders only backend-provided values. |
| G-11 | **ACCEPTED** | - | Protected `data/raw/ohlcv.parquet` exists and matched the protected hash; 42,326 rows have no detected basic timestamp/OHLCV defects. | Read-only integrity inspection. | Preserve file, manifest, and hash; do not overwrite. | Hash and independent read-only validation recorded in audit. |
| G-12 | **ACCEPTED** | - | Analysis route explicitly rejects provider failure with HTTP 503 and has tests that reject local fallback and Coinbase substitution ([`routes_tournament.py`](./api/routes_tournament.py#L620); [`test_v33_8_failure_injection.py`](./tests/test_v33_8_failure_injection.py#L211)). | Fail-closed provider-failure handling is implemented and partially tested. | Preserve behavior while adding the network guard. | Existing mocked failure tests continue to pass. |
| G-13 | **ACCEPTED** | - | Standard HAR registry authorization is offline-only; analysis response provenance marks `OFFLINE_RESEARCH_ONLY`. | Research governance separates model identity from production authorization. | Keep authorization unchanged. | Registry and response continue to state offline-only; production serving remains locked. |

## Research and evidence gaps

### Forecast performance

- Exact registered model artifact, hash, feature transform, fit window, and forecast outputs are unavailable.
- No matching, chronological, horizon-purged OOS forecast table exists for persistence, Standard HAR, QLIKE-HAR, HAR-RS-DOW, and a regime-aware benchmark.
- No admissible values for QLIKE, MAE, RMSE, relative improvement, DM/HLN, Holm-adjusted inference, confidence intervals, or regime-stratified performance are established.
- Prior historical figures remain retrospective claims and do not establish a registered-model result.
- No directional accuracy result can be inferred from volatility scores.

### Calibration, excursions, and regime intelligence

- C2 code embeds a historical 2026 replay with 5,671 bars and states 84.89% causal coverage, 90.43% pooled coverage, 82.14% extreme-volatility coverage, and a broad 95% interval `[73.14%, 93.14%]`. These are code-embedded historical claims, not a fresh prospective result. The 2026 window is retrospective development/replay data, not confirmatory evidence.
- The envelope is suppressed for Bitstamp as a source mismatch, but an absent `source_exchange` defaults to Coinbase and can activate the hardcoded branch.
- The same embedded report says prospective accumulation is frozen at `7/100`; the current ledger instead has 10 seven-day records, 5 resolved and 5 pending. The embedded count must not be used as current evidence.
- C2 remains disabled for this milestone regardless of source. Matching a source does not authorize activation.
- The 24-hour MFE/MAE quantiles are fixed-multiplier outputs, not demonstrated calibrated quantiles. The default conformal flag is not tied to an artifact.
- The 200-bar threshold classifier has no established out-of-sample utility or dependence-aware transition analysis.

### Prospective evidence

- The ledger contains 21 records: 11 resolved 24-hour targets and 10 seven-day targets (5 resolved, 5 pending).
- Nine adjacent seven-day issue windows overlap. The number of records must not be reported as the number of independent blocks.
- Even 100 non-overlapping observations would not automatically prove validity. Precision, serial dependence, missing resolutions, regime composition, and effective sample size remain part of the gate.
- Frozen records and protocol were not edited.

## Test evidence and limits

- Focused Python command: **29 passed**. It covered the provider failure-injection file, market-monitor routes, registry/variance tests, and uncertainty tests.
- Frontend command: `node tests_frontend.js` -> **All Frontend Unit Tests Passed Successfully**.
- V35.3 regression summary reports 320 categorized tests / 75 Python files. V35.3 acceptance material's 343 / 77 is an aggregate that adds separately reported adversarial and frontend groups, not a single runner result.
- `test_inventory.csv` counts 363 files and 1,704 AST-discovered test-like functions; this is not pytest collection. 288 legacy files were not in the default categorized runner. Exact network-marker deselections are not recorded.
- The broad current log excerpt ends during collection/execution with failure markers and lacks a final summary. Full-suite status is not established.
- No live provider request, external network call, or complete frontend-to-real-API request was performed for this audit.

## Change-control recommendation

The user authorized **reports only**. Therefore this ledger is a proposal, not an implementation plan with permission to edit code. No code change, model fit, model promotion, evidence-ledger edit, statistical-gate change, C2 activation, or provider authorization is included.
