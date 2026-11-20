# BTCognitive — Master Feature-by-Feature QA Matrix (V32.28)

**Execution Date:** 2026-10-25  
**Version:** V32.28  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed)  
**Positive-Edge Alerts Emitted:** `0`  
**Terminal Software QA State:** `SOFTWARE_QA_PASS`  
**Terminal Scientific State:** `NO_GO_NO_VALIDATED_EDGE` / `NO_GO_EVIDENCE_GAP`  

---

## 1. Feature QA Matrix (QA-A through QA-J)

| QA Section | Feature / Invariant Tested | Source File(s) | Test Command(s) | Evidence & Exit Code | QA Verdict | Defect / Note |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **QA-A: Safety & Integrity** | Live trading disabled across config, API, and UI layers. | `config/security.py`, `engine/smart_entry_pipeline.py` | `pytest tests/test_prospective_shadow_collector.py -k test_live_trading_disabled_guard` | `test_live_trading_disabled_guard PASSED` (Exit 0) | **PASS** | Live order execution permanently disabled; throws `RuntimeError`. |
| **QA-A: Safety & Integrity** | Protected files bit-identical byte-for-byte SHA-256 match. | All 5 protected files in `data/` and `data/raw/` | Python SHA-256 baseline comparator | All 5 hashes verified 100% bit-identical | **PASS** | Zero ledger mutation or file truncation. |
| **QA-A: Safety & Integrity** | Anti-tampering & pickle rejection. | `models/registry/research/` | Python inspect script | `AMFORGE/tabicl-gold-btc-finetuned` rejected; zero pickle unpickling | **PASS** | Pickle deserialization prevented. |
| **QA-B: Data Contracts** | Monotonic timestamps, OHLC geometry, duplicate rejection, freshness. | `engine/data_verification.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_data_contract` | 6 tests passed (Geometric, Duplicates, Freshness, Causal) | **PASS** | Rejects broken geometry and stale feeds. |
| **QA-B: Data Contracts** | Legacy mixed CCXT dataset quarantined for confirmatory claims. | `data/raw/ohlcv.parquet` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_data_contract_rejects_unverified_provenance` | `test_data_contract_rejects_unverified_provenance_when_required PASSED` | **PASS** | `UNVERIFIED_SOURCE` fails closed when authenticated data is required. |
| **QA-B: Data Contracts** | Authenticated Coinbase hourly dataset lineage and gap audit. | `data/research/coinbase_btc_usd_hourly_v1/` | Python manifest verification | 33,424 bars, 3 documented outages (3h, 5h, 5h), 0 duplicates, 0 synthetic bars | **PASS** | Lineage verified against Coinbase REST API endpoint. |
| **QA-C: Strategy Engine** | Causal breakout channel excluding bar $t$ (`shift(1)`). | `engine/strategy_signal_engine.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_donchian` | `test_donchian_channel_excludes_signal_bar PASSED` | **PASS** | Excludes current bar $t$; fills at Open $t+1$. |
| **QA-C: Strategy Engine** | Spot short restriction mapped to CASH. | `engine/strategy_signal_engine.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_spot_short` | `test_spot_short_restriction_maps_to_cash_and_abstains PASSED` | **PASS** | Spot shorts map to `CASH / SPOT_SHORT_INELIGIBLE`. |
| **QA-C: Barrier Resolver** | Deterministic triple-barrier resolution with conservative collisions. | `engine/barrier_resolver.py` | `pytest tests/test_entry_contracts_and_resolver.py` | 13/13 tests passed | **PASS** | Ambiguous intrabar collisions resolve strictly as `SL_FIRST`. |
| **QA-C: Barrier Resolver** | Opening gap execution through stop/target. | `engine/barrier_resolver.py` | `pytest tests/test_entry_contracts_and_resolver.py -k test_resolver_opening_gap` | 2 tests passed (Gap TP, Gap SL) | **PASS** | Fills at Open, capturing true slippage. |
| **QA-C: Barrier Resolver** | Timeout signed return accounting at horizon $H=24$. | `engine/barrier_resolver.py` | `pytest tests/test_entry_contracts_and_resolver.py -k test_resolver_timeout` | `test_resolver_timeout_at_horizon PASSED` | **PASS** | Signed P&L preserved at horizon candle Open. |
| **QA-D: Model Registry** | Model artifact SHA-256 verification against freeze metadata. | `engine/directional_forecast_service.py` | `pytest tests/test_v32_25_directional_integration.py -k test_v32_25_directional_models_sha256` | `test_v32_25_directional_models_sha256_match_authoritative_manifest PASSED` | **PASS** | 1h, 4h, 24h joblib models match metadata. |
| **QA-D: Model Registry** | Tampered artifact fails closed. | `engine/directional_forecast_service.py` | `pytest tests/test_v32_25_directional_integration.py -k test_v32_25_tampered_model_artifact_fails_closed` | `test_v32_25_tampered_model_artifact_fails_closed PASSED` | **PASS** | Corruption raises immediate load error. |
| **QA-D: Model Registry** | Horizon mismatch fails closed. | `engine/smart_entry_pipeline.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_pipeline_horizon_mismatch_fails_closed` | `test_pipeline_horizon_mismatch_fails_closed PASSED` | **PASS** | 72h strategy cannot consume 24h model. |
| **QA-D: Model Registry** | Directional probabilities segregated from first-passage barrier probabilities. | `engine/smart_entry_pipeline.py` | Code audit & unit tests | Directional GBDT probabilities attached as context only; never used as $p_{\text{TP}}$ | **PASS** | Strict target separation enforced. |
| **QA-D: Model Registry** | Chronos-2 foundation benchmark status. | `models/foundation/chronos_adapter.py` | `pytest tests/test_foundation_adapters.py -k test_chronos_adapter` | `test_chronos_adapter_forecast PASSED` | **PASS** | Interface verified. Marginal quantiles isolated from runtime. Dependencies isolated in `requirements-research.txt`. |
| **QA-E: Meta-Model** | Tri-state probability partition sum normalization. | `engine/trade_outcome_evaluator.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_probability_partition_sum_normalization` | `test_probability_partition_sum_normalization PASSED` | **PASS** | Enforces $p_{\text{TP}} + p_{\text{SL}} + p_{\text{TO}} = 1.0 \pm 10^{-3}$. |
| **QA-E: Meta-Model** | Friction converted to R units; reduces net EV. | `engine/trade_outcome_evaluator.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_friction_in_r` | `test_friction_in_r_and_higher_friction_reduces_net_ev PASSED` | **PASS** | Higher friction monotonically lowers $EV_{\text{net}}$. |
| **QA-E: Meta-Model** | Statistical uncertainty rejection when 95% CI lower bound $\le 0$. | `engine/trade_outcome_evaluator.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_statistical_uncertainty_rejection` | `test_statistical_uncertainty_rejection_when_lower_bound_negative PASSED` | **PASS** | Rejects when empirical lower bound $\le 0.0$. |
| **QA-E: Meta-Model** | Purged/embargoed chronological training & calibration. | `research/experiments/run_phase4_meta_model.py` | Master pipeline execution | 24h embargo applied; Brier skill +0.0115; 0/130 holdout trades admitted | **PASS** | No lookahead leakage across splits. |
| **QA-F: Smart Entry Gates** | Gate 1: `UNVERIFIED_SOURCE` | `engine/data_verification.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_data_contract_rejects_unverified_provenance` | PASSED | **PASS** | Confirmatory gate blocks unverified data. |
| **QA-F: Smart Entry Gates** | Gate 1: `DATA_CONTRACT_BREACH` | `engine/data_verification.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_data_contract_rejects_geometric` | PASSED | **PASS** | Rejects high < low / high < open. |
| **QA-F: Smart Entry Gates** | Gate 1: `STALE_DATA` | `engine/data_verification.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_data_contract_rejects_stale` | PASSED | **PASS** | Rejects candles older than $2\times$ timeframe. |
| **QA-F: Smart Entry Gates** | Gate 1: `FEATURE_UNAVAILABLE` | `engine/data_verification.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_data_contract_rejects_unavailable` | PASSED | **PASS** | Rejects missing microstructure inputs. |
| **QA-F: Smart Entry Gates** | Gate 3: `HORIZON_MISMATCH` | `engine/smart_entry_pipeline.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_pipeline_horizon_mismatch` | PASSED | **PASS** | Blocks incompatible forecast horizons. |
| **QA-F: Smart Entry Gates** | Gate 2: `SPOT_SHORT_INELIGIBLE` | `engine/strategy_signal_engine.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_spot_short` | PASSED | **PASS** | Blocks shorting on spot exchange. |
| **QA-F: Smart Entry Gates** | Gate 4: `META_MODEL_UNAVAILABLE` | `engine/smart_entry_pipeline.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_full_pipeline_fails_closed` | PASSED | **PASS** | Fails closed when meta-model is missing. |
| **QA-F: Smart Entry Gates** | Gate 5: `STATISTICAL_UNCERTAINTY` | `engine/trade_outcome_evaluator.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_statistical_uncertainty` | PASSED | **PASS** | Rejects when lower bound $\le 0.0$. |
| **QA-F: Smart Entry Gates** | Gate 5: `NEGATIVE_NET_EXPECTANCY` | `engine/trade_outcome_evaluator.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_negative_net_expectancy` | PASSED | **PASS** | Fails closed when $EV_{\text{net}} \le 0.0$. |
| **QA-F: Smart Entry Gates** | Gate 6: `REGIME_MISMATCH` | `engine/strategy_signal_engine.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_bollinger_reversion` | PASSED | **PASS** | Mean-reversion requires range regime. |
| **QA-G: Alerts & Shadow Runner** | Alert deduplication & disclaimer enforcement. | `engine/smart_entry_pipeline.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_research_alert_deduplication` | PASSED | **PASS** | Hash deduplication prevents spam; disclaimer verified. |
| **QA-G: Alerts & Shadow Runner** | Zero positive-edge alerts emitted on failure. | `engine/smart_entry_pipeline.py` | `pytest tests/test_strategy_to_alert_pipeline.py -k test_full_pipeline_fails_closed` | `stage6_research_alert['alert_emitted'] is False` | **PASS** | Exactly 0 alerts emitted when gates fail. |
| **QA-G: Alerts & Shadow Runner** | Prospective shadow collector idempotency & file locking. | `engine/prospective_shadow_collector.py` | `pytest tests/test_prospective_shadow_collector.py` | 12/12 tests passed | **PASS** | Lock file prevents duplicate instances; append-only verified. |
| **QA-G: Alerts & Shadow Runner** | Prospective worker resilience & settlement grace period. | `engine/prospective_worker.py` | `pytest tests/test_prospective_worker_and_resilience.py` | 6/6 tests passed | **PASS** | Handles corrupted entries and settlement grace. |
| **QA-H: API & Operations** | In-process FastAPI TestClient route tests. | `api/routes_research.py`, `api/server.py` | `pytest tests/test_smart_entry_api.py tests/test_strategy_to_alert_pipeline.py -k test_api` | 8 API tests passed | **PASS** | `/smart-entry/pipeline/latest` returns 200 OK, `live_trading: "DISABLED"`. |
| **QA-H: API & Operations** | Isolated HTTP process verification on port 8899. | `research/experiments/verify_isolated_api_server.py` | Python script execution | Server booted, OpenAPI routes verified, shut down cleanly | **PASS** | Ephemeral test server cleanly terminated. |
| **QA-H: API & Operations** | Port 8000 listener status disclosure. | Live operating system | `netstat -ano \| findstr :8000` | Port 8000 verified inactive (no listener) | **PASS** | Disclosed truthfully: no active background listener. |
| **QA-H: Frontend Operations** | Frontend polling budget, formatters, and deduplication. | `tests_frontend.js`, `web/app.js` | `node tests_frontend.js` | 100% passed (steady state: 29.5 req/min vs 60 limit) | **PASS** | Verified terminal markers and rate limiter. |
| **QA-I: Dependencies & Docs** | Core vs. research requirements separation. | `requirements.txt`, `requirements-research.txt` | Python compilation & file inspect | Clean separation between runtime LightGBM/Torch and optional Chronos/Transformers | **PASS** | Runtime requirements remain lean. |
| **QA-J: Full Regression Round** | Full 69-test backend test suite execution. | `tests/` | `pytest tests/test_strategy_to_alert_pipeline.py tests/test_entry_contracts_and_resolver.py tests/test_smart_entry_api.py tests/test_v32_25_directional_integration.py tests/test_prospective_shadow_collector.py tests/test_prospective_worker_and_resilience.py` | **69 passed in 33.15s** (100% pass rate) | **PASS** | Zero test failures across all retained components. |
| **QA-J: Full Regression Round** | Red-team review for lookahead leakage & false claims. | Independent audit pass | Comprehensive source inspection | Verified: no lookahead, no pickle execution, no fabricated data | **PASS** | Final claims match empirical artifacts. |

---

## 2. Summary of QA Status

- **Total Unit & Integration Tests Executed:** 69 backend tests + full frontend suite.
- **Passed:** 69 / 69 backend tests (100%), 100% frontend checks.
- **Failed:** 0.
- **Terminal Software QA State:** **`SOFTWARE_QA_PASS`**.
- **Terminal Scientific Verdict:** **`NO_GO_NO_VALIDATED_EDGE` / `NO_GO_EVIDENCE_GAP`** (because the strategy baseline loses -0.2465 R to -0.9898 R after transaction costs, and the calibrated meta-model admits 0 trades on holdout).
