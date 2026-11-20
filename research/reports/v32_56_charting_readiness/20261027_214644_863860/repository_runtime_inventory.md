# V32.56 product and runtime inventory

## Confirmed runtime

- Backend: FastAPI application in `api/server.py`, with static frontend mounting and modular routers.
- Client: a compiled/bundled `web/app.js` delivered from `web/index.html`; no SPA framework package dependency was found in `package.json`.
- Chart: TradingView Lightweight Charts loaded from unpkg in `web/index.html`; this is a dependency, not a market-data entitlement.
- Market/forecast routes: `api/market_monitor_routes.py` provides `/api/dashboard`, `/api/market-drivers`, `/api/forecast/latest`, `/prediction/latest`, and `/api/readiness`. Market values are retrieved through server-side market-driver/provider clients.
- Current supported public-market contract is BTC/USD-centric; `api/market_monitor_routes.py` rejects unsupported requested symbol/interval combinations. Broad symbol/timeframe support is not established.
- Indicators and forecast state are rendered in `web/app.js`; the UI checks origin against the latest closed chart candle. On an unavailable/malformed/timeout response it clears forecast series and retains the price chart.
- Deployment artifacts exist: Dockerfile, docker-compose.yml, render.yaml, fly.toml. CI is limited to `.github/workflows/market-monitor.yml`, covering two market test modules.
- Auth: `api/security_auth.py` defines public/default role and configured API-key/Bearer roles; no exchange account linking was found.

## Forecast contract and marker behavior

`/api/forecast/latest` delegates to `engine.forecast_engine_15m.generate_forecast_contract`. The frontend only creates a marker when the forecast origin equals the latest closed candle for the active interval; otherwise it must not anchor a marker. The source code separately renders forecast state/panel content. A live browser observation was not claimed in this audit because public data rights are blocked and no licensed staging provider was identified. Browser evidence therefore remains pending.

## Execution boundary

No broker/order placement route or exchange authentication integration was found. The code does expose manual journal/user-position and smart-entry simulation routes, which persist user-supplied/simulated lifecycle events. They are not a public chart-MVP dependency and must remain segregated. `OFFLINE_RESEARCH_ONLY` and `NO_GO_NO_VALIDATED_EDGE` gate model authorization/recommendation and live-capital status; chart rendering is not itself conditional on production model authorization.

## Confirmed P0 defect

`api/routes_user_positions.py` uses a hard-coded 80000.0 quote after a provider failure. That fallback is incompatible with the no-fabricated-market-data requirement. It is outside broker execution, but it is a confirmed defect for any displayed position/monitor quote. Do not expose that path publicly until it returns an explicit unavailable state.

## Smallest ranked changes — not implemented by this audit

1. Replace the hard-coded position-monitor quote fallback with `UNAVAILABLE`; test provider failure returns no fabricated price.
2. Add a rights gate to public market-data routes that blocks third-party data display until a provider license record is affirmative; test default BLOCKED and an explicit licensed-provider configuration.
3. Add chart-contract browser tests using QA fixtures: OK/GAP/STALE/PARTIAL/UNAVAILABLE, marker alignment/fallback panel, source/cutoff/model version, and cache-key isolation.
4. Keep simulator/journal routes off the chart-MVP navigation; test no public chart workflow reaches Enter/Continue/Exit.
5. Expand the existing CI workflow only after those focused tests exist; do not use aggregate coverage as the gate.
