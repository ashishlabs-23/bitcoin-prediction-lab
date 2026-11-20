# BTCognitive V35.4 Analysis Pipeline Audit

**Audit date:** 2026-11-03  
**Scope:** Read-only trace of the BTC-USD analysis request and its data, risk, and rendering paths.  
**Result:** A complete live end-to-end request was not run. The actual provider call is prohibited by the current data-mode contract, and the code path does not enforce that prohibition.

## 1. Request path and contracts

| Stage | Source and function | Input / output | Provenance, time, units | Failure and missing-data behavior | Evidence and assessment |
|---|---|---|---|---|---|
| Chart candles | [`market_candles`](./api/market_monitor_routes.py#L280); frontend chart state in [`app.js`](./web/app.js#L17776) | API response carries `status`, `symbol`, `interval`, `count`, `candles`, `source`, `retrieved_at`, and `degraded`. Each candle has epoch-seconds `time` and OHLCV numeric fields. | Hourly cache source is Bitstamp BTC/USD. Timestamps are candle opens; the route includes a retrieval timestamp from the sidecar provenance file. Prices are USD; volume is provider-provided and not explicitly unit-annotated in this response. | Unsupported symbol/interval returns an explicit unsupported/unavailable status. The 1h Bitstamp cache branch checks file existence and read success, but does not validate freshness, gaps, candle geometry, or the whole file before returning `LIVE`. | The local hourly cache was observed ending `2026-11-02 17:00 UTC` during the audit, while the service freshness limit is 2 hours. The endpoint branch does not apply that limit. |
| Closed-candle request construction | [`buildClosedHourlyAnalysisCandles`](./web/app.js#L285); [`handleAnalyse`](./web/app.js#L17766) | Filters to bars satisfying `time + 3600 <= now`, maps to ISO `timestamp_utc`, copies OHLCV, and sets `is_closed: true`. The request also includes instrument, timeframe, source, request ID, current chart price, freshness policy, and `auto_tournament`. | Client timestamps are seconds converted to UTC ISO. It does not itself enforce hourly continuity or uniqueness. | Fewer than 168 bars, a non-ready source, unsupported timeframe, or missing/nonpositive current price blocks the UI request. Browser errors are surfaced in the view. | Frontend tests pass; no browser-to-real-backend test was performed. |
| Request validation | [`AnalyseRequestModel`](./api/routes_tournament.py#L435), [`post_analyse_market`](./api/routes_tournament.py#L522) | Request fields include `instrument`, `timeframe`, `data_source`, `request_id`, `live_price`, `enforce_freshness`, `max_age_hours`, optional candles, `auto_tournament`, and `force_fresh_tournament`. | Pydantic structural parsing; request payload is hashed as finite JSON. | Unsupported instrument/timeframe and invalid JSON are rejected. `force_fresh_tournament` is rejected. Request-ID reuse with a changed digest returns 409. No explicit response Pydantic model is declared; the endpoint returns a generic dictionary. | Code inspection; not every validation branch was runtime tested in this audit. |
| Provider retrieval | [`_post_analyse_market`](./api/routes_tournament.py#L537), [`get_or_refresh_bitstamp_data`](./engine/bitstamp_market_data_service.py#L326), [`fetch_raw_bitstamp_ohlcv`](./engine/bitstamp_market_data_service.py#L171) | The normal non-fixture route calls Bitstamp and receives a validated DataFrame plus metadata. It does not consume submitted chart candles as the analysis dataset. | Bitstamp public BTC/USD 1h OHLC; service parses timestamps and provider string numerics. The result carries source/provider, retrieval time, raw payload hash, and persistence provenance. | Timeout, HTTP status, empty payload, malformed values, invalid OHLC, duplicate/nonmonotonic timestamps, gaps, and incomplete candles have explicit service failure codes. Route failure is HTTP 503 and does not fall back to Coinbase or `data/raw/ohlcv.parquet`. | Mocked failure tests cover several cases. The public provider was not contacted. **BROKEN:** service fetch does not call `assert_no_external_network`, although [`is_external_network_permitted`](./engine/data_mode.py#L100) is false in every mode. |
| Candle/freshness checks | [`validate_bitstamp_ohlc`](./engine/bitstamp_market_data_service.py#L85), [`check_data_freshness_and_gaps`](./engine/regime_strategy_tournament.py#L574), [`_validate_hourly_candles`](./engine/regime_strategy_tournament.py#L684) | Provider data becomes a canonical UTC-indexed DataFrame with an `available_time` at candle close. The analysis engine filters `is_closed` when supplied and computes a candle watermark/hash. | UTC timestamps; OHLC in USD; provider volume; freshness uses completed-candle close time and a default 2-hour policy. | Invalid candles return an abstention/invalid-candle result. If freshness enforcement is requested, stale or gapped input blocks a live setup. The analysis request defaults `enforce_freshness=False`, while the UI sets it true for Bitstamp/Coinbase chart sources. | Tests include stale data and candle validation. The separate cached-candles route does not use this validator/freshness check. |
| Regime and strategy analysis | [`analyse_current_market`](./engine/regime_strategy_tournament.py#L726), [`MarketRegimeClassifier.classify`](./engine/regime_strategy_tournament.py#L183) | Closed hourly candles produce indicator/regime output, strategy screening, candidates/rejections, and setup diagnostics. | Technical inputs include EMA20/50/200, ADX14, ATR14, Bollinger bandwidth, and warmup history. Classifier requires 200 bars; trend/volatility outputs are not return-forecast accuracy. | Invalid/insufficient input yields `ABSTAIN`/unknown. Regime uses fixed thresholds (e.g. expansion if ATR or bandwidth criteria pass; trend if ADX threshold passes; compression by bandwidth threshold). | Deterministic threshold behavior is inspectable; out-of-sample regime utility and transition persistence are not established by this audit. |
| Tournament and decision | [`execute_integrated_analyse_and_tournament`](./engine/regime_strategy_tournament.py#L1767) | Current screening feeds the bounded/cached tournament evidence path and a decision object; response includes strategy assessment, tournament, decision, status, timings, and read-only flags. | Analysis timestamp is UTC. This is strategy/regime assessment, not the registered Standard HAR inference path. | With no candidates or invalid analysis, the decision should abstain. Exceptions are not specifically caught and tested at this endpoint boundary. `force_fresh_tournament` is disallowed from the interactive route. | No simulated attempt is created by this analysis function; this is separate from any later user-triggered simulated-entry endpoint. |
| Volatility/risk output | [`decoupled_analysis_engine.py`](./engine/decoupled_analysis_engine.py#L185), [`generate_forecast`](./engine/range_forecast_service.py#L125), [`evaluate_uncertainty`](./engine/uncertainty_service.py#L41) | Produces trailing volatility summaries, a 7-day envelope on eligible source paths, and 24-hour MFE/MAE bounds. | 7-day variance/volatility and 24-hour excursion bounds are distinct outputs and targets. Prices are USD; excursion bounds are proportional multipliers converted to price levels. | Bitstamp is suppressed as an unverified calibration-source mismatch. If `source_exchange` is absent, code defaults it to Coinbase and can enter the C2 branch. The embedded `7/100` prospective status is stale versus the current ledger. The excursion generator uses fixed multipliers; uncertainty defaults to calibrated unless explicitly told otherwise. | **BROKEN:** unknown source can be treated as Coinbase; fixed values and default calibration flag do not establish calibration. C2 must remain disabled. Never attribute these outputs to Standard HAR. |
| Provenance and serialization | [`_attach_analysis_provenance`](./api/routes_tournament.py#L391) and route return | Attaches request source, submitted count/hash, analyzed count/window hash, latest closed timestamp, and `OFFLINE_RESEARCH_ONLY` authorization. FastAPI serializes a generic dictionary. | Request and analyzed-window SHA-256 are separate; this is useful evidence that the submitted and analyzed snapshots may differ. | Provider failure is explicit; response-schema validation and model-output validation are not established. | Generic response mapping is assigned directly to frontend state. |
| Frontend rendering | [`handleAnalyse`](./web/app.js#L17776), [`app.js`](./web/app.js#L17844), regime panel [`app.js`](./web/app.js#L18729) | On successful fetch, the frontend stores `res` as analysis data and renders values from that object. | Displayed result fields originate from the backend response object; the frontend also has separately acquired chart price/candles. | Request errors clear analysis state and show an error. Response shape is not validated against a generated contract before rendering. | Frontend unit tests pass; no end-to-end browser/backend request was executed. |

## 2. Source and target separation

The registered Standard HAR is **not the model executed by `/api/tournament/analyse`**. That request produces a deterministic regime/strategy screen and a separate decoupled volatility/risk payload. The registry separately names:

- Standard HAR: annualized 7-day realized variance, `rv7d_var_ann`, 168 hours, `rv_1d`, `rv_7d`, and `rv_30d` features; offline-only.
- A distinct directional model identity: sign of the 1-hour forward log return. Its accuracy cannot be inferred from volatility losses.
- A distinct 24-hour realized-variance identity and separate excursion estimates. Neither substitutes for the 168-hour Standard HAR target.

No model registry identity or output should be inferred from the UI's labels alone. In particular, volatility-envelope coverage is not directional hit rate or trading profitability.

## 3. Failure-injection coverage

| Scenario | Existing evidence | Audit result |
|---|---|---|
| Provider timeout | `test_failure_1_http_timeout`, with fetch mocked | Covered as a service failure; not a real HTTP timeout. |
| HTTP 429 / HTTP error | `test_failure_2_http_429_rate_limit`, with fetch mocked | Error metadata covered; actual provider client status handling not exercised. |
| Empty response | `test_failure_4_empty_response` | Covered. |
| Malformed upstream payload | `test_failure_3_malformed_json` supplies a malformed dictionary to validator | Validator rejection covered; raw HTTP JSON decoding path only partly represented. |
| Stale data | `test_failure_8_stale_response_fail_closed` | Downstream stale detection/setup blocking covered; stale cache endpoint falsely labeled `LIVE` is not covered. |
| Missing candle/gap | `test_failure_6_missing_candle_gap` | Covered at service validation. |
| Duplicate candle | `test_failure_5_duplicate_candles` | Covered at service validation. |
| Invalid OHLC | `test_failure_7_invalid_ohlc_extrema` | Covered for high/low geometry; not every numeric edge case. |
| Incomplete candle | Validator checks candle end against retrieval time | No explicit targeted incomplete-candle test was identified. |
| Provider outage/no fallback | `test_failure_9`, `12`, `13`, `15` | Mocked fail-closed/no-substitution behavior covered. |
| Successful retrieval | `test_failure_10` uses a mocked response and in-memory cache | Mock success only; no live provider retrieval. |
| Analysis/model exception | No dedicated test identified | Not established; route-level exception behavior needs test. |
| Missing model output | No dedicated test identified | Not established. |
| Calibration unavailable | Uncertainty service tests include an explicit `conformal_calibrated=False` branch | Unit branch is covered, but production call defaults to `True`; integration not established. |
| Invalid analysis API response | No response-model validation test identified | Not established; generic dictionary response is rendered without contract validation. |

## 4. Root causes and minimal proposals

### A. Network policy bypass

**Root cause:** Provider fetch function directly performs HTTP/subprocess work without invoking the central policy guard.  
**Proposal:** Enforce the network guard before any request/process; keep offline response explicit.  
**Acceptance:** In all restricted modes, a test proves the guard raises before socket or PowerShell process creation; API response is explicit and no fallback occurs.

### B. Stale cached data marked live

**Root cause:** The hourly cache endpoint uses file existence as a sufficient condition for `LIVE`.  
**Proposal:** Validate snapshot integrity and completed-candle freshness before returning a live/ready status; report stale/unavailable explicitly.  
**Acceptance:** Stale, malformed, missing, and fresh-cache route tests verify response status and frontend readiness behavior.

### C. Calibration and source identity

**Root cause:** Missing source identity defaults to Coinbase for the C2 branch; fixed constants are labeled with empirical calibration status; uncertainty defaults to calibrated.  
**Proposal:** Missing/unknown source and missing calibration provenance must fail closed; suppress calibrated coverage language until supported by a verifiable artifact.  
**Acceptance:** Unknown-source and missing-artifact calls return unavailable/uncalibrated output with no nominal coverage claim; Bitstamp remains suppressed.

### D. Incomplete API/failure contracts

**Root cause:** The route returns a generic dictionary and focused tests do not cover all requested failure modes.  
**Proposal:** Add a response contract and focused tests for incomplete candles, model exception/missing output, unavailable calibration, and malformed response.  
**Acceptance:** Each failure returns an explicit non-success/abstention shape; frontend does not render malformed outputs as success.

No code changes are authorized by this report. Standard HAR must remain untouched until its registered artifact and provenance are recovered.
