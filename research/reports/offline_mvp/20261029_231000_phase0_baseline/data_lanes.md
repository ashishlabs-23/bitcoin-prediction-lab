# BTCognitive — Data Lane Architecture & Provenance Specification

**Audit Phase:** Phase 0 Baseline  
**Date:** 29 October 2026  
**Location:** `research/reports/offline_mvp/20261029_231000_phase0_baseline/data_lanes.md`  
**Execution Context:** Internal Offline Research MVP (`127.0.0.1:8000`)

---

## 1. Three-Lane Architectural Model

To eliminate silent data leakage, accidental live network calls, and conflation of test fixtures with empirical findings, BTCognitive defines three strictly partitioned data lanes:

| Data Lane | Primary Purpose | Permitted Data Sources | Invariance & Non-Negotiable Prohibitions | Permitted Rights Status |
| :--- | :--- | :--- | :--- | :--- |
| **`fixture`** | Repeatable, deterministic automated QA, regression suites, and browser CI tests. | Hardcoded JSON/array fixtures, synthetic OHLCV sequences with known edge cases (gaps, flatlines, extreme spikes). | **MUST NEVER** read empirical protected datasets silently. **MUST NEVER** feed fixture backtest outputs into model scorecards or present fixtures as real market evidence. | `FIXTURE_ONLY` |
| **`offline_research`** | Local exploratory charting, indicator validation, regime classification, and causal backtesting. | Verified local historical parquet snapshots (`data/raw/ohlcv.parquet`, `data/research/..._v2`). | **MUST NEVER** silently fill historical gaps. **MUST NEVER** relabel `BTCUSDT` as `BTC/USD`. **MUST NEVER** make outbound network calls. | `RESEARCH_ALLOWED` or `REVIEW_REQUIRED` |
| **`provider`** | Staging / future live exchange feed integration (Post-MVP only). | Authenticated, contractually licensed commercial exchange feeds (e.g. Bitstamp DLA, CoinGecko Commercial). | **STRICTLY DISABLED BY DEFAULT**. Cannot be activated by UI clicks, environment drift, or undocumented fallback routes. | `PUBLIC_DISPLAY_CLEARED` |

---

## 2. Dataset Manifest Specifications

Every empirical or fixture dataset must carry an authoritative manifest schema:

```json
{
  "dataset_id": "COINBASE_BTC_USD_HOURLY_CANONICAL_RAW",
  "provider": "Coinbase Exchange",
  "instrument": "BTC-USD",
  "quote_currency": "USD",
  "venue": "COINBASE",
  "interval": "1h",
  "timezone": "UTC",
  "downloaded_at_utc": "2026-10-26T16:00:00Z",
  "range_start_utc": "2022-01-01T00:00:00Z",
  "range_end_utc": "2026-10-26T16:00:00Z",
  "row_count": 42233,
  "sha256": "c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f",
  "terms_url": "https://www.coinbase.com/legal/market_data",
  "permitted_use_status": "REVIEW_REQUIRED",
  "permitted_activities": [
    "OFFLINE_LOCAL_RESEARCH",
    "INTERNAL_ALGORITHM_VERIFICATION"
  ],
  "prohibited_activities": [
    "PUBLIC_REDISTRIBUTION",
    "HOSTED_COMMERCIAL_DISPLAY",
    "UNAUTHORIZED_AI_TRAINING"
  ],
  "known_gaps": [],
  "validation_report": "research/reports/v32_63_feature_value_audit/20261029_223400_audit/dataset_integrity_report.md",
  "notes": "Historical gap candles backfilled from exchange archive; terminates 73 hours prior to Oct 29 audit date."
}
```

---

## 3. Reachable Network Calls & Local Leak Inventory

An empirical source code audit across all API routes, engines, and frontend scripts identified the following network-sensitive paths:

| Component | File & Line Number | Trigger Mechanism | Target URL / Remote Host | Current Behavior & Defect | Phase 1 Required Remediation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Frontend UI** | `web/app.js:1180` | Loading candlestick chart in browser | `https://api.exchange.coinbase.com/products/BTC-USD/candles` | Browser directly attempts outbound fetch to Coinbase REST before falling back to backend | Inject client-side `DATA_MODE` check; in offline/fixture mode, bypass Coinbase REST entirely and query local `/api/market/candles` |
| **Frontend UI** | `web/app.js:1190` | Fallback backend candle fetch | `${getApiBaseUrl()}/api/market/candles?symbol=BTCUSDT&interval=1h` | Requests `symbol=BTCUSDT` rather than canonical `BTC-USD` | Harmonize request parameter to `symbol=BTC-USD` matching canonical dataset |
| **Backend API** | `api/routes_market.py:115` | `GET /market/comparator` | External exchange APIs via `api/market_drivers.py:_fetch_quote` | Tries to reach Coinbase, Kraken, Bitstamp APIs asynchronously | Gate endpoint behind `DATA_MODE`; if `offline_research` or `fixture`, return `status="DATA_UNAVAILABLE"` immediately without socket creation |
| **Backend Engine** | `api/market_drivers.py:61` | Internal driver polling | Public HTTP endpoints via `httpx.AsyncClient` | Makes outbound HTTP calls if triggered | Enforce early fail-closed guard when `DATA_MODE != "provider"` |
| **Backend Engine** | `engine/coinbase_15m_adapter.py:21` | Requesting 15m candles | `urllib.request` to Coinbase REST | Attempts live scraping of 15m candles | Return `status="UNSUPPORTED_REQUEST"` without network socket creation |

---

## 4. Phase 1 Implementation Plan for Data-Lane Gating

1. **Environment Flag:** Formalize `DATA_MODE = "fixture" | "offline_research" | "provider"`.
   - Default when unconfigured: `"fixture"` for pytest runners; `"offline_research"` for local web server (`127.0.0.1`).
2. **Provider Route Hard-Lock:** If `DATA_MODE != "provider"`, any code attempting remote network connections must immediately raise a structured `ProviderDisabledException` or return a graceful `DATA_UNAVAILABLE` payload before DNS lookup or socket creation.
3. **Frontend Awareness:** Deliver `DATA_MODE` in `GET /api/terminal/status` so `web/app.js` renders an explicit data lane badge and skips all client-side outbound REST calls.

