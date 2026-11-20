# BTCognitive — Three-Lane Data Architecture Matrix

**Version:** 1.0.0 (Phase 1 Baseline)  
**Effective Date:** 29 October 2026  
**Implementation File:** `engine/data_mode.py`  
**Governing Standard:** BTCognitive Offline-First Research Architecture  

---

## 1. Architectural Lane Definitions

BTCognitive strictly enforces three discrete operational data lanes. Mode ambiguity or silent fallback between lanes is prohibited by code-level assertion guards.

| Characteristic | Lane 1: `fixture` | Lane 2: `offline_research` | Lane 3: `provider` |
| :--- | :--- | :--- | :--- |
| **Primary Intent** | Deterministic automated testing & isolated CI runs | Private loopback research, algorithm backtesting, model evaluation | Live staging / production market feeds (Future) |
| **Default Trigger** | Automated test runners (pytest detected in `sys.modules`) | Loopback development server (`uvicorn` on `127.0.0.1:8000`) | Explicit environment configuration (`BTC_DATA_MODE=provider`) |
| **External Network Permitted** | **FALSE** (`ExternalNetworkBlockedError` raised before socket creation) | **FALSE** (`ExternalNetworkBlockedError` raised before socket creation) | **FALSE (Phase 1 Fail-Closed)**; True only upon licensed vendor verification |
| **Protected Artifact Access** | **BLOCKED** (`ProtectedFileAccessBlockedError` raised on empirical datasets) | **PERMITTED** (Read-only access to `data/raw/ohlcv.parquet`) | **PERMITTED** (Read-only historical baseline) |
| **Candle Data Source** | Synthetic deterministic sinusoids (`DETERMINISTIC_FIXTURE`) | Canonical hourly parquet snapshot (`LOCAL_HISTORICAL_SNAPSHOT`) | Configured external exchange REST (`PROVIDER_EXCHANGE_REST`) |
| **Primary Symbol** | Strictly `BTC-USD` | Strictly `BTC-USD` | Strictly `BTC-USD` |
| **Price Observation** | Deterministic fixture close (e.g. ~$80,000 baseline) | Genuine last closed candle price in parquet | Exchange spot ticker quote (Truthful null if unavailable) |
| **Failure Mode** | Fail-closed with explicit error assertion | Fail-closed with `HISTORICAL_SNAPSHOT` degraded flag | Fail-closed: `DATA_UNAVAILABLE` with truthful nulls (No fake quotes) |
| **Rights Clearance Status** | `FIXTURE_ONLY` | `REVIEW_REQUIRED` (Internal private research only) | `BLOCKED` (Pending commercial redistributable license) |

---

## 2. Invariant Rules Across All Lanes

1. **Zero Outbound Market Traffic in Restricted Modes:**
   Neither `fixture` nor `offline_research` may make DNS queries, open HTTP/HTTPS sockets, or connect to WebSockets. Calls to `httpx.get`, `urllib.request.urlopen`, or `WebSocket` fail closed via `assert_no_external_network()`.

2. **Zero Simulated Live Trades / Attempts:**
   Running calculations or clicking *Analyse* in any mode produces `attempts_created: 0`. No prospective ledgers are appended during research audits or deterministic checks.

3. **Bit-Level Immutability of Protected Research Datasets:**
   The 6 historical datasets (`ohlcv.parquet`, backup, backfilled, and the 3 prospective ledgers) are immutable. `fixture` mode is physically barred from accessing them.

4. **Canonical Symbol Alignment:**
   All routes normalize incoming aliases (`BTC/USD`, `BTCUSD`, `BTCUSDT`) to canonical `BTC-USD` in responses. Unsupported assets (`ETH-USD`, etc.) are rejected with HTTP 422 / `UNSUPPORTED_REQUEST`.

5. **Truthful Reporting Over Synthetic Fabrication:**
   When an external feed is unavailable or blocked, APIs report `price_usd: null` and `status: DATA_UNAVAILABLE`. Under no circumstances are static fallback quotes (such as $80,000) fabricated to disguise feed interruptions.

