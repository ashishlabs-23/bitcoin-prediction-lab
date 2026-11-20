# V37.2 Frontend and Browser QA Report

**Assessment date:** 2026-11-04 (UTC+05:30)  
**Branch:** `milestone/v35.3-critical-remediation`  
**HEAD at inspection:** `25d483f4c3646661b57311de9d0b53d2be881adb`

## Scope and preservation

This task inspected the frontend route mapping and test coverage, ran focused frontend checks, and attempted browser validation using a loopback-only synthetic fixture. It made **no production, test, configuration, data, manifest, or prior-report edits**. The only file created by this task is this report.

The worktree was already substantially dirty. At inspection, frontend paths were modified (`web/app.js`, `web/index.html`, `web/styles.css`, and `web_src/api_client.js`), and two frontend modules were untracked (`web_src/manual_trade_journal_view.js` and `web_src/smart_entry_simulator_view.js`). The existing `web/app.js` diff was especially large. These changes were preserved; no cleanup, formatting, build, staging, or destructive Git operation was performed.

## UI mapping reviewed

`web/index.html` mounts the app into `#root` and loads `analysis_contract.js` and `app.js`. The app uses hash routing; its inspected branches include `/landing`, `/how-it-works`, `/paper-trading`, `/position-monitor`, `/journal`, `/smart-entry`, `/research`, `/arena`, and `/forecast`, with the terminal as the default view. `tests_frontend.js` checks navigation and home-card markers, forecast UI contracts, journal and Smart Entry preservation, unavailable-state contracts, API/WebSocket resolution, request deduplication/caching, rate-limit backoff, and the steady-state request budget.

The HTML also references third-party Google Fonts, Three.js, Lightweight Charts, React, and ReactDOM from external origins. React is required by the app's top-level initialization; chart rendering is conditional on Lightweight Charts, and the 3D background is guarded when Three.js is unavailable.

## Focused checks

| Command | Result |
|---|---|
| `npm test` | **PASS** — ended with `All Frontend Unit Tests Passed Successfully!`; covered the frontend assertions described above. The script does not report a numeric test count. |
| `npm run check` | **PASS** — `node --check` completed for `web/app.js`, `web_src/api_client.js`, `web_src/websocket.js`, and `web_src/formatters.js`. |
| `git diff --check -- web\app.js web\index.html web\styles.css web_src` | **PASS** — no whitespace errors reported. Git emitted existing LF-to-CRLF working-copy warnings for `web/app.js` and `web_src/api_client.js`. |

No backend test suite was run. `npm run build` was intentionally not run because the build script may rewrite generated/production frontend files in this dirty worktree.

## Isolated fixture and browser attempt

An inline, temporary Python HTTP fixture was started on `127.0.0.1:8765`. It served the checked-out frontend assets and a generic synthetic `DATA_UNAVAILABLE` JSON response; non-GET requests were denied. Manual loopback checks returned HTTP 200 for `/` (1,803-byte HTML) and `/api/health` (the controlled fixture payload). No backend application, provider, market feed, or external data source was started or queried. The fixture process was stopped after the attempt.

The integrated browser was configured to block non-loopback HTTP requests and external WebSocket connections. **Browser E2E is partial/unverified:**

- Navigation to the loopback fixture did not complete in the browser (`page.goto` timed out; the page remained `about:blank`, and the browser reported a failed/aborted local request). The fixture's request log contained only the manual local checks, so the browser did not reach the fixture.
- A file-URL fallback loaded the document title but did not complete parsing: root/body were unavailable and absolute asset references resolved to `file:///C:/styles.css`, `file:///C:/analysis_contract.js`, and `file:///C:/app.js`, which failed with 403/aborted-resource events.
- The HTML's external scripts therefore did not produce an initialized React app. No rendered screens, navigation interactions, API-backed UI states, or browser screenshots could be verified. No successful external-origin response was observed; the browser tooling did not provide reliable intercepted-origin telemetry, so this is not a claim that every external request was captured.

The source-level tests and syntax checks pass, but they do not substitute for a rendered browser run. Browser validation should be repeated when a browser session can access the isolated loopback fixture while retaining an explicit external-origin block.

## Governed decisions

- **Research experiment:** `INCONCLUSIVE` — frontend checks only; browser rendering was not verified.
- **Prospective evidence:** `NOT_STARTED`
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`
- **Live trading:** `DISABLED`
