# BTCognitive — Market Risk Intelligence & Research Terminal

BTCognitive is a scientific market risk intelligence platform and empirical research terminal for Bitcoin (`BTC/USD`). Built under strict epistemic and econometrics governance, the system provides real-time market monitoring, point-in-time volatility modeling, and an offline research lab for selective, cost-aware trade setups.

> **Research Governance & Epistemic Boundary:**
> - **Strict Non-Execution:** No live broker execution or capital routing.
> - **Epistemic Integrity:** Volatility forecasting accuracy (QLIKE, RMSE) is never conflated with directional return prediction or unconditional profitability.
> - **Production Lock:** Research models remain `OFFLINE_RESEARCH_ONLY`. Production trading is permanently `DISABLED`.

---

## 1. System Architecture

BTCognitive is structured into four primary layers:

```
┌────────────────────────────────────────────────────────┐
│                   Web Research Terminal                │
│       Vanilla JS / CSS UI with UTC Candle Charts       │
└───────────────────────────▲────────────────────────────┘
                            │ REST & WebSocket (/ws)
┌───────────────────────────┴────────────────────────────┐
│              Hardened FastAPI Backend Server           │
│  - OWASP ASVS 5.0 Security Headers & Trusted Host      │
│  - Rate Limiting, CORS & Sanitized Exception Handling  │
│  - Market Monitor, Prediction, Arena, & Health Routes  │
└───────────────────────────▲────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────┐
│            Quantitative & Execution Engines            │
│  - Point-in-Time (PIT) Feature Cache & Data Invariants │
│  - Triple-Barrier Outcome Labeling & Reference Oracle  │
│  - Canonical Decision Records (D_t) & Paper Ledger     │
│  - Realized Semi-Variance & HAR Volatility Models      │
└───────────────────────────▲────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────┐
│                  Public Data Providers                 │
│      Coinbase Exchange • Bitstamp • Kraken Spot        │
└────────────────────────────────────────────────────────┘
```

---

## 2. Market Data & API Endpoints

