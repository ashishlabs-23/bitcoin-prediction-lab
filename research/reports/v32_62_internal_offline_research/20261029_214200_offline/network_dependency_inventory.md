# Runtime Network Dependency Inventory (V32.62)

**Audit Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Audit Directory:** `research/reports/v32_62_internal_offline_research/20261029_214200_offline/`  
**Operational Scope:** Internal Offline Research Mode on Loopback (`127.0.0.1`).  
**Classification Categories:**
- `LOCAL_COMPUTATION`: Computes entirely in-memory using Python/JavaScript stdlib or math/ML libraries; zero data or network dependencies.
- `HISTORICAL_LOCAL_DATA`: Operates on static, read-only local disk files (`ohlcv.parquet`, model joblib artifacts, JSON ledgers).
- `CACHED_RESULT`: Operates on in-memory caches populated at startup.
- `EXTERNAL_SERVICE_DEPENDENT`: Requires outbound internet network calls to third-party exchange APIs (Coinbase, Binance, Kraken, Bybit, Bitstamp).
- `CURRENTLY_UNAVAILABLE`: External feed is disabled or unconfigured; fails closed with explicit empty/null response.

---

## 1. Comprehensive Component Dependency Matrix

| Subsystem / Module | Specific File & Function | Network Dependency | Classification | Offline Behavior on `127.0.0.1` | Fails Closed? |
| :--- | :--- | :--- | :---: | :--- | :---: |
| **FastAPI Core Server** | `api/server.py` (`uvicorn.run`) | Bound to `127.0.0.1:8000` | `LOCAL_COMPUTATION` | Serves API routes and static UI locally | N/A |
| **Scientific Startup Gate** | `validation/startup_gate.py` (`verify_scientific_contract`) | Reads `models/har_rs_dow_pipeline.joblib` | `HISTORICAL_LOCAL_DATA` | Computes artifact SHA-256 hash locally | **YES** |
| **Authoritative Model Registry** | `models/authoritative_model_registry.py` | In-memory dataclasses | `LOCAL_COMPUTATION` | Returns `OFFLINE_RESEARCH_ONLY` status | **YES** |
| **Macro State & Regime Engine** | `api/routes_terminal.py` (`get_macro_regime`) | Reads `data/raw/ohlcv.parquet` | `HISTORICAL_LOCAL_DATA` | Evaluates regime on 42,237 historical bars | **YES** |
| **Conformal Risk Envelope** | `api/routes_terminal.py` (`predict_risk_envelope`) | Local joblib model pipeline | `HISTORICAL_LOCAL_DATA` | Computes $[L_t, U_t]$ intervals locally | **YES** |
| **Calibration Health Observatory** | `engine/observatory.py` | In-memory singleton | `CACHED_RESULT` | Evaluates rolling coverage on local memory | **YES** |
| **Strategy Tournament Catalogue** | `api/routes_tournament.py` (`get_catalogue`) | In-memory registry (28 strategies) | `LOCAL_COMPUTATION` | Lists strategy descriptors and contracts | **YES** |
| **Analyse Setup Evaluation** | `api/routes_tournament.py` (`analyse_setup`) | Reads `data/raw/ohlcv.parquet` | `HISTORICAL_LOCAL_DATA` | Screens eligible strategies on historical bars | **YES** |
| **Market Memory & Journal** | `backtest/market_memory.py` | In-memory / JSON store | `LOCAL_COMPUTATION` | Records backtest stats locally | **YES** |
| **Multi-Exchange Comparator** | `api/routes_market.py` (`get_market_comparator`) | Outbound REST to Coinbase/Kraken/Bitstamp | `EXTERNAL_SERVICE_DEPENDENT` | Returns `HISTORICAL_BENCHMARK_ONLY` / fails closed | **YES** |
| **15m Candle Ingestion** | `engine/coinbase_15m_adapter.py` | Outbound REST to Coinbase API | `EXTERNAL_SERVICE_DEPENDENT` | Fails closed with `DATA_UNAVAILABLE` / empty list | **YES** |
| **Multi-Exchange Fallback Chain** | `api/http_client.py` (`fetch_binance_klines_async`) | Outbound REST to Binance/Coinbase/Kraken | `EXTERNAL_SERVICE_DEPENDENT` | Fails closed with empty list `[]`; zero fallback quote | **YES** |
| **Provider Adapters (Bitstamp/CoinGecko)**| `engine/market_data_adapters/` | Outbound REST to Bitstamp/CoinGecko | `CURRENTLY_UNAVAILABLE` | Disabled by flag (`BTC_ENABLE_PROVIDER_ADAPTER=false`); fails closed | **YES** |
| **TradingView Chart Widget** | `web/app.js` (Lightweight Charts 4.1.3) | Client-side UMD bundle | `LOCAL_COMPUTATION` | Renders candlesticks in browser locally | **YES** |
| **Technical Indicators (EMA, RSI, ATR)**| `web/app.js` & `engine/indicators.py` | In-memory mathematical transforms | `LOCAL_COMPUTATION` | Computes indicators over rendered bars | **YES** |
| **Simulated Trade Monitoring** | `engine/smart_entry_engine.py` | In-memory position tracker | `LOCAL_COMPUTATION` | Evaluates trade rules against bar series | **YES** |
| **Prospective Ledgers** | `data/prospective_entry_ledger*.jsonl` | Append-only disk files | `HISTORICAL_LOCAL_DATA` | Read-only inspection; zero mutations | **YES** |

---

## 2. External Network Call Elimination & Sandboxing

1. **Host Binding:** Uvicorn is strictly bound to `127.0.0.1` (`--host 127.0.0.1`). Public external interfaces (`0.0.0.0`) are not used in offline research mode.
2. **Fail-Closed External Calls:** All functions in `api/http_client.py` and `engine/coinbase_15m_adapter.py` catch network connection failures and timeouts cleanly, returning explicit `DATA_UNAVAILABLE` or empty collections.
3. **Zero Quote Fabrication:** The legacy $80,000 synthetic fallback quote in `api/routes_tournament.py` was eliminated in V32.58. When market data is absent, the endpoint returns HTTP 400 with `status: "DATA_UNAVAILABLE"`.
4. **Zero Live Order Execution:** No code exists to connect to private broker APIs, execute orders, or manage custody. `trading_enabled = False` is enforced at the architecture level.

