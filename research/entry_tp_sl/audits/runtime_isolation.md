# Runtime Isolation Audit

**Scope:** Read-only inspection of the local-safe and production startup paths. No unsafe application was launched and no experiment, model fit, holdout read, or persistence operation was performed.

## Findings

- `api/local_safe_server.py` constructs a separate FastAPI application without importing the production app, legacy inference engine, feature cache, or market-memory module. It serves existing static files and reads authorization/provenance artifacts for status.
- `api/server.py` imports legacy runtime and security-audit modules. Its lifespan verifies contracts, initializes `feature_cache`, calls `sanitize_market_memory()`, and starts `live_engine`. The freeze-check exception is caught/logged and does not by itself prevent startup.
- `engine/inference_service.py` startup calls `make_dataset(horizon_bars=24)` and fits `AdaptiveRegimeEnsemble`; its background loop fetches external exchange data. Successful updates may persist predictions/outcomes and process candles. Shutdown sets a flag and closes the HTTP client but does not retain/await/cancel the spawned task.
- `backtest/market_memory.py` import-time initialization opens SQLite and creates tables; `sanitize_market_memory()` can rewrite CSV and delete SQLite rows. Prediction recording inserts into SQLite and syncs CSV.
- `engine/security_audit.py` has import-time log-directory/file effects. `api/notifications.py` creates a singleton that reads `.env` and loads values into process environment.
- `api/routes_terminal.py` has a lazy initializer that reads aligned research data, splits around a holdout date, predicts on the holdout and streams values to the observatory when its live/observatory endpoint is invoked. This endpoint was not invoked.
- `engine/feature_cache.py` reads local parquet during explicit initialization; absent data yields a degraded empty cache. Updates later replace in-memory data but do not clear the degraded flag.

## Recommendation

Continue to run only `api.local_safe_server:app` bound to `127.0.0.1`. Keep its endpoint allowlist explicit and avoid importing/registering production routers to obtain functionality. The current safe server is appropriate for static UI and truthful status inspection; any new read-only feed/calculator should be implemented as isolated helpers with no legacy router startup. Explicitly test import/startup for forbidden module imports and forbidden call invocations.

## Evidence inspected

- `api/local_safe_server.py`
- `api/server.py` lifespan and router registration
- `engine/inference_service.py`
- `engine/feature_cache.py`
- `backtest/market_memory.py`
- `engine/security_audit.py`
- `api/notifications.py`
- `api/routes_terminal.py`
