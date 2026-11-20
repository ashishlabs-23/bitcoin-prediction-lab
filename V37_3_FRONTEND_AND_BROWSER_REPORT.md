# V37.3 Frontend and Browser Report

**Assessment date:** 2026-11-04 (UTC+05:30)  
**Branch:** `milestone/v35.3-critical-remediation`  
**HEAD at inspection:** `25d483f4c3646661b57311de9d0b53d2be881adb`

## Scope and preservation

This workstream was limited to `web/app.js`, directly related `web/styles.css`, and this report. Existing navigation, hash routes, and feature families were retained; this was corrective UI work, not feature removal. `web/index.html` was already modified at baseline and was not edited here. The pre-existing untracked `web/analysis_contract.js` was also left untouched.

Changes made in this workstream:

- Fixed two render-time `ReferenceError`s found in Chrome: the chart component now receives `historyFreshness` from its feed hook, and the overview feed banner derives health from the existing verified-live market condition.
- Removed reviewed hard-coded BTC-price and portfolio fallbacks from chart/forecast, position-monitor, journal, and paper-trading views. Missing quote, portfolio, performance, latency, and feed-age fields now display unavailable states instead of fabricated prices, zero performance, or “ready” status.
- Kept configured paper-trading cost assumptions distinct from observed spread/fill data.
- Added responsive navbar wrapping and narrower paper-trading/journal grids. These final responsive changes were **not browser-retested** before the task stop.
- Preserved actionable `console.warn`/`console.error` diagnostics and existing `BTCognitiveTiming` information logs. No `console.log` or `console.debug` statements were removed from application code.

## Browser and network setup

The same-machine runner was available: local Google Chrome at `C:\Program Files\Google\Chrome\Application\chrome.exe`, driven by the installed Python Playwright package. React 18, ReactDOM 18, Three.js r134, and Lightweight Charts 4.1.3 were absent locally, so the following no-save test-only install was used; no dependency manifest or lockfile was changed:

```powershell
npm install --no-save --package-lock=false --ignore-scripts react@18 react-dom@18 three@0.134.0 lightweight-charts@4.1.3
```

The browser used a temporary loopback-only static harness. Its in-memory HTML response mapped the checked-in CDN script URLs to those local test packages; the checked-in `web/index.html` was not rewritten. A local API fixture returned HTTP 503 with `DATA_UNAVAILABLE` and `data: null` for every API request. It supplied **no market values or model observations** and did not start the FastAPI application. Browser HTTP routing aborted every non-local origin. A WebSocket guard rejected non-local sockets; no external WebSocket attempt was observed. Two requests to `https://fonts.googleapis.com/...` were blocked.

This is a local rendered-UI test, **not** a production-dependency or live-backend integration test. The loopback fixture's `/ws` endpoint was unsupported and returned 404.

## Earlier browser evidence (superseded by final smoke below)

The last completed Chrome run occurred after the two render-time fixes, but **before** the subsequent unavailable-value and final responsive CSS edits. Therefore these observations do not verify the final worktree:

- `GET /#/terminal`: HTTP 200; React root had one rendered child; body text was 5,714 characters.
- All ten existing routes rendered one root child and non-empty screen content: `/terminal`, `/landing`, `/how-it-works`, `/paper-trading`, `/position-monitor`, `/journal`, `/smart-entry`, `/research`, `/arena`, `/forecast`.
- The grouped “More” menu exposed How It Works, Overview, AI Forecasts & Risk, Paper Trading, Position Copilot, and Settings. Clicking How It Works changed the hash to `#/how-it-works`.
- The unavailable fixture produced unavailable/stale/delayed UI text and the visible `LIVE TRADING DISABLED` label. The fixture handled 70 local API requests, all with unavailable responses. No API write/execute control was activated.
- The Lightweight Charts global loaded, but the tested default Smart Entry screen had no identified chart container; its single canvas was the Three.js background. Chart-screen rendering and chart controls remain unverified.
- No uncaught page errors were recorded in that run. Console output included expected blocked-font and fixture-503 diagnostics plus the expected unsupported loopback WebSocket 404.
- At viewport 390×844, terminal, overview, How It Works, position monitor, Smart Entry, research, arena, and forecast had no measured document overflow. Paper Trading and Journal still measured body widths of 444 and 452 pixels. A final CSS grid correction was made afterward, but was not rechecked.
- The live-trading-disabled label was present; the queried screen had zero `button:disabled` elements. Disabled/guarded controls were not exhaustively interacted with.

