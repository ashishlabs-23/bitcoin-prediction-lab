# V37.1 Application Runtime Report

**Scope:** Runtime inspection only. No production source, tests, configuration, datasets, or existing reports were edited. No test suite was run.

## Result

**Backend startup: NOT VERIFIED; intentionally not started.** The documented startup path can read protected OHLCV observations during module import and again during application startup. A guarded import confirmed the first such read attempt, and aborted before opening the file or binding a port. The normal documented command was therefore not run.

**Frontend/dashboard: NOT VERIFIED.** The integrated browser tooling opened an `about:blank` page, but the backend was not listening; a loopback-only navigation to the dashboard timed out. No dashboard render or browser-originated API request reached the backend.

**Market data: No observations were opened or served.** Metadata and source behavior were inspected only. No synthetic fixtures were needed or installed because the application could not safely reach its routes.

## Baseline and preservation

- Branch: `milestone/v35.3-critical-remediation`
- HEAD: `25d483f4c3646661b57311de9d0b53d2be881adb`
- Initial `git status --short`: 473 entries, including extensive pre-existing modifications and untracked reports. These were preserved.
- No listener was present on ports 8000, 5173, or 4173 during the initial check. No process was stopped.
- `V37_1_APPLICATION_RUNTIME_REPORT.md` did not exist before this report.

## Commands and steps

1. Read the documented startup instructions in `README.md` (line 387):
   ```powershell
   python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
   ```
   The documented page is `http://127.0.0.1:8000` (README line 389). No separate frontend start script is documented; `package.json` provides `check`, `test`, and `build`, but no `start` script.
2. Set `BTC_DATA_MODE=offline_research` in the attempted Python process and installed a process-local `pandas.read_parquet` guard that refused access to any file named `ohlcv.parquet`. This was a safety probe, not the documented Uvicorn command.
3. Imported `api.server` under that guard. Import failed before a server was created:
   ```text
   Loaded 6945 persistent forecast records from SQLite
   ...
   api/routes_tournament.py -> research.v12_strategy_tournament_engine.py
   V12StrategyTournamentEngine.__init__ -> _load_and_prepare_data
   pd.read_parquet(self.data_path)
   RuntimeError: PROTECTED_READ_BLOCKED: refusing to read data/raw/ohlcv.parquet
   ```
   The attempted Parquet read was stopped before the original reader ran. The log also shows import-time SQLite initialization/read; no database write was observed or intentionally requested.
4. Confirmed afterward that no app listener remained on ports 8000, 5173, or 4173.
5. Opened an integrated browser page at `about:blank`. Before navigation, installed a Playwright route that aborted every non-loopback origin; then attempted:
   ```js
   page.goto("http://127.0.0.1:8000/", {
     waitUntil: "domcontentloaded",
     timeout: 5000
   })
   ```
   Result: `TimeoutError` after 5 seconds; page remained `about:blank`. No external origins were recorded by the route (`blockedExternalOrigins: []`).

## Startup safety and application routes

The source explains why an unmodified launch is unsafe for this request:

- `research/v12_strategy_tournament_engine.py` eagerly constructs a tournament engine during import; its loader reads its configured Parquet input. The guarded import reached `data/raw/ohlcv.parquet` and was stopped.
- `api/server.py` lifespan also runs `evaluate_runtime_readiness(force_refresh=True)` and `feature_cache.initialize()`. In `validation/startup_gate.py`, readiness reads `data/raw/ohlcv.parquet`; in `engine/feature_cache.py`, initialization reads processed features and may read the same raw OHLCV file.
- Thus, setting offline mode alone does **not** make the documented startup safe from protected-file reads. The guard prevented an observation read, but the application did not start.

Static source inspection found these relevant routes and behaviors:

