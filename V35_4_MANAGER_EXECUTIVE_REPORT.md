# BTCognitive V35.4 Manager Executive Report

**Audit date:** 2026-11-03  
**Audit mode:** Read-only inspection; no code or protected evidence modified  
**Repository:** `ashishlabs-23/bitcoin-prediction-lab`  
**Branch / HEAD:** `milestone/v35.3-critical-remediation` / `25d483f4c3646661b57311de9d0b53d2be881adb`

## Executive decision

| Decision | V35.4 result |
|---|---|
| Research experiment | **INCONCLUSIVE** |
| Prospective evidence | **COLLECTING; NOT SUFFICIENT FOR CONFIRMATORY EVALUATION** |
| Model authorization | **OFFLINE_RESEARCH_ONLY** |
| Live trading | **DISABLED** |
| Registered Standard HAR out-of-sample accuracy | **NOT ESTABLISHED** |
| Complete end-to-end analysis acceptance | **NOT ESTABLISHED** |

The registered Standard HAR is defined as an offline 168-hour annualized realized-variance forecast, not a directional or price forecast. Its registry-referenced model artifact is absent and the registry hash is a placeholder. Consequently, its exact out-of-sample performance cannot be reproduced or attributed to the registered model. Prior reported scores are not accepted as a substitute.

The analysis path contains two correctness issues that prevent accepting the present end-to-end behavior: the Bitstamp fetch path does not enforce the repository's external-network prohibition, and a cached hourly Bitstamp file can be returned as `LIVE` without applying the service's freshness or integrity checks. Additionally, calibration-shaped outputs can be produced from fixed constants when source provenance is missing; these must not be presented as calibrated.

No code changes, model changes, test-gate changes, commits, or branches were made. No protected dataset, manifest, or ledger was intentionally written. The five V35.4 reports document findings and proposed work only.

## Scope and evidence

The audit traced the current files from frontend candle acquisition through `/api/tournament/analyse`, Bitstamp acquisition/validation, causal candle filtering, regime and strategy analysis, risk-envelope construction, response provenance, and frontend rendering. A complete live request was deliberately not made: the authoritative data-mode contract prohibits external network calls, while the Bitstamp analysis service currently bypasses that contract.

The protected `data/raw/ohlcv.parquet` file was present and read-only verified: 42,326 hourly rows from `2022-01-01 00:00 UTC` to `2026-10-30 13:00 UTC`, with no duplicate/out-of-order timestamps, hourly gaps, non-finite OHLCV values, or invalid OHLC geometry. Its SHA-256 matched the expected hash embedded in the failure-injection test. This corrects an earlier inventory statement that the file was missing.

## Priority findings