Two screenshots were captured in memory by the local runner (not persisted as image files because this workstream's owned-file scope excludes screenshot assets):

| Capture | Viewport | PNG bytes | SHA-256 |
|---|---:|---:|---|
| Terminal dashboard | 1440×1000 | 380,051 | `dc22a5a0df0b0c8c17744fd6ee7f52c8b79c98fce4fece039ae1519952564265` |
| Mobile screen | 390×844 | 310,184 | `108fc2f5b631cd57c8b5d6550130b835bb2ce5dea325ca909a0587f9fe85713e` |

## Tests and limitations

Before the source corrections in this workstream:

| Command | Result |
|---|---|
| `npm test` | Passed; printed `All Frontend Unit Tests Passed Successfully!` (the runner reports no numeric test count). |
| `npm run check` | Passed; `node --check` completed for `web/app.js`, `web_src/api_client.js`, `web_src/websocket.js`, and `web_src/formatters.js`. |

This earlier run predates final edits; use the final acceptance results below. The real FastAPI startup/API lifecycle, real market freshness, real candle rendering, and disabled-control interaction are not verified by the fixture.

## Final bounded browser smoke (after source edits)

The final smoke used same-machine Chrome and local Playwright after current frontend and CSS changes. No app routes, navigation, or features were changed for this follow-up.

- `GET /#/terminal`: HTTP 200; one React root child, non-empty rendered dashboard, and visible `LIVE TRADING DISABLED`.
- All ten existing routes rendered one root child with non-empty content: `/terminal`, `/landing`, `/how-it-works`, `/paper-trading`, `/position-monitor`, `/journal`, `/smart-entry`, `/research`, `/arena`, and `/forecast`.
- The grouped “More” links (How It Works, Overview, AI Forecasts & Risk, Paper Trading, Position Copilot, Settings) were visible; selecting How It Works reached `#/how-it-works`.
- The local fixture provided only `DATA_UNAVAILABLE` / HTTP 503 responses with no market prices or model observations. The paper portfolio's explicit unavailable state rendered. It handled 94 local API requests, with zero non-GET/write requests.
- At viewport 390×844, document width remained 390 on Terminal, Paper Trading, and Journal. The initial Paper Trading check measured body and `#root` at 419px; a subsequent CSS-only fix was applied and the final bounded check below confirms those widths at 390px without overflowing descendants.
- Lightweight Charts loaded and `#btc-lwc-chart` mounted on Terminal. No candles were supplied, so real-data chart rendering, freshness, and chart interactions remain unverified.
- No uncaught page errors were recorded. Expected diagnostics included blocked Google Fonts requests and API-fixture 503/unavailable warnings. No non-local WebSocket attempt was observed. The isolated fixture is not the FastAPI application; its local `/ws` route is unsupported.
- No trade, journal-write, or other write/execute control was activated. The live-trading-disabled label was visible; full control-by-control disabled-state interaction was not performed.

Final screenshots were persisted outside the repository in the session `files` directory:

| Capture | Viewport | Session file | PNG bytes | SHA-256 |
|---|---:|---|---:|---|
| Terminal dashboard | 1440×1000 | `files/v37_3_dashboard_desktop.png` | 374,808 | `a4cb6060530881e502288f85f8a1feac39def912a8e7e00f283c9d21a6704f21` |
| Paper Trading mobile (refreshed) | 390×844 | `files/v37_3_paper_trading_mobile.png` | 177,426 | `0c3e040cc0f4fb33840b8e3f917a7e2cbea905f6ab460f24fe1b01a15a55437e` |

Absolute evidence directory: `C:\Users\Ashish\.copilot\session-state\51eedde1-236e-4970-84a5-a1b2daff43ad\files`.

## Final tests and limitations

| Command | Result |
|---|---|
| `npm test` | **PASS** — printed `All Frontend Unit Tests Passed Successfully!`; the runner reports no numeric test count. |
| `npm run check` | **PASS** — `node --check` completed for `web/app.js`, `web_src/api_client.js`, `web_src/websocket.js`, and `web_src/formatters.js`. |
| `git diff --check -- web\app.js web\styles.css` | **PASS** — no whitespace errors (existing LF-to-CRLF working-copy warning for `web/app.js`). |

The real FastAPI startup/lifespan and API responses remain **unverified**. No real market feed or market values were fetched; freshness is unavailable. The 503 fixture validates fail-closed presentation only. Real-data chart rendering/interactions and full disabled-control interaction remain open.

## 2026-11-04 Mobile-width acceptance addendum

The manager's follow-up identified the Paper Trading root at 419px on a 390px viewport. A final bounded local Chrome/Playwright check confirmed the overflow came from the execution-ledger header's non-wrapping flex row (the “0 Records Logged” span extended beyond its container). A **CSS-only** mobile rule now lets that header wrap and allows its text column to shrink/wrap; no content or controls were hidden or removed.

Post-fix check at 390×844 on `#/paper-trading`: `document.documentElement.scrollWidth=390`, `document.body.scrollWidth=390`, `#root.scrollWidth=390`, `#paper-trading-page.scrollWidth=390`, and sleeve-grid width 342px. No descendant crossed the viewport edge; both gated and ungated sleeves and the unavailable-state message remained present. The unavailable-only fixture served 15 local API requests. Two Google Fonts requests were blocked; no non-local WebSocket attempt or uncaught page error occurred. Real backend/API and market-feed behavior remain unverified.

Post-fix commands:

| Command | Result |
|---|---|
| `npm test` | **PASS** — `All Frontend Unit Tests Passed Successfully!` |
| `npm run check` | **PASS** — all configured JavaScript syntax checks completed. |
| `git diff --check -- web\styles.css V37_3_FRONTEND_AND_BROWSER_REPORT.md` | **PASS** — no whitespace errors. |

## Changed files

- `web/app.js`
- `web/styles.css`
- `V37_3_FRONTEND_AND_BROWSER_REPORT.md`

`web/index.html` was already modified at baseline and was not changed by this workstream. No test, backend, data, dependency-manifest, lockfile, or other existing report files were changed by the frontend workstream.

## Governed decisions

- **Research experiment:** `INCONCLUSIVE` — frontend-only work; no model or performance evaluation.
- **Prospective evidence:** `NOT_STARTED`
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`
- **Live trading:** `DISABLED`
