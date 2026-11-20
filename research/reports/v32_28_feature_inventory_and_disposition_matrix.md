# BTCognitive — Comprehensive Feature Inventory & Architectural Disposition Matrix (V32.28)

**Date:** 2026-10-25  
**Version:** V32.28  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed)  
**Scope:** Systematic classification of all modules, engines, models, registries, and routes across BTCognitive into strict lifecycle dispositions.

---

## 1. Architectural Disposition Categories

1. **`CORE_KEEP`:** Essential component on the primary decision path:  
   $$\text{Verified Data} \longrightarrow \text{Strategy Signal} \longrightarrow \text{Horizon-Matched Forecast} \longrightarrow \text{Trade Outcome Meta-Model} \longrightarrow \text{Cost \& Uncertainty} \longrightarrow \text{Smart Entry Gate} \longrightarrow \text{Research Alert}$$
2. **`SUPPORT_KEEP`:** Verified infrastructure, monitoring, diagnostic tooling, or shadow tracking utility. Kept active but **strictly forbidden** from generating trade execution signals on its own.
3. **`RESEARCH_ONLY`:** Experimental module isolated from runtime execution decisions. Operates offline without affecting Smart Entry.
4. **`PARK` / `DEPRECATE`:** Unvalidated or speculative component (e.g. multi-strategy genetic arena) decoupled from the primary decision path to eliminate backtest overfitting (PBO) and data-snooping risks.
5. **`REMOVE` / `REJECT`:** Proven unsafe (e.g. untrusted pickle deserialization), copyleft licensing risks (GPL), or dead code safely excised.
6. **`BLOCKED`:** Potentially valid theoretical concept whose required empirical data (e.g. Level-2 order book depth, OFI, VPIN) is absent from OHLCV candles. Fails closed without synthetic fabrication.

---

## 2. Complete Module-by-Module Inventory & Disposition Matrix