1. **BROKEN - provider network policy bypass.** [`is_external_network_permitted`](./engine/data_mode.py#L100) returns `False` in every mode. [`fetch_raw_bitstamp_ohlcv`](./engine/bitstamp_market_data_service.py#L171) invokes PowerShell HTTP or `httpx` without enforcing that policy; the analysis route reaches it through [`get_or_refresh_bitstamp_data`](./engine/bitstamp_market_data_service.py#L326). Provider failures do fail closed with HTTP 503 and no Coinbase or local-dataset substitution, but the outbound request can already occur.
2. **BROKEN - stale local feed can be labeled live.** [`market_candles`](./api/market_monitor_routes.py#L280) serves the hourly Bitstamp Parquet when the file exists and returns `status: LIVE`, without freshness or full integrity validation on that branch. The frontend accepts `BITSTAMP` as a ready chart source in [`app.js`](./web/app.js#L17776). The analysis route normally fetches its own Bitstamp data rather than using the submitted chart candles, so displayed and analyzed snapshots may differ.
3. **NOT ESTABLISHED - Standard HAR performance.** The registry specifies `rv7d_var_ann`, a 168-hour horizon, and `rv_1d`, `rv_7d`, and `rv_30d` features in [`authoritative_model_registry.py`](./models/authoritative_model_registry.py#L78). The referenced `experiments/results/freeze/standard_har_v1.joblib` is absent, and the registry artifact hash is a placeholder. QLIKE, MAE, RMSE, relative improvement, DM/HLN tests, Holm-adjusted results, confidence intervals, and regime results for the registered artifact are all **NOT ESTABLISHED**.
4. **BROKEN - unverified calibration presentation.** [`decoupled_analysis_engine.py`](./engine/decoupled_analysis_engine.py#L211) uses fixed C2 envelope widths and embedded historical coverage claims. When `source_exchange` is absent, the code defaults it to Coinbase and can enter that envelope branch; Bitstamp input is suppressed as a source mismatch. The same code embeds a prospective-ledger status of `7/100`, which conflicts with the current ledger and is not authoritative. [`range_forecast_service.py`](./engine/range_forecast_service.py#L153) uses fixed excursion multipliers, while [`uncertainty_service.py`](./engine/uncertainty_service.py#L48) defaults `conformal_calibrated=True`. These are not evidence of a current, reproducible calibration artifact.
5. **UNVALIDATED - regime utility and prospective evidence.** The regime classifier is a 200-bar deterministic threshold classifier ([`regime_strategy_tournament.py`](./engine/regime_strategy_tournament.py#L180)); independent out-of-sample usefulness is not established. The prospective ledger has 10 seven-day records, 5 resolved and 5 pending. Nine adjacent issue windows overlap, leaving at most one non-overlapping 168-hour interval under a simple greedy selection. This is not sufficient confirmatory evidence.
6. **UNDERDEVELOPED - end-to-end and failure-injection coverage.** Existing mocked tests cover important provider, candle, freshness, and fail-closed cases. The audit did not establish coverage for incomplete candles, analysis-model exceptions or missing model output, malformed analysis responses, or full UI-to-response integration.

## Test-count reconciliation

- `artifacts/v35_3_regression_summary.json` records **320 passed** across **75 categorized Python test files**: 24 platform, 41 econometric, and 10 strategy files. This is the categorized regression-runner result.
- V35.3's **343 / 77** figure adds the separately recorded 12-case adversarial script and 11 frontend check groups. It is an aggregate claim, not one runner's measured output; the frontend script does not emit a test-case count.
- `artifacts/test_inventory.csv` reports **363 files / 1,704 AST-discovered test-like functions**. AST discovery is not pytest collection. The default runner omits 288 `legacy`-categorized files. The exact count deselected by `pytest.ini`'s `not network` marker is not recorded.
- `full_test_run_current.log` is an incomplete progress excerpt with failure markers and no final summary. It does not establish current full-suite health.
- In this audit session, the focused command covering provider failure injection, market-monitor routes, model registry/variance, and uncertainty reported **29 passed**; `node tests_frontend.js` reported **All Frontend Unit Tests Passed Successfully**. Neither is an end-to-end run.

## Minimal proposed work (not authorized or applied)

1. Enforce `assert_no_external_network` before any Bitstamp subprocess/socket call and test that restricted modes block before process/network creation.
2. Validate cached candles before serving them; return an explicit stale/unavailable status and ensure the frontend does not show stale data as ready.
3. Keep C2 disabled and suppress its interval/coverage output in this milestone. Default unknown source and missing calibration provenance to unavailable. Do not change a statistical gate to obtain passing results.
4. Add focused tests for incomplete candles, model exceptions/missing outputs, malformed analysis responses, and the source-missing calibration branch.
5. Do not retrain, replace, promote, or modify Standard HAR. Recover the registered artifact and matching hash through governed provenance before attempting an exact-model evaluation. Until then, report accuracy as **NOT ESTABLISHED**.

## Final status

**V35.4 acceptance is not met.** Keep research-only authorization, production serving locked, prospective collection unchanged, C2 disabled, unvalidated calibration outputs suppressed, and live trading disabled.
