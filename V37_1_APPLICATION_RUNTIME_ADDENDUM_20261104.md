# V37.1 Application Runtime — Dated Follow-up Addendum

**Date:** 2026-11-04 (UTC+05:30)  
**Related report:** `V37_1_APPLICATION_RUNTIME_REPORT.md`  
**Scope:** One synthetic-isolated actual-app startup and local route check. This addendum supplements, and does not replace, the original report.

## Outcome

**The FastAPI application imported and completed its lifespan under `TestClient` with offline research mode enabled.** No Uvicorn listener or browser session was used. The runtime returned the root HTML, static assets, health, both candle intervals, and the dashboard-unavailable response.

All pandas Parquet reads were replaced with deterministic in-memory synthetic frames; direct repo Parquet/SQLite file access was guarded; all SQLite connections were redirected to one unique session-only database; repo writes were blocked; application file logging was redirected outside the repo; subprocess creation was denied; and DNS/socket connections were limited to loopback. No protected observations were opened, no repo write was recorded, and no external network attempt or denial occurred.

This is a **synthetic runtime compatibility check**, not evidence about real BTC-USD candles, cache freshness, production readiness, or browser E2E behavior.

## Isolation and exact procedure

Executed inline with the project interpreter; no harness or fixture file was created:

```powershell
@' ... Python runtime harness ... '@ | .\.venv_win\Scripts\python.exe -
```

The process set both `BTC_DATA_MODE=offline_research` and `DATA_MODE=offline_research`, disabled bytecode writes, then:

1. Replaced `pandas.read_parquet` before importing `api.server`. It returned synthetic hourly OHLCV (800 rows), a synthetic Coinbase-like 15-minute cache (96 rows), a synthetic Bitstamp-like hourly cache (72 rows), or the synthetic hourly frame according to requested path. Cache manifest and provenance JSON reads were also supplied from in-memory synthetic values.
2. Blocked direct reads of repo Parquet and SQLite files and blocked writes/directories under the repo. No such block was triggered. Redirected any app `FileHandler` targeting the repo to a unique session log.
3. Replaced `sqlite3.connect` and `sqlite3.dbapi2.connect` so all connections (including calls naming `market_memory.db` and `observatory.db`) targeted one unique database under the session `files` directory. Three connections were redirected.
4. Denied subprocess creation before execution. This prevented the startup full-freeze verifier subprocess from reading repo files; the authoritative runtime readiness consequently remained blocked. The separate scientific contract/model-artifact check completed and logged `PASS`.
5. Guarded DNS and socket `connect`/`connect_ex` to allow loopback only, then imported the actual `api.server` app and ran its lifespan and requests with FastAPI `TestClient`.
6. Replaced `get_offline_historical_candles` with an empty synthetic history solely for the `/api/dashboard` unavailable-path check. This was an in-memory patch, not a source edit.

The app's eager tournament-engine import reached its Parquet loader, which received only the injected synthetic OHLCV. Its indicator/4-hour preparation therefore operated on synthetic input. No tournament selection/evaluation route was called, and no real market inputs were used.

## Runtime evidence

FastAPI lifespan started and shut down cleanly. The startup log included:

```text
PASS: Scientific contract gate fully verified [...]
WARNING Authoritative research gate BLOCKED [FULL_FREEZE_VERIFIER_DID_NOT_RUN]
INFO Initializing BTCognitive market data client and feature cache...
INFO FeatureCache initialized from parquet with 800 rows.
INFO Started background research-condition alert evaluator (interval=60s).
...
INFO Shutdown complete.
```

| Request via TestClient | Result |
|---|---|
| `GET /` | HTTP 200; HTML, 1,803 bytes |
| `GET /styles.css` | HTTP 200; CSS, 113,017 bytes |
| `GET /app.js?v=35.4.1` | HTTP 200; JavaScript, 1,015,105 bytes |
| `GET /analysis_contract.js` | HTTP 200; JavaScript, 4,022 bytes |
| `GET /api/health` | HTTP 200; `status=ok`, `mode=MARKET_MONITOR_ONLY`, `research_status=BLOCKED_AUDIT_FAILURE`, `live_trading_enabled=false`, `order_submission_enabled=false`, `trading_enabled=false`, `execution_status=DISABLED_ANALYSIS_ONLY` |
| `GET /api/market/candles?symbol=BTC-USD&interval=15m&limit=5` | HTTP 200; `HISTORICAL_SNAPSHOT`, 5 synthetic rows, `LOCAL_HISTORICAL_CACHE`, `retrieved_at=2026-11-04T11:15:00Z`, `degraded=true` |
| `GET /api/market/candles?symbol=BTC-USD&interval=1h&limit=5` | HTTP 200; `FRESH`, 5 synthetic rows, `LOCAL_BITSTAMP_CACHE`, latest completed time `2026-11-04T10:00:00+00:00`, synthetic retrieval timestamp |
| `GET /api/dashboard` | HTTP 200; `status=DATA_UNAVAILABLE`, `market.status=DATA_UNAVAILABLE`, `price_usd=null`, zero candles, reason `Validated local historical candles are unavailable.` |

The returned candle source, freshness, timestamps, prices, and counts above describe only the supplied synthetic frames. The dashboard-unavailable response describes only the explicit empty synthetic offline-history case.

## Network, persistence, browser, and limitations

- Seven `pandas.read_parquet` calls were intercepted and served synthetic frames: four `ohlcv.parquet`, one `features.parquet`, one `coinbase_15m.parquet`, and one `BTCUSD_1h.parquet`.
- Direct protected-file read attempts blocked: **0**. Repo write attempts blocked: **0**.
- SQLite redirects: **3**. The temporary DB was outside the repository. Any SQLite activity during this runtime was confined to that DB.
- Subprocesses denied before process creation: **2**. This intentionally prevented the full-freeze verifier, leaving readiness and research authorization blocked; the 200 health response is not a readiness pass.
- External DNS/socket denials: **0**; external-network guard assertions: **0**. No provider request was attempted. Socket policy allowed loopback only; one loopback connect was observed.
- No browser was used in this follow-up. Static assets were served successfully through `TestClient`, but browser rendering, CDN-dependent script behavior, and browser-originated API calls remain unverified. No external origin was contacted.
- The temporary SQLite DB and redirected log were removed after the process exited. The app lifespan closed; no Uvicorn server or background worker remains.
- No repository source, test, configuration, dataset, or prior report was changed. No tests were run.

## Updated release decisions

- **Research experiment:** `INCONCLUSIVE` — synthetic runtime behavior only.
- **Prospective evidence:** `NOT_STARTED`
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`; runtime readiness was `BLOCKED_AUDIT_FAILURE`.
- **Live trading:** `DISABLED`
