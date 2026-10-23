# BTCognitive PRD Amendment V14 — Application Reliability, Live Terminal Feature Completion, Graceful Degradation & Frontend Security

**Document Version:** 14.0.0  
**Effective Date:** October 2026  
**Status:** APPROVED & GOVERNED  
**Supersedes:** PRD V13 Amendment (`docs/BTCognitive_PRD_Amendment_V13.md` preserved in historical records)  
**Parent PRD:** `docs/BTCognitive_Master_PRD.md`, `docs/BTCognitive_Master_PRD_v2_Continuation.md`  

---

## 1. Executive Summary & Core Mission

This Amendment specifies and governs **BTCognitive V14**, transitioning the application from strategy discovery to a hardened, reliable, secure, and complete institutional research terminal.

V14 addresses and eliminates the core operational, reliability, and security gaps identified after V13:
1. **Stale-Build & Asset Invalidation:** Ensures the running browser client reliably serves and refreshes the latest verified codebase via deterministic asset query hashing (`?v=14.0.0`) and strict HTTP cache-invalidation headers (`no-cache, no-store, must-revalidate`).
2. **Frontend Security & Zero Sensitive Information Exposure:** Enforces strict server-side sanitization across all public API payloads, HTML, scripts, and error handlers. Strips all server filesystem paths (e.g. `C:\Users\...`, `/home/...`), internal database connection strings, credentials, and raw stack traces. Implements OWASP ASVS 5.0 security headers including Content Security Policy (CSP), clickjacking defenses, and MIME-sniffing prevention.
3. **Graceful Degradation Under Partial Failures:** Decouples core terminal telemetry (real-time OHLCV candles, Coinbase WebSocket tick stream, and authoritative volatility risk forecasts) from secondary or optional components (e.g. scenario engine, order flow feeds). An unavailable dependent calculation restricts only that specific calculation, displaying transparent non-actionable explanations rather than breaking unrelated panels.
4. **User-Controlled Strategy Lifecycle Completion:** Strictly distinguishes the four operational states of research strategies:
   - **Selection:** User inspection of spec, parameters, and citations without chart manipulation.
   - **Preview:** User-initiated temporary preview drawing distinct dotted lines (`#38BDF8`, `#34D399`, `#F87171`) labeled `PREVIEW — NOT ENABLED: ...` and presenting an amber diagnostic ribbon with `[+ Enable Overlay]` and `[✕ Clear Preview]`. Preview does not alter authoritative monitoring or signal state.
   - **Active Overlay:** Explicit user-enabled continuous monitoring drawing solid/dashed levels and displaying the cyan `ACTIVE OVERLAY: ...` ribbon with single-overlay exclusivity.
   - **Trading Authorization:** Irrevocably locked at `live_trading = "DISABLED"` and `model_authorization = "OFFLINE_RESEARCH_ONLY"`.
5. **Truthful Telemetry & Elimination of Fabricated Data:** Purges the hardcoded mock trades array fallback (`meieTrades`) in favor of an authentic session ledger. Retains strict transparency regarding order book depth, never synthesizing mock depth from spot candles.
6. **Essential Professional Terminal Capabilities:** Integrates instant technical indicator toggles (`EMA 20/50` trend ribbons and `Bands` for nominal diffusion/conformal risk envelopes) directly in the chart command bar with O(1) visibility switching.

---

## 2. Non-Negotiable Operational & Security Boundaries

1. **Strict Non-Execution:** `live_trading` remains permanently `DISABLED`. Order routing, broker adapters, execution endpoints, and live capital deployment remain deactivated.
2. **Offline Research Authorization:** `model_authorization` remains `OFFLINE_RESEARCH_ONLY`. User interaction with strategy cards, overlays, or preview modes does not alter server-side execution authorization.
3. **Zero Information Leakage:** No server filesystem paths, internal workstation usernames, database URIs, API tokens, raw exception traces, or proprietary weights may appear in client bundles, DOM nodes, console messages, or API error bodies.
4. **Zero Telemetry Fabrication:** No fake prices, mock trades, synthetic order-book levels, or fabricated performance metrics are permitted under any circumstance.
5. **Deterministic Asset Serving:** All client HTML documents must link CSS and JavaScript bundles using the active major release query string (`?v=14.0.0`), served with strict `Cache-Control: no-cache, no-store, must-revalidate`.

---

## 3. P0 Architectural & Security Specifications

### 3.1 Deterministic Asset Versioning & Caching
* `web/index.html` specifies:
  - `<link rel="stylesheet" href="/styles.css?v=14.0.0" />`
  - `<script src="/app.js?v=14.0.0"></script>`
* `SecurityHeadersMiddleware` intercepts all requests matching `.js`, `.css`, `.html`, or `/` and injects:
  - `Cache-Control: no-cache, no-store, must-revalidate`
  - `Pragma: no-cache`
  - `Expires: 0`

