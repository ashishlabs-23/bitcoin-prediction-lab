# BTCognitive — Public Chart MVP Scope & Route Governance Matrix

**Document Date:** 30 October 2026  
**Product Scope:** TradingView-like BTC/USD charting, technical analysis, and market risk intelligence interface.  
**Operating Boundary:** Phase 1 / V32.66 Preparation Gate. Strictly **no live trading, no broker integration, no custody, no order execution**.  

---

## 1. Public Chart MVP Feature Boundary

| Feature Area | MVP Classification | Operational Contract & Constraints |
| :--- | :--- | :--- |
| **BTC/USD Candlestick Chart** | **IN SCOPE** | Renders 1h and 4h closed UTC candlesticks via TradingView Lightweight Charts. Strict timestamp alignment. Price basis explicitly declared (Benchmark VWAP vs Venue Spot). Zero synthetic bar fabrication. |
| **Timeframe Selectors** | **IN SCOPE** | 1H (`#tf-btn-1H`) and 4H (`#tf-btn-4H`) verified in UI. Backend adapter contract supports 15m, 1h, 4h, and 24h intervals. |
| **Technical Indicators** | **IN SCOPE** | EMA 20/50 trend ribbons (`#toggle-ema-btn`), Bollinger Bands 20,2 (`#toggle-bb-btn`), RSI-14 (`#toggle-rsi-btn`), and 24h Realized Volatility (`realized_volatility_24h_pct`). |
| **Clock & Timestamps** | **IN SCOPE** | Header shows UTC and local clocks. Candlestick hover crosshair renders exact UTC epoch timestamps. |
| **Attribution & Price Basis** | **IN SCOPE** | Prominent brand badge ("Powered by CoinGecko" or "Market Data by CoinAPI"), price basis badge (`AGGREGATED_GLOBAL_BENCHMARK` or `VENUE_SPECIFIC_SPOT_ORDERBOOK`), and freshness latency badge. |
| **Freshness & Gap Reporting** | **IN SCOPE** | Status badge indicates data status (`LIVE`, `STALE`, or `DATA_UNAVAILABLE`). Gaps in historical data are reported honestly via `ProviderContinuityReport` without interpolation. |
| **Forecast Baseline Overlay** | **CONDITIONAL** | Read-only statistical baseline (`OFFLINE_RESEARCH_ONLY`). Must display explicit governance disclaimer: *"Informational baseline only; no validated predictive edge; strictly not investment advice."* Production forecasts remain disabled. |
| **Smart Entry / Tournament** | **RESEARCH ONLY** | Retained in offline research mode for quantitative development (`/api/tournament/*`). Excluded from public unauthenticated chart view. |
| **Simulated Trade Journal** | **DISABLED / OUT OF SCOPE** | Manual journaling (`/api/journal/*`) and simulated order entry are internal development tools. Disabled in public release. |
| **User Position Tracker** | **DISABLED / OUT OF SCOPE** | Portfolio / position tracking (`/api/positions/*`) disabled for public chart MVP. |
| **Broker Execution / Orders** | **PERMANENTLY DISABLED** | Permanently out of scope. Zero order placement, no API keys for exchanges, no broker SDKs, no capital custody. |

---

## 2. API Route Allowlist & Governance Classification

| Route Path | HTTP Method | Router | MVP Classification | Target Response in Public Production |
| :--- | :--- | :--- | :--- | :--- |
| `/api/health` | GET | System | **PUBLIC MVP** | `200 OK` (Liveness probe, lightweight status) |
| `/api/market/candles` | GET | Market Monitor | **PUBLIC MVP** | `200 OK` (Normalized closed OHLCV bars with attribution) |
| `/api/market/dashboard` | GET | Market Monitor | **PUBLIC MVP** | `200 OK` (Technical metrics, realized volatility, RSI-14) |
| `/api/market/status` | GET | Market Monitor | **PUBLIC MVP** | `200 OK` (Data mode, feed freshness, price basis) |
| `/api/market/comparator` | GET | Market Monitor | **PUBLIC CONDITIONAL** | `200 OK` with `DATA_UNAVAILABLE` fail-closed when provider offline |
| `/api/market/orderbook` | GET | Market Monitor | **DISABLED IN MVP** | `503 Service Unavailable` (L2 feeds unconfigured) |
| `/api/prediction/latest` | GET | Prediction | **RESEARCH ONLY** | `200 OK` with `OFFLINE_RESEARCH_ONLY` token |
| `/api/prediction/intelligence` | GET | Prediction | **RESEARCH ONLY** | Restricted or `403 Forbidden` for public users |
| `/api/prediction/longitudinal` | GET | Prediction | **RESEARCH ONLY** | Restricted to internal research |
| `/api/tournament/analyse` | POST | Tournament | **RESEARCH ONLY** | `403 Forbidden` / Internal loopback only |
| `/api/tournament/run` | POST | Tournament | **RESEARCH ONLY** | `403 Forbidden` / Internal loopback only |
| `/api/tournament/registry` | GET | Tournament | **RESEARCH ONLY** | Internal research registry |
| `/api/journal/*` | ALL | Manual Journal | **DISABLED** | `404 Not Found` or `403 Forbidden` in public deployment |
| `/api/positions/*` | ALL | User Positions | **DISABLED** | `404 Not Found` or `403 Forbidden` in public deployment |
| `/api/notifications/*` | ALL | Notifications | **RESEARCH ONLY** | Internal researcher alerts |
| `/api/research/*` | ALL | Research | **RESEARCH ONLY** | Internal experimental ledger inspection |
| `/api/terminal/state` | GET | Terminal | **PUBLIC MVP** | `200 OK` (Read-only terminal UI state) |

---

## 3. Deployment Guardrails for Public Staging

1. **Public Reverse Proxy Rule:** Nginx / Cloudflare must block all paths matching `/api/tournament/*`, `/api/journal/*`, `/api/positions/*`, and `/api/research/*`.
2. **CORS Policy:** Strict domain restriction in production (`Access-Control-Allow-Origin: https://btcognitive.com`). Wildcards prohibited.
3. **No Upstream Proxying:** The public API server must never serve raw responses from upstream providers or act as a data redistribution mirror. Endpoints serve transformed, rounded, and attributed candlesticks only.