The backend queries public exchange endpoints without creating synthetic cross-instrument blend prices:
- **Spot Providers:** Real Coinbase, Bitstamp, and Kraken REST/WS tickers and closed candles.
- **Derivatives Separation:** Binance `BTCUSDT` perpetual data is strictly isolated as a derivatives context.
- **Derived Metrics:** Calculates point-in-time momentum, realized volatility, RSI, and relative volume exclusively from validated closed candles.

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/dashboard?horizon=24h` | Unified dashboard payload (quotes, closed candles, drivers, baseline ranges). |
| `GET` | `/api/market-drivers` | Point-in-time market driver indicators across spot venues. |
| `GET` | `/prediction/latest?horizon=24h` | Empirical historical-distribution baseline range (P10–P90 80% quantile band). |
| `GET` | `/api/research/entry-tp-sl` | Research milestone status and barrier contract parameters (governed gate). |
| `GET` | `/api/notifications/recent` | Recent research condition alerts from in-memory ring buffer (limit=20). |
| `GET` | `/api/notifications/settings` | Current notification channel configurations (webhook, telegram, email). |
| `POST` | `/api/notifications/test` | Dispatch a neutral delivery-test alert across configured channels (Admin only). |
| `POST` | `/api/notifications/research-alerts/evaluate` | Manually evaluate documented research conditions on fresh market data. |
| `GET` | `/health` | API operational health, circuit-breaker states, and model authorization flag. |
| `WS` | `/ws` | Hardened real-time intelligence stream (broadcasts candle updates & NEW_ALERT). |

---

## 3. Strategy and Entry Intelligence

BTCognitive evaluates Bitcoin (`BTC/USD`) market structure through three distinct, unmerged research frameworks:

### A. The Structural Entry / TP / SL Track (`BTC-ENTRY-TP-SL-V3`)
This is the formal directional research track registered in `research/entry_tp_sl/`:
- **Market Conditions Evaluated:**
  - Operates on a **15-minute decision cadence** (:00, :15, :30, :45 UTC) using closed 15-minute aggregated spot candles.
  - Detects two causal structural setup archetypes:
    1. **A1 (Sweep and Reclaim):** Identifies when price sweeps a 20-bar rolling swing high or low by 0.1% to 1.5% and closes back inside the prior extreme within 3 bars. Direction: `SHORT` on sweep of highs; `LONG` on sweep of lows.
    2. **A2 (Range Reclaim):** Identifies when price consolidates in a 48-bar range (1.5% to 6.0% width), deviates outside by 0.1% to 1.0%, and closes back within the range boundary.
- **Entry, Take-Profit, and Stop-Loss Calculation:**
  - **Entry Execution Basis:** Fills at the **Open of the immediate next 1-minute bar** ($t_{\text{fill}} = t_0 + 60\text{s}$) following the completed decision bar. If price gaps at open, the order fills at actual open. If the 1-minute bar is missing, the setup fails closed (`DATA_GAP`).
  - **Volatility Scaling:** Uses 14-period Average True Range calculated on 15-minute bars ($\text{ATR}_{14, 15\text{m}}$).
  - **Predetermined Barrier Grid:**
    - Long Setups: $\text{TP} = \text{Entry} + (\text{Multiplier}_{\text{TP}} \times \text{ATR})$, $\text{SL} = \text{Entry} - (\text{Multiplier}_{\text{SL}} \times \text{ATR})$.
    - Short Setups: $\text{TP} = \text{Entry} - (\text{Multiplier}_{\text{TP}} \times \text{ATR})$, $\text{SL} = \text{Entry} + (\text{Multiplier}_{\text{SL}} \times \text{ATR})$.
    - **Primary Reference (`barrier_pair_01`):** $1.0\times\text{ATR}$ TP, $1.0\times\text{ATR}$ SL ($R:R = 1.0$), 240-minute vertical timeout (16 bars).
    - **Confirmatory Secondary:** Pairs ranging from $1.5\times / 1.0\times$ ($R:R = 1.5$) to $2.0\times / 1.0\times$ ($R:R = 2.0$), plus tight (120m) and wide (480m) horizons.
  - **Path Evaluation:** Evaluates 1-minute discrete high/low paths using conservative dual-touch collision resolution. If high hits TP and low hits SL in the same 1-minute bar, the outcome is marked `UNRESOLVED_INTRABAR` and penalized.
- **Friction & Transaction Cost Accounting:**
  - **BASE Scenario:** 10 bps entry fee + 10 bps exit fee + 5 bps entry slip + 5 bps exit slip + 2.5 bps half-spread = **35.0 bps round-trip**.
  - **CONSERVATIVE Scenario:** 15 bps entry fee + 15 bps exit fee + 10 bps entry slip + 15 bps exit slip + 5 bps half-spread = **65.0 bps round-trip**.
- **Empirical Evidence & Governance Verdict:**
  - Evaluated out-of-sample via walk-forward testing on $N = 20,244$ trades across 14 years (2012–2026, 7.7M 1m bars).
  - Setup rules $B_3$ proved statistical separation over matched random baseline $B_0$ ($B_3 > B_0$).
  - LightGBM meta-labeling ($B_4$) achieved a 47.1% win rate (base), but mean net return was **$-0.5678R$** (BASE) and **$-1.0954R$** (CONSERVATIVE).
  - Failed the pre-registered economic hurdle ($E_{\text{min}} \ge +0.10R$).
  - **Scientific Decision:** **`COST_ERASED`**. Live capital deployment is **STRICTLY PROHIBITED**.

### B. Volatility-Compression Strategy (`STRAT-VOLCOMP-01`)
This is the non-directional compression framework registered in `results/volatility_compression_arena_preregistration.md`:
- **Market Conditions Evaluated:** Evaluates the 24-hour conformal excursion envelope width $W_t = \hat{y}_{\text{MFE}, 24h}^{\text{P90}} + \hat{y}_{\text{MAE}, 24h}^{\text{P90}}$.
- **Entry Trigger:** Triggers when $W_t$ compresses below the 10th percentile of its rolling 168-hour history ($\text{CompressionPercentile}_{168h}(W_t) \le 0.10$).
- **Evidence & Current Status:** Proved volatility compression precedes elevated realized price dispersion ($\bar{r} = +1.03\%$). However, economic tradability was unvalidated due to the synthetic "free option" straddle artifact. **Status: `FROZEN / RESEARCH_ONLY`**.

### C. Active Regime-Adaptive Tournament Rules (`V12StrategyTournamentEngine`)
- **Market Conditions Evaluated:** Evaluates completed 1-hour candles using Wilder ADX(14) and 3-candle persistence hysteresis across 4 regimes: `TRENDING_BULL`, `TRENDING_BEAR`, `CONSOLIDATION_RANGE`, `VOL_COMPRESSION_RANGE`.
- **Candidate Strategies:** `MTF_MOMENTUM_TREND` (Donchian breakout with 50% partial exit at 1R), `VOL_COMPRESSION_BREAKOUT` (BBW compression with 12-bar breakout), and `SHORT_HORIZON_MEAN_REVERSION`.
- **System Abstentions:** The system explicitly records an `ABSTAIN` event whenever:
  - Market data has gaps or missing bars ($>60$s missing interval).
  - Regime is `UNKNOWN` or `TRANSITION_UNSUPPORTED`.
  - Signal cooldown is active (within 4 bars of previous setup).
  - Risk budget is exhausted or circuit-breaker state is tripped.
  - Expected net payoff $EV_{\text{net}} \le 0$ after transaction friction.
  - Model authorization is locked (`OFFLINE_RESEARCH_ONLY`).

---

## 4. Entry Alerts and Notifications

BTCognitive includes a multi-channel alert engine that evaluates market conditions in real time without executing live orders.

### A. Alert Evaluation & Trigger Conditions
A background worker in `api/server.py` evaluates market conditions every 60 seconds (or on-demand via `POST /api/notifications/research-alerts/evaluate`):
1. **Data Availability Gate:** Requires at least 200 validated hourly bars from the Coinbase spot feed.
2. **Freshness Gate:** The latest candle timestamp must be $\le 7,200\text{ seconds}$ (2 hours) old. Stale feeds immediately return `STALE_MARKET_DATA` with zero alerts dispatched.
3. **Reference Price Gate:** Requires a valid positive, finite spot price.
4. **Regime Gate:** Gated if market regime is `UNKNOWN` or `TRANSITION_UNSUPPORTED`.
5. **Condition Detection:**
   - **Strategy Rule Triggered:** Active candidate rule (`MTF_MOMENTUM_TREND`, `VOL_COMPRESSION_BREAKOUT`, or `SHORT_HORIZON_MEAN_REVERSION`) satisfied on completed 1h bar in a compatible regime.
   - **Volatility-Compression Coiling:** Bollinger Bandwidth (BBW 20) $\le 20$th percentile or regime is `VOL_COMPRESSION_RANGE`.
   - **Regime Confirmed:** Wilder ADX(14) confirms a persistent 3-candle regime state.

### B. Alert Payload Contents
When triggered, the engine emits a standardized, auditable research alert:
- `id`: Unique identifier (e.g., `rc_1730000000_a1b2c3d4`).
- `type`: `"RESEARCH_CONDITION_ALERT"`.
- `tier`: `"RESEARCH_INTELLIGENCE"` with badge `"RESEARCH ONLY"`.
- `timestamp`: UTC ISO timestamp.
- `reference_price_usd`: Current spot price.
- `condition_name`: Name of the triggered condition (e.g. `VOLATILITY_COMPRESSION_COILING`).
- `condition_hypothesis`: The underlying econometrics hypothesis.
- `trigger_reason`: Exact quantitative condition satisfied.
- `regime`: Active confirmed market regime.
- `limitations`: Explicit statement that live trading and automated execution are permanently disabled.
- `governance`: Object with `product_mode: "ANALYSIS_ONLY"`, `live_trading_enabled: false`, `execution_status: "DISABLED_ANALYSIS_ONLY"`.

> **Note on Directional Levels in Alerts:**
> Specific directional trade targets (entry price, TP, SL) are **intentionally omitted from live production alerts**. Because Track V3 concluded with a `COST_ERASED` verdict, broadcasting directional signals would violate scientific and capital-safety guardrails.

### C. Deduplication, Cooldown, and Quality Controls
- **Cooldown:** Enforces a mandatory **15-minute cooldown** (`COOLDOWN_SECONDS = 900.0`) per condition ID.
- **Hourly Deduplication:** Constructs a deduplication key based on `{condition_id}_{hourly_bucket}_{price_rounded_to_100}` stored in `seen_dedup_hashes`.
- **Restart Persistence:** Cooldown timestamps and seen hashes are persisted to disk at `data/research_alert_state.json`. They are reloaded on process startup to prevent duplicate alerts following server restarts.
- **Non-Research Blocking:** The dispatch router (`dispatch_alert`) strictly blocks any alert where `is_research_alert` and `is_test` are false, preventing unverified market signals from leaking into communication channels.

---

## 5. Implementation Status & Feature Matrix

| Component | Required Behavior | Current State | Verification / Location | Notes |
|---|---|---|---|---|
| **Terminal Alert Feed** | Display real-time research alerts, cooldown badges, and trigger rationales in the Web Terminal UI. | **Operational & Wired** | `web/app.js`, `api/notifications.py` | Handles `NEW_ALERT` and `RESEARCH_CONDITION_ALERT` over `/ws`, sounds alert chime, and presents active alert modal. |
| **AI Forecast Chart Overlay** | Render 15m/1h price persistence baseline and diffusion envelope on TradingView canvas. | **Operational (Research Only)** | `web/app.js` (`ChartTopBar`), `engine/forecast_engine_15m.py` | V29 null-guard applied to `ChartTopBar`. Labeled explicitly as `RESEARCH ONLY · LIVE TRADING DISABLED`. |
| **Directional Signals in Live Alerts** | Include TP, SL, and trade direction in alert notifications. | **Blocked by Governance (`COST_ERASED`)** | `api/notifications.py`, `models/` | Track V3 demonstrated negative net expectancy ($-0.5678R$). Cannot be exposed until prospective edge validation on live L2 order book depth passes pre-registered hurdles. |
| **Real-time L2 Order Book Depth** | Replace square-root volume slippage models with empirical order book depth fills. | **Modeled Approximation Only** | `engine/execution_cost_model.py` | Connect real-time WebSocket Level-2 book feeds (Coinbase/Kraken) to compute dynamic sweep slippage. |

---

## 6. Local Quickstart & Deployment

> **Comprehensive Deployment Guide:** For full Docker, Docker Compose, Fly.io, Render.com, VPS (systemd/nginx), security hardening, and troubleshooting instructions, see [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md).

### Quickstart (Windows PowerShell)

```powershell
# 1. Clone repository
git clone https://github.com/ashishlabs-23/bitcoin-prediction-lab.git
cd bitcoin-prediction-lab