- `api/server.py` registers `api.market_monitor_routes` before other routers and mounts `web/` at `/`.
- Market-monitor routes include `/api/health`, `/api/readiness`, `/api/dashboard` and `/api/market/dashboard`, plus `/api/market/candles` and `/market/candles`.
- Legacy `api.routes_market` also provides `/candles`. Its hourly path reads the in-memory `feature_cache`; its 15-minute branch returns unavailable in offline mode rather than consulting the local cache.
- In contrast, `api.market_monitor_routes.market_candles` has an offline 15-minute branch that loads the Coinbase adapter’s local cache and labels returned rows `LOCAL_HISTORICAL_CACHE` / `HISTORICAL_SNAPSHOT`; absent cache, it returns `DATA_UNAVAILABLE`.
- The market-monitor hourly candle branch checks the separate Bitstamp cache at `data/providers/bitstamp/BTCUSD_1h.parquet`. If present, it validates hourly/closed-candle semantics and reports `LOCAL_BITSTAMP_CACHE`, freshness (`FRESH`/`STALE` or unavailable), latest completed candle time, observed age, and retrieval time from provenance. Otherwise, downstream dashboard retrieval can require providers.
- `/api/dashboard` calls the market-dashboard provider path. `engine/data_mode.is_external_network_permitted()` returns false in the current lanes, and `api.market_drivers._get_json` calls `assert_no_external_network` before making an HTTP request. The Coinbase 15m fetcher and Bitstamp service also assert before provider access.

These are source findings only; none of those HTTP routes were reached in this run.

## Cache metadata only

No Parquet rows, holdout values, or provenance-file contents were opened.

| File | Metadata observed | Runtime status |
|---|---|---|
| `data/raw/coinbase_15m.parquet` | Present; 830,946 bytes; modified 2026-10-26 17:46:34 UTC | Local cache availability was not tested through the API. |
| `data/raw/coinbase_15m_manifest.json` | Present; 774 bytes; modified 2026-10-26 17:46:34 UTC | Contents not read. |
| `data/providers/bitstamp/BTCUSD_1h.parquet` | Present; 56,271 bytes; modified 2026-11-03 15:08:36 UTC | Cache observations were not read or validated. |
| `data/providers/bitstamp/provenance.json` | Present; 860 bytes; modified 2026-11-03 15:08:36 UTC | Contents not read. |
| `data/raw/ohlcv.parquet` | Present in the metadata listing | Protected observations were not opened; the guarded import attempt was blocked. |

Consequently, BTC-USD candle counts, actual source/as-of timestamps, freshness, and unavailable behavior remain **unverified at runtime**. The report does not treat the cache-file presence or source-level route contract as proof of valid/fresh candle data.

## Frontend, network, and execution boundaries

- `web/index.html` references Google Fonts (`fonts.googleapis.com`, `fonts.gstatic.com`) and scripts from `cdnjs.cloudflare.com` and `unpkg.com` (Three.js, Lightweight Charts, React, ReactDOM). Those requests were not allowed or made. Since the browser never received the local dashboard document, no claim is made about whether its UI can render offline.
- `package.json` has no frontend `start` script or declared local React/browser dependency. The README uses the backend-served static app.
- `web/app.js` defaults its hash route to `#/terminal`; its effects poll health and load AI/market data. Those actual frontend requests could not be observed because the app page did not load.
- `engine/data_mode.py` declares external network disabled for the current lanes. However, **no market endpoint ran**, so no attempted provider path was observed being blocked at runtime. The loopback-only browser policy was installed, but because navigation did not complete, it recorded no external request.
- Execution-disable behavior is source-confirmed, not runtime-confirmed: monitor health declares `live_trading_enabled`, `order_submission_enabled`, and `trading_enabled` false with `execution_status="DISABLED_ANALYSIS_ONLY"`; server lifespan sets `live_engine.is_running = False`. No health response was obtained.

## Failures and limitations

1. The backend import-time tournament initialization attempted a protected OHLCV read; the guard stopped it before data access. The server never bound to loopback.
2. The documented unguarded Uvicorn command was intentionally not run because both import and lifespan have protected-file read paths.
3. Browser infrastructure was available, but loopback navigation timed out without a backend; no dashboard, browser E2E, or frontend-to-backend request was verified.
4. Offline route behavior, cache validation/freshness, provider-call blocking at an endpoint, and execution flags were not dynamically verified. No synthetic fixture or test was run.

## Governed decisions

- **Research experiment:** `INCONCLUSIVE` — this was an application runtime check, not an experiment.
- **Prospective evidence:** `NOT_STARTED`
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`
- **Live trading:** `DISABLED`
