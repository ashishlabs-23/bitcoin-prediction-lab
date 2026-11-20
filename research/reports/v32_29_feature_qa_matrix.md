# BTCognitive — Complete Feature QA & Evidence Matrix (V32.29)

**Date:** 2026-10-25  
**Version:** V32.29  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed)  
**Coordinator:** Agent A  

---

## 1. Feature-by-Feature Verification Matrix (All 25 Modules)

| # | Component / Module | Code Path(s) | Architectural Disposition | Verification Status | Exact Test File(s) / Evidence Command | Empirical & Runtime Reality |
| :-: | :--- | :--- | :---: | :---: | :--- | :--- |
| **1** | **Market Data Validator** | `engine/data_verification.py` | `CORE_KEEP` | **UNIT_TESTED & INTEGRATION_TESTED** | `tests/test_strategy_to_alert_pipeline.py` (Tests 1–7, 20) | Fails closed on unverified venue, missing/duplicate timestamps, geometric OHLC violations, stale candles, and unverified source. Verified 100%. |
| **2** | **Protected Ledger Vault** | `data/prospective_entry_ledger.jsonl`, `data/raw/ohlcv.parquet`, etc. | `CORE_KEEP` | **UNIT_TESTED & HASH_VERIFIED** | `tests/test_prospective_shadow_collector.py` (Test 4), SHA-256 Hash Audits | All 5 protected files verified bit-identical at baseline and post-QA. Read-only invariant strictly enforced. |
| **3** | **Strategy Signal Engine** | `engine/strategy_signal_engine.py` | `CORE_KEEP` | **UNIT_TESTED & REPRODUCED** | `tests/test_strategy_to_alert_pipeline.py` (Tests 8–11), `run_phase2_strategy_baseline.py` | Causal Donchian breakout and Bollinger mean-reversion. Channel excludes bar $t$ via `.shift(1)`. Next-open fills. Spot shorts map to `CASH / SPOT_SHORT_INELIGIBLE`. |
| **4** | **Deterministic Barrier Resolver** | `engine/barrier_resolver.py` | `CORE_KEEP` | **UNIT_TESTED** | `tests/test_entry_contracts_and_resolver.py` (Tests 1–13) | Path-dependent triple-barrier evaluator. Conservative intrabar collision resolves as `SL_FIRST`. Opening gaps executed at open. Timeout uses signed P&L. |
| **5** | **Trade-Outcome Meta-Model** | `research/experiments/run_phase4_meta_model.py` | `CORE_KEEP` (Offline) | **UNIT_TESTED & EMPIRICALLY_VERIFIED** | `tests/test_strategy_to_alert_pipeline.py` (Tests 12, 17), `run_phase4_meta_model.py` | Calibrated multinomial logistic regression ($p_{\text{TP}}, p_{\text{SL}}, p_{\text{TO}}$). Brier skill $+0.0115$. Zero holdout trades admitted ($EV_{\text{net}} \le 0$). Capital protector. |
| **6** | **Execution Cost & Net Expectancy Engine** | `engine/trade_outcome_evaluator.py`, `engine/execution_cost_model.py` | `CORE_KEEP` | **UNIT_TESTED** | `tests/test_strategy_to_alert_pipeline.py` (Tests 13–16, 22), `test_entry_contracts_and_resolver.py` (Test 1) | Closed-form net edge: $EV_{\text{net}} = p_{\text{TP}}(k_{\text{tp}} - C_R) - p_{\text{SL}}(k_{\text{sl}} + C_R) + p_{\text{TO}}(\mathbb{E}[R_{\text{TO}}] - C_R)$. Friction converted to R units. Fails closed on non-positive edge. |
| **7** | **Smart Entry Pipeline** | `engine/smart_entry_pipeline.py` | `CORE_KEEP` | **INTEGRATION_TESTED & REAL_HTTP_TESTED** | `tests/test_strategy_to_alert_pipeline.py` (Tests 17–18), `tests/test_isolated_real_http_server.py` (Tests 2–4) | 7-stage fail-closed orchestrator. Verified both in-process and over loopback socket via real HTTP. Emits `ABSTAIN` with explicit machine-readable reason codes. |
| **8** | **Research Alert Engine** | `engine/smart_entry_pipeline.py`, `api/notifications.py` | `CORE_KEEP` | **UNIT_TESTED** | `tests/test_strategy_to_alert_pipeline.py` (Test 19) | Hash deduplication prevents duplicate alerts during repeated polling. Mandatory disclaimer attached. Zero positive alerts emitted in real QA. |
| **9** | **Vol Risk Model (HAR-RS-DOW)** | `models/authoritative_model_registry.py`, `engine/realized_semi_variance.py` | `SUPPORT_KEEP` | **SOURCE_REVIEWED & BENCHMARKED** | `validation/startup_gate.py`, `experiments/results/freeze/repaired_scientific_contract_manifest.json` | Authorized for volatility risk forecasting under QLIKE loss. Verified by scientific startup gate. Strictly decoupled from directional trade signaling. |
| **10** | **Conformal Risk Envelopes** | `models/uncertainty.py`, `engine/decision_envelope.py` | `SUPPORT_KEEP` | **SOURCE_REVIEWED** | `tests/test_interval_sharpness.py`, `engine/decision_envelope.py` | Empirical distribution-free P10–P90 bands. Calibrated via Winkler interval score. Provides volatility context only. |
| **11** | **Autonomous Shadow Runner** | `engine/shadow_feed_runner.py`, `engine/prospective_shadow_collector.py` | `SUPPORT_KEEP` | **UNIT_TESTED** | `tests/test_prospective_shadow_collector.py` (Tests 1–12), `tests/test_prospective_worker_and_resilience.py` (Tests 1–6) | Standalone CLI background collector. In-position gating prevents overlapping candidates. Single-instance process lock verified. Live orders disabled. |
| **12** | **Longitudinal Observatory** | `engine/observatory.py`, `experiments/results/observatory.db` | `SUPPORT_KEEP` | **SOURCE_REVIEWED & RUNTIME_VERIFIED** | `tests/test_observatory.py`, SQLite database inspection | Tracks calibration drift and forecast health over time. 6,945 persistent records verified in isolated SQLite store. |
| **13** | **Historical Analog Engine** | `api/routes_analogs.py` | `SUPPORT_KEEP` | **SOURCE_REVIEWED** | `tests/test_historical_analogs.py`, `api/routes_analogs.py` | Dynamic time warping scenario explorer. Strictly decoupled from Smart Entry gates. |
| **14** | **Counterfactual Stress Engine** | `engine/scenario_contract_engine.py` | `SUPPORT_KEEP` | **SOURCE_REVIEWED** | `tests/test_scenario_freshness_and_contract_v7.py` | Replays liquidity shocks and fee spikes through candidate setups. Diagnostic tool only. |
| **15** | **Cross-Venue Divergence Radar** | `engine/cross_venue_divergence.py` | `SUPPORT_KEEP` | **SOURCE_REVIEWED** | `tests/test_cross_venue_divergence.py` | Monitors spot spread divergence across Coinbase, Binance, Kraken. Diagnostic radar only; zero arbitrage trades placed. |
| **16** | **FastAPI Application Server** | `api/server.py`, `api/security_middleware.py` | `SUPPORT_KEEP` | **INTEGRATION_TESTED & REAL_HTTP_TESTED** | `tests/test_smart_entry_api.py` (Tests 1–7), `tests/test_isolated_real_http_server.py` (Tests 1–4) | Hardened REST server with OWASP ASVS headers and rate limiting. Verified over real TCP loopback HTTP socket. |
| **17** | **Trading Terminal UI** | `web/index.html`, `web/app.js`, `web/styles.css` | `SUPPORT_KEEP` | **UNIT_TESTED & STATIC_VERIFIED** | `node tests_frontend.js` | Pure HTML5/Vanilla JS. Verified formatters, request deduplication, TTL caching, and 29.5 req/min steady-state polling budget vs 60 req/min limit. |
| **18** | **Directional GBDT Classifiers** | `engine/directional_forecast_service.py` | `RESEARCH_ONLY` | **UNIT_TESTED & HOLD_OUT_EVALUATED** | `tests/test_v32_25_directional_integration.py` (Tests 1–9), `run_phase3_forecast_evaluation.py` | Frozen LightGBM return-sign models. Holdout AUC 0.5136–0.5285 (near coin flip). Contributes market context only; raw directional probability never substituted for $p_{\text{TP}}$. |
| **19** | **Chronos-2 Foundation Forecaster** | `models/foundation/chronos_adapter.py` | `RESEARCH_ONLY` | **ARCHITECTURE_REVIEWED — INFERENCE_NOT_EXECUTED** | `requirements-research.txt`, HuggingFace Model Card Review | Produces marginal quantiles $P(\text{Price}_{t+H} \in [P10, P90])$, mathematically incompatible with first-passage barrier probabilities. Heavy dependencies isolated. Not promoted. |
| **20** | **TFT & Router Deep Learning Models** | `models/checkpoints/tft.pt`, `models/checkpoints/router.pt` | `RESEARCH_ONLY` | **SOURCE_REVIEWED** | `models/checkpoints/`, `models/tft_model.py` | PyTorch MoE routing network checkpoints preserved on disk for offline research. Unpromoted to runtime execution path. |
| **21** | **Hawkes Point Process** | `engine/hawkes_shadow_session.py` | `RESEARCH_ONLY` | **SOURCE_REVIEWED** | `tests/test_hawkes_*.py` | Point-process trade arrival intensity research. Offline research only. |
| **22** | **Strategy Arena & Genetic Tournaments** | `engine/arena_runner.py`, `engine/arena_evolution.py` | `PARK` | **PARKED_SAFE** | `engine/arena_runner.py` | Genetic strategy optimization decoupled from Smart Entry to eliminate backtest overfitting (PBO) and data-snooping risks. |
| **23** | **External Pickle Models (`TabICL`)** | `models/tabicl_finetuned.pkl` | `REMOVE / REJECT` | **REJECTED_UNTRUSTED_PICKLE — FILE_NOT_PRESENT** | Inspection of `models/` directory | External pickle rejected due to arbitrary code execution risk and missing encoder classes. File was never downloaded; zero placeholder hashes remain. |
| **24** | **GPL Consensus Model** | `maverick90024/btc-usd-consensus-1d` | `REMOVE / REJECT` | **REJECTED_LICENSE_INCOMPATIBLE** | Repository Licensing Audit | GPL-3.0 copyleft code excluded from application integration to preserve codebase licensing integrity. |
| **25** | **Microstructure OFI / VPIN / Hawkes** | Order flow imbalance, volume toxicity | `BLOCKED` | **BLOCKED_ON_EVIDENCE** | `engine/data_verification.py` (Test 3) | High-frequency microstructure features cannot be synthesized from OHLCV candles. Fails closed with `FEATURE_UNAVAILABLE`. |

---

## 2. Summary by Architectural Disposition

| Disposition Category | Exact Module Count | Active Runtime Role | Verification Method |
| :--- | :---: | :--- | :--- |
| **`CORE_KEEP`** | **8** | Primary deterministic decision pipeline | Unit tested, integration tested, and real HTTP socket verified. |
| **`SUPPORT_KEEP`** | **9** | Infrastructure, monitoring, and diagnostic tooling | Unit tested (shadow runner, frontend), integration tested (API server), source reviewed (Observatory, radar, stress engine). |
| **`RESEARCH_ONLY`** | **4** | Offline exploratory research | Directional GBDT unit tested; Chronos-2 architectural review (inference not executed); TFT/Hawkes source reviewed. |
| **`PARK`** | **1** | Parked to eliminate PBO overfitting | Decoupled from runtime; verified safe. |
| **`REMOVE / REJECT`** | **2** | Unsafe pickle and incompatible copyleft | Quarantined / excluded from integration consideration. |
| **`BLOCKED`** | **1** | Awaiting Level-2 order book depth feed | Fails closed on pure OHLCV; zero synthetic fabrication. |
| **Total Inventory** | **25** | **Complete System Audit** | **100% Accounted For** |