# 2. Activate virtual environment
.\.venv_win\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
cp .env.example .env

# 5. Launch the backend server (FastAPI + uvicorn)
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
```

### Quickstart (macOS / Linux)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
```

Access the research terminal at **`http://127.0.0.1:8000`**. The static frontend (`web/index.html` and `web/app.js`) is served directly by FastAPI without any required Node compilation step.

### IDE Configuration (VS Code / Antigravity)

When opening the parent directory, ensure `.vscode/settings.json` points to the project virtual environment and includes `BTCognitive` in python extraPaths:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/BTCognitive/.venv_win/Scripts/python.exe",
    "python.analysis.extraPaths": [
        "${workspaceFolder}/BTCognitive"
    ],
    "python.autoComplete.extraPaths": [
        "${workspaceFolder}/BTCognitive"
    ]
}
```

---

## 7. Test Suite Execution

BTCognitive enforces strict contract verification across backend endpoints, causal point-in-time features, and frontend assets:

```bash
# 1. Frontend build verification & smoke tests (Node.js)
node build_frontend.js

# 2. Fast market-driver and route baseline tests (Python pytest)
pytest tests/test_market_drivers.py tests/test_market_monitor_routes.py -v

# 3. Forecast chart and frontend contract tests
pytest tests/test_v10_market_data_and_forecast_chart.py tests/test_frontend_contracts.py -v