| Component / Module | Code Path(s) | Architectural Disposition | Functional Role & Call Evidence | Data & Dependencies | Failure Mode & Safeguards |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Market Data Validator** | `engine/data_verification.py` | `CORE_KEEP` | Validates candles, schema, monotonic timestamps, duplicate rejection, and freshness within $2\times$ timeframe. | Pandas, PyArrow. Consumes Coinbase hourly parquets. | Fails closed with `DATA_CONTRACT_BREACH`, `STALE_DATA`, or `UNVERIFIED_SOURCE`. |
| **Protected Ledger Vault** | `data/prospective_entry_ledger.jsonl`, `data/raw/ohlcv.parquet`, etc. | `CORE_KEEP` | Stores immutable audit ledgers and raw historical datasets with bit-identical SHA-256 checks. | File system. Zero external dependencies. | Read-only. Writing or altering protected files triggers immediate test suite failure. |
| **Strategy Signal Engine** | `engine/strategy_signal_engine.py` | `CORE_KEEP` | Evaluates deterministic strategies on completed bars (`TSMOM_DONCHIAN_24H_168H`, `RANGE_BOLLINGER_REVERSION_20H`). | NumPy, Pandas. Excludes current bar via `shift(1)`. | Causal next-open execution. Spot shorts map strictly to `CASH / SPOT_SHORT_INELIGIBLE`. |
| **Deterministic Barrier Resolver** | `engine/barrier_resolver.py` | `CORE_KEEP` | Deterministically evaluates triple-barrier excursions ($TP$, $SL$, $Timeout$). | `engine/entry_contracts.py`. | Intrabar collision resolves conservatively as `SL_FIRST`. Opening gaps executed at open. |
| **Trade-Outcome Meta-Model** | `research/experiments/run_phase4_meta_model.py` | `CORE_KEEP` (Offline) | Trains calibrated multinomial logistic regression predicting tri-state probabilities ($p_{\text{TP}}, p_{\text{SL}}, p_{\text{TO}}$). | Scikit-Learn (`PredefinedSplit`, sigmoid calibration). | When $EV_{\text{net}} \le 0$, model abstains 100% of the time, protecting capital. |
| **Execution Cost & Net Expectancy Engine** | `engine/trade_outcome_evaluator.py`, `engine/execution_cost_model.py` | `CORE_KEEP` | Evaluates closed-form net edge $EV_{\text{net}} = p_{\text{TP}}(k_{\text{tp}} - C_R) - p_{\text{SL}}(k_{\text{sl}} + C_R) + p_{\text{TO}}(\mathbb{E}[R_{\text{TO}}] - C_R)$ with bootstrap CI. | NumPy. Assumed benchmark scenarios (27 bps, 87 bps). | Fails closed with `NEGATIVE_NET_EXPECTANCY` or `STATISTICAL_UNCERTAINTY`. |
| **Smart Entry Pipeline** | `engine/smart_entry_pipeline.py` | `CORE_KEEP` | Orchestrates 7 ordered decision gates. Emits `ABSTAIN` or `ELIGIBLE_FOR_SHADOW_EVALUATION`. | Consumes all core components. | Returns machine-readable failure reason codes. Live trading strictly disabled. |
| **Research Alert Engine** | `engine/smart_entry_pipeline.py`, `api/notifications.py` | `CORE_KEEP` | Dispatches research alerts with full audit payload and mandatory disclaimer: *"Research only — no order placed; not a guarantee of profit."* | In-memory hash set, local test sinks. | Hash deduplication prevents repeated alerts during periodic polling. Zero alerts emitted unless all gates pass. |
| **Vol Risk Model (HAR-RS-DOW)** | `models/authoritative_model_registry.py`, `engine/realized_semi_variance.py` | `SUPPORT_KEEP` | Forecasts realized semivariance components (1h, 24h, 168h) under QLIKE loss. | NumPy, Scikit-Learn. | **Production Authorized for Volatility.** Strictly forbidden from directional trade signaling. |
| **Conformal Risk Envelopes** | `models/uncertainty.py`, `engine/decision_envelope.py` | `SUPPORT_KEEP` | Generates distribution-free empirical prediction bands (P10–P90) over forward horizons. | NumPy. Evaluated via Winkler score. | Does **not** represent a guaranteed price boundary or directional target. |
| **Autonomous Shadow Runner** | `engine/shadow_feed_runner.py`, `engine/prospective_shadow_collector.py` | `SUPPORT_KEEP` | Background runner ingesting hourly bars, tracking prospective candidates, and resolving barrier outcomes without orders. | File lock `data/.prospective_shadow_runner.lock`. | In-position gating prevents overlapping trade issuance. Fails closed on API outage. |
| **Longitudinal Observatory** | `engine/observatory.py`, `experiments/results/observatory.db` | `SUPPORT_KEEP` | SQLite store tracking model calibration drift, Brier degradation, and forecast health over time. | SQLite3, Python stdlib. | Read/write to isolated SQLite DB; does not touch protected parquets. |
| **Historical Analog Engine** | `api/routes_analogs.py`, `tests/test_historical_analogs.py` | `SUPPORT_KEEP` | Matches current price trajectory against historical market episodes using dynamic time warping. | NumPy. | Scenario exploration tool only; cannot bypass Smart Entry gates. |
| **Counterfactual Stress Engine** | `engine/scenario_contract_engine.py`, `engine/counterfactual_contract_engine.py` | `SUPPORT_KEEP` | Replays historical liquidity shocks, fee spikes, and flash crashes through candidate setups. | Python stdlib, Pandas. | Stress testing tool only; disconnected from live execution. |
| **Cross-Venue Divergence Radar** | `engine/cross_venue_divergence.py`, `engine/spot_exchange_comparator.py` | `SUPPORT_KEEP` | Monitors top-of-book spot spread divergence across Coinbase, Binance, Kraken, and Bitfinex. | CCXT (Public ticker endpoints). | Diagnostic radar only; does not place arbitrage trades. |
| **FastAPI Application Server** | `api/server.py`, `api/security_middleware.py` | `SUPPORT_KEEP` | Serves modular REST and WebSocket endpoints with OWASP ASVS 5.0 security headers and rate limits. | FastAPI, Starlette, Uvicorn. | Sanitized global error handler prevents stack trace leakage. Tested via `TestClient`. |
| **Trading Terminal UI** | `web/index.html`, `web/app.js`, `web/styles.css` | `SUPPORT_KEEP` | Interactive dashboard featuring TradingView-grade HTML5 canvas candlestick rendering, risk radar, and shadow ledger inspector. | Pure HTML5, CSS3, Vanilla JS. Zero npm build dependencies. | Polling limiter caps requests at 29.5 req/min (server limit: 60 req/min). |
| **Directional GBDT Classifiers** | `engine/directional_forecast_service.py`, `models/registry/research/` | `RESEARCH_ONLY` | Frozen LightGBM return-sign models (1h, 4h, 24h). Evaluated on 2026 holdout (AUC: 0.5136–0.5285). | Joblib, Scikit-Learn. | Marked `PROVENANCE_LIMITED_RESEARCH_ONLY`. Fails closed if artifact SHA-256 mismatches. Context only. |
| **Chronos-2 Foundation Forecaster** | `models/foundation/chronos_adapter.py`, `research/experiments/run_phase3_forecast_evaluation.py` | `RESEARCH_ONLY` | Pretrained 120M foundation time-series model (`amazon/chronos-2`, Apache-2.0). | PyTorch, Transformers (Optional research venv). | Predicts marginal quantiles, not first-passage stopping probabilities. Excluded from core runtime dependencies. |
| **TFT & Router Deep Learning Models** | `models/checkpoints/tft.pt`, `models/checkpoints/router.pt` | `RESEARCH_ONLY` | PyTorch Temporal Fusion Transformer and Mixture-of-Experts routing network. | PyTorch. | Offline research only. Retaining checkpoints on disk; unpromoted to runtime execution path. |
| **Hawkes Point Process** | `engine/hawkes_shadow_session.py`, `tests/test_hawkes_*.py` | `RESEARCH_ONLY` | Evaluates trade cluster arrival intensity and jump volatility feedback. | NumPy, Scikit-Learn. | Theoretical research only; disconnected from Smart Entry decision path. |
| **Strategy Arena & Genetic Tournaments** | `engine/arena_runner.py`, `engine/arena_evolution.py`, `api/routes_arena.py` | `PARK` | Multi-agent genetic strategy optimization and tournament leaderboards. | SQLite3, NumPy. | **Parked from default path.** Decoupled from Smart Entry to eliminate backtest overfitting (PBO) risks. |
| **External Pickle Models (`TabICL`)** | `AMFORGE/tabicl-gold-btc-finetuned` (`tabicl_finetuned.pkl`) | `REMOVE` / `REJECT` | External tabular model fine-tuned on CFD data. | PyTorch, Pickle. | **Rejected & Blocked.** Poses arbitrary code execution risks and suffers `NotFittedError` due to missing `_X_encoder_`. Never loaded. |
| **GPL Consensus Model** | `maverick90024/btc-usd-consensus-1d` | `REMOVE` / `REJECT` | Daily BTC-USD consensus model under GPL-3.0 copyleft license. | Python. | **Rejected.** Blocked from application integration to protect codebase licensing. |
| **Microstructure OFI / VPIN / Hawkes** | Order flow imbalance, volume toxicity, jump intensity. | `BLOCKED` | High-frequency order book microstructure features. | Requires Level-2 order book feed. | **Blocked.** OHLCV candles cannot fabricate these features. Fails closed with `FEATURE_UNAVAILABLE`. |

---

## 3. Core Path vs. Auxiliary Decoupling Verification

All auxiliary, parked, and research-only modules are strictly decoupled from the core Smart Entry decision engine:
- `SmartEntryPipeline` requires only: `DataContractValidator`, `StrategySignalEngine`, `DeterministicBarrierResolver`, `TradeOutcomeEvaluator`, and `NotificationManager`.
- If Hawkes, Arena, TFT, Chronos, or Historical Analogs fail or are disabled, the core pipeline functions unimpeded and fails closed with explicit reason codes.
- Zero live execution paths exist; all order submission calls throw `RuntimeError("Live execution permanently disabled")`.