### 3.2 Error Sanitization & Diagnostic Request IDs
* `sanitized_exception_handler` in `api/security_middleware.py`:
  - Intercepts both `fastapi.HTTPException` and `starlette.exceptions.HTTPException`.
  - Scans error details using regex patterns `_PATH_REGEX` and `_DB_REGEX`, redacting matches to `[REDACTED_PATH]` and `[REDACTED_URI]`.
  - Emits a standard UUIDv4 `request_id` for client telemetry while logging full internal diagnostics to `security_audit.log_event`.
  - Replaces all unhandled generic exceptions with HTTP 500 containing only `error: "INTERNAL_SERVER_ERROR"`, a safe user message, and `request_id`.

### 3.3 OWASP ASVS 5.0 Compliant Security Headers
Every HTTP response carries:
* `X-Content-Type-Options: nosniff`
* `X-Frame-Options: DENY`
* `Referrer-Policy: strict-origin-when-cross-origin`
* `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
* `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`
* `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self' ws: wss: https:; img-src 'self' data: https:; frame-ancestors 'none';`

---

## 4. Live Terminal Feature & Usability Architecture

### 4.1 Technical Indicator Toggles
* **EMA 20/50 Ribbons:** Toggled via `#toggle-ema-btn` in `ChartTopBar`. Controls series visibility on `ema20Ref` and `ema50Ref` without full chart re-renders.
* **Diffusion & Conformal Bands:** Toggled via `#toggle-bands-btn` in `ChartTopBar`. Controls series visibility on `upperBandSeriesRef` and `lowerBandSeriesRef`.

### 4.2 User-Controlled Strategy Preview & Overlay
* **Preview Mode:**
  - Invoked by clicking `👁️ Preview on Chart` on any card in `StrategyTournamentDashboard`.
  - Renders amber banner `.chart-overlay-diagnostic-banner.preview` on the chart.
  - Draws dotted lines (`LineStyle.Dotted`, width 1.5): Entry (`#38BDF8`), Take Profit (`#34D399`), and Stop Loss (`#F87171`) titled `PREVIEW — NOT ENABLED: ...`.
  - Does not modify paper position, active signal, or authoritative monitoring state.
* **Active Overlay Mode:**
  - Invoked by clicking `+ Enable Chart Overlay` in card or `[+ Enable Overlay]` on preview banner.
  - Purges preview state and prior overlays.
  - Draws solid/dashed lines (`LineStyle.Dashed` for Entry, `LineStyle.Solid` for TP/SL).
  - Renders cyan banner `.chart-overlay-diagnostic-banner` with `ACTIVE OVERLAY: ...` and `[+ Disable Overlay]` / `[✕ Clear]`.
* **Clean Removal:**
  - Clicking `[✕ Clear Preview]`, `[+ Disable Overlay]`, or `[✕ Clear]` instantly removes all price lines from Lightweight Charts and resets internal refs.

---

## 5. Traceability & Acceptance Verification Summary

| Requirement ID | Description | Implementation File | Verification Test | Status |
| :--- | :--- | :--- | :--- | :--- |
| **V14-REL-01** | Deterministic Asset Versioning | `web/index.html` | `test_v14_index_html_deterministic_asset_versioning` | **VERIFIED** |
| **V14-REL-02** | Asset Cache Invalidation Headers | `api/security_middleware.py` | `test_v14_static_assets_cache_control_headers` | **VERIFIED** |
| **V14-SEC-01** | OWASP ASVS Security Headers | `config/security.py` | `test_v14_owasp_asvs_security_headers` | **VERIFIED** |
| **V14-SEC-02** | Zero Path/DB/Stack Leakage | `api/security_middleware.py` | `test_v14_exception_sanitization_and_request_id` | **VERIFIED** |
| **V14-SEC-03** | Public API Path Redaction | `api/security_middleware.py` | `test_v14_public_api_endpoints_no_path_leakage` | **VERIFIED** |
| **V14-STRAT-01** | Strategy Preview vs Overlay | `web/app.js` | `test_v14_strategy_setup_preview_mode_invariants` | **VERIFIED** |
| **V14-STRAT-02** | Zero Level Fabrication | `api/routes_tournament.py` | `test_v14_no_fabricated_strategy_levels_when_no_setup` | **VERIFIED** |
| **V14-DATA-01** | Elimination of Mock Trades | `web/app.js` | `test_v14_paper_trades_truthful_reporting` | **VERIFIED** |
| **V14-GOV-01** | Live Trading Lock (`DISABLED`) | `config/security.py` | `test_v14_master_governance_invariants` | **VERIFIED** |
| **V14-TERM-01** | Terminal Indicator Toggles | `web/app.js`, `web/styles.css` | Browser subagent validation | **VERIFIED** |
| **V14-RESP-01** | Mobile Layout Responsiveness | `web/styles.css` | Browser subagent (390x844) | **VERIFIED** |