# 4. V29 Status contract and fail-closed decision anatomy tests
pytest tests/test_v29_status_contract_and_decision_anatomy.py -v

# 5. Entry/TP/SL contract freeze, PIT invariants, and barrier resolver tests
pytest tests/entry_tp_sl/ -v
```

---

## 8. Architectural & System Limitations (Cons)

A critical assessment of the current application reveals the following limitations and trade-offs:

1. **Workspace Layout & Nested Directory Ambiguity:**
   - The git repository and package code are located in a nested subdirectory (`BTCognitive/BTCognitive`) rather than the workspace root. Without explicit `extraPaths` and interpreter paths in `.vscode/settings.json`, external tooling and linters suffer import resolution errors.

2. **Strict Production & Model Lock (No Live Trading):**
   - The platform deliberately enforces `OFFLINE_RESEARCH_ONLY` model authorization and `DISABLED` live trading. Directional accuracy is treated as an unvalidated hypothesis; users looking for automated signal execution or broker connectivity will find these capabilities blocked by protocol.

3. **Flat File Data Ingestion & I/O Overhead:**
   - Historical 1-minute bar data (~394 MB CSV) is stored in raw flat files (`data/raw/btcusd_1-min_data.csv`). Frequent full-file SHA-256 verifications and CSV parsing introduce noticeable disk I/O latency and memory overhead compared to columnar formats (e.g., Parquet, Arrow, or TimescaleDB).

4. **Public REST API Rate Limits & Upstream Fragility:**
   - Market data ingestion depends on public exchange REST endpoints (Coinbase, Bitstamp, Kraken). Outages, network partitions, or rate limits immediately trigger "fail-closed" unavailable states. There is no enterprise-tier multi-source tick aggregator or resilient failover gateway.

5. **Monolithic Frontend Architecture:**
   - The terminal frontend uses React 18 with in-browser components (`web/app.js`, ~12,000 lines) and TradingView Lightweight Charts served directly without an npm build pipeline. While zero-build simplifies deployment, modular bundlers (e.g., Vite/TypeScript) would improve code splitting and component encapsulation.

6. **Single-Node SQLite Concurrency Limits:**
   - Paper trading transactions, canonical decisions ($D_t$), and audit ledgers rely on SQLite and local disk persistence. This architecture is not designed for multi-node distributed clustering or horizontal horizontal write scaling without encountering database lock contention.

7. **Prospective Validation Delay:**
   - In accordance with the governing econometrics contract, at least 100 non-overlapping post-freeze forward blocks must be collected before prospective confirmatory evaluation. As a result, prospective model promotion takes several weeks of continuous live data accumulation.

---

## 9. Research Governance & Epistemic Principles

- **Target Separation:** 24-hour forward realized variance (`rv24h_var_ann`) is an hourly-sampled variance proxy across 24 closed hourly candles, distinct from longer 168-hour targets.
- **Loss Functions & Evaluation:** Models are evaluated via asymmetric QLIKE and robust RMSE metrics, with Diebold-Mariano tests applying the Harvey-Leybourne-Newbold (1997) finite-sample correction.
- **Point-in-Time Discipline:** Strict causality ($t_{\text{feature}} \le t_{\text{decision}} < t_{\text{maturity}}$); no lookahead or retroactive dataset revisions.
