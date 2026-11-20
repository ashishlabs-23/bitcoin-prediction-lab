# BTCognitive V32.31 — Opt-In Coinbase L2 Entry-Gating Research Report

**Date:** 2026-10-25  
**Version:** V32.31  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed; zero live broker/order execution paths)  
**Lead Econometrician:** Agent 2  
**Lead Microstructure Architect:** Agent 3  
**Lead QA Orchestrator:** Antigravity  

---

## 1. Executive Summary & Governed Decisions

| Dimension | Governed Status | Quantitative Justification |
| :--- | :--- | :--- |
| **Software Implementation & Verification** | **`SOFTWARE_QA_PASS`** | 86/86 automated regression & L2 unit tests passed (100%). Independent browser subagent QA verified all UI controls with **0 console errors**. Port 8000 cleanly closed with no lingering daemons. All 5 protected files verified **100% byte-identical** against baseline SHA-256 hashes. |
| **Scientific Hypothesis ($H_1$)** | **`NO_GO_NO_VALIDATED_EDGE`** | Evaluated across 33,424 Coinbase hourly candles, macro breakout net returns remain negative (-0.1778 R under 27 bps). L2 OFI entry-gating is pre-registered under $H_1$, but prospective confirmatory accumulation ($N \ge 100$) has not yet matured. Zero live trading authorization permitted. |
| **Prospective Evidence Accumulation** | **`COLLECTING_INSUFFICIENT_SAMPLE`** | Requires accumulation of at least $N \ge 100$ independent non-overlapping 168-hour trades before confirmatory evaluation. Historical L2 fabrication from OHLCV is strictly prohibited. |
| **Production Execution Authorization** | **`OFFLINE_RESEARCH_ONLY`** | Broker APIs disconnected; order placement permanently fail-closed. |
| **Live Trading Gate** | **`DISABLED`** | Live capital deployment remains strictly unauthorized. |

---

## 2. Architecture & Design Principles

### 2.1 Resilient, Opt-In WebSocket Collector (`engine/coinbase_l2_collector.py`)
- **Default Disabled:** Requires explicit operator configuration (`COINBASE_L2_COLLECTOR_ENABLED=1`). Never launches automatically on startup or during tests.
- **BTC-USD Spot Only:** Rejects any other symbol or derivative instrument.
- **Protocol Adherence:** Implements Coinbase Exchange WebSocket protocol subscribing to `level2_batch`, `matches`, and `heartbeat` channels on `wss://ws-feed.exchange.coinbase.com`.
- **Fault Detection & Resynchronization:**
  - Detects sequence gaps ($\text{seq}_{\text{curr}} > \text{seq}_{\text{prev}} + 1$).
  - Detects heartbeat stalls ($> 5.0\text{s}$).
  - Detects socket drops and triggers graceful reconnection backoff (up to 5 attempts).
  - Instantly marks local book `is_synchronized = False` and invalidates downstream features until an authoritative snapshot arrives.
- **Zero Fabrication:** Microstructure features are never backfilled or estimated from 1-minute or hourly OHLCV candles.

### 2.2 Point-in-Time Microstructure Features (`engine/l2_microstructure_features.py`)
- **Order Flow Imbalance (OFI):** Implemented according to Cont, Kukanov & Stoikov (2014):
  $$\text{OFI} = \sum_{k} \left(\Delta Q_B(k) - \Delta Q_A(k)\right)$$
  Tracks discrete top-of-book quote and depth shifts, measuring net limit-order buying pressure into breakout candles.
- **Order Book Imbalance (OBI):** Computes top-5, top-10, and top-25 depth imbalance:
  $$\text{OBI}_K = \frac{\sum_{i=1}^K V_i^{\text{bid}} - \sum_{i=1}^K V_i^{\text{ask}}}{\sum_{i=1}^K V_i^{\text{bid}} + \sum_{i=1}^K V_i^{\text{ask}}} \in [-1.0, +1.0]$$
- **Cumulative Volume Delta (CVD):** Aggressor trade volume delta from signed market matches.
- **Top-of-Book Spread:** Bid-ask spread relative to midpoint in basis points.
- **Causal Isolation:** Calculations consume strictly events with receipt timestamps $t \le t_{\text{decision}}$.

### 2.3 Shadow Gating & Dedicated Ledger (`engine/prospective_l2_shadow_gating.py`)
- **Target Strategy:** `TSMOM_DONCHIAN_168H_336H` (BTC-USD Spot, 168h breakout with 336h macro EMA trend filter).
- **Two-Phase Audit Trail:**
  - *Phase A (`L2_GATED_CANDIDATE`):* Immutable record emitted at decision time $t_0$, recording setup parameters, full L2 snapshot, and gate decision.
  - *Phase B (`L2_GATED_OUTCOME`):* Immutable outcome record appended after barrier resolution or 168h horizon timeout.
- **Dedicated Ledger Path:** [data/research/prospective_l2_gated_ledger_v1.jsonl](file:///c:/Projects/BTCognitive/BTCognitive/data/research/prospective_l2_gated_ledger_v1.jsonl).
  All 5 protected historical and prospective ledgers remain untouched.

---

## 3. Pre-Registered Protocol & Decision Criteria

Pre-registered in [research/reports/v32_31_l2_preregistration_protocol.md](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/v32_31_l2_preregistration_protocol.md) before evaluating outcomes:

1. **Primary Hypothesis ($H_1$):** Conditioning entry on contemporaneous positive OFI ($\text{OFI}_{15\text{m}} > 0$), balanced book depth ($\text{OBI}_5 > -0.20$), and tight spread ($\le 5.0\text{ bps}$) will filter toxic breakouts, improving net return expectancy by $\Delta \mathbb{E}[R_{\text{net}}] \ge +0.20\text{ R}$ under the Active Trader (27 bps) fee scenario.
2. **Fail-Closed Gate Rules:**
   $$\text{Decision} = \begin{cases} 
   \text{GATE\_ACCEPTED\_SHADOW} & \text{if } \text{Sync}=\text{True} \land \text{OFI}_{15\text{m}} > 0.0 \land \text{OBI}_5 > -0.20 \land \text{Spread} \le 5.0\text{ bps} \\
   \text{GATE\_REJECTED\_TOXIC\_OFI} & \text{if } \text{OFI}_{15\text{m}} \le 0.0 \\
   \text{GATE\_REJECTED\_HEAVY\_ASK} & \text{if } \text{OBI}_5 \le -0.20 \\
   \text{GATE\_REJECTED\_WIDE\_SPREAD} & \text{if } \text{Spread} > 5.0\text{ bps} \\
   \text{GATE\_ABSTAIN\_L2\_UNAVAILABLE} & \text{if } \text{Feed Desynchronized or Stale } (>5.0\text{s})
   \end{cases}$$
3. **Statistical Power & Sample Size:**
   Target of at least $N \ge 100$ independent, non-overlapping 168-hour prospective trades is required to achieve 80% statistical power ($\beta=0.20, \alpha=0.05$) to detect $\Delta = +0.25\text{ R}$.
4. **Prohibition on Threshold Fishing:** Post-hoc tuning of filter thresholds on the confirmatory sample is strictly prohibited.

---

## 4. Test Execution Ledger & Reproducibility

### 4.1 Automated Backend Regression & Unit Suite (86 Tests, 100% Pass)
```powershell
python -m pytest tests/test_strategy_to_alert_pipeline.py tests/test_entry_contracts_and_resolver.py tests/test_smart_entry_api.py tests/test_v32_25_directional_integration.py tests/test_prospective_shadow_collector.py tests/test_prospective_worker_and_resilience.py tests/test_isolated_real_http_server.py tests/test_coinbase_l2_collector_and_gating.py -v
```
**Results:** **86 passed, 3 warnings in 14.85s (Exit Code 0)**.
- `tests/test_coinbase_l2_collector_and_gating.py`: 13 passed.
  - Collector disabled-by-default and product authorization: Passed.
  - Snapshot & incremental l2update order-book reconstruction: Passed.
  - Sequence gap detection and fail-closed desync: Passed.
  - Heartbeat stall (>5.0s) staleness invalidation: Passed.
  - Hand-computed Cont et al. OFI known-answer fixture: Passed.
  - OBI depth and CVD trade prints: Passed.
  - Causal point-in-time boundary (no lookahead): Passed.
  - Complete gating decision matrix: Passed.
  - Two-phase ledger audit and idempotency: Passed.
  - Protected files isolation assertion: Passed.
  - API HTTP GET endpoints for L2 gating status & evaluation: Passed.
- `tests/test_strategy_to_alert_pipeline.py`: 22 passed.
- `tests/test_entry_contracts_and_resolver.py`: 13 passed.
- `tests/test_smart_entry_api.py`: 7 passed.
- `tests/test_v32_25_directional_integration.py`: 9 passed.
- `tests/test_prospective_shadow_collector.py`: 12 passed.
- `tests/test_prospective_worker_and_resilience.py`: 6 passed.
- `tests/test_isolated_real_http_server.py`: 4 passed over loopback TCP socket.

### 4.2 Frontend Unit & Budget Suite (100% Pass)
```powershell
node tests_frontend.js
```
**Results:** **100% passed (Exit Code 0)**.
- Formatters, in-flight deduplication, TTL caching, 429 backoff handling.
- Polling budget: **29.5 req/min steady-state** vs. server limit of 60 req/min.
- Smart Entry and V32.31 Coinbase L2 Microstructure Gating UI markers verified.

---

## 5. Independent Browser QA Matrix & Evidence

An independent browser QA subagent inspected the application running locally at `http://127.0.0.1:8000`:

| Checkpoint | UI Component / Route | Verification Condition | Result | Evidence / Log Check |
| :--- | :--- | :--- | :---: | :--- |
| **QA-01** | `#/terminal` | Workstation loads cleanly; candlesticks and telemetry intact | **PASS** | 0 console errors |
| **QA-02** | `#/smart-entry` | Smart Entry route renders decision engine view | **PASS** | View rendered |
| **QA-03** | `#l2-gating-research-panel` | Dedicated V32.31 L2 entry-gating research card rendered | **PASS** | Element present |
| **QA-04** | `#l2-collector-badge` | Displays `COLLECTOR: DISABLED BY DEFAULT` | **PASS** | Verified |
| **QA-05** | `#l2-trading-badge` | Displays `LIVE TRADING: DISABLED` | **PASS** | Verified |
| **QA-06** | `#l2-target-strategy` | Displays `TSMOM_168H_336H` | **PASS** | Verified |
| **QA-07** | `#l2-gating-rules` | Displays `OFI > 0 · OBI₅ > -0.20 · Spread ≤ 5 bps` | **PASS** | Verified |
| **QA-08** | `#l2-sample-target` | Displays `N ≥ 100 Trades` | **PASS** | Verified |
| **QA-09** | `#l2-confirmatory-decision`| Displays `NOT_STARTED_INSUFFICIENT_SAMPLE` | **PASS** | Verified |
| **QA-10** | `#l2-gating-callout` | Displays fail-closed warning and non-execution boundary | **PASS** | Verified |
| **QA-11** | Interactive Demo | "Load Synthetic Demo" / "Evaluate" generates decision | **PASS** | Calculation verified |
| **QA-12** | Responsive 768px (Tablet) | Viewport resized; cards wrap cleanly with no overflow | **PASS** | Verified |
| **QA-13** | Responsive 375px (Mobile) | Viewport resized; single-column stacked layout verified | **PASS** | Verified |
| **QA-14** | `#/research` & `#/arena` | Existing scientific and tournament routes remain functional | **PASS** | Verified |
| **QA-15** | Console Error Audit | Browser console inspected for unhandled JS errors | **PASS** | **0 Errors** |

---

## 6. Protected Files Integrity Audit

All 5 protected files were hashed using SHA-256 before code changes and after full test execution:

| Protected File Path | Baseline SHA-256 Hash | Post-QA SHA-256 Hash | Integrity Status |
| :--- | :--- | :--- | :---: |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **MATCH (Byte-Identical)** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **MATCH (Byte-Identical)** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **MATCH (Byte-Identical)** |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **MATCH (Byte-Identical)** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **MATCH (Byte-Identical)** |

---

## 7. Operating Instructions for Opt-In L2 Shadow Collector

### 7.1 Enabling Collection in an Authorized Research Session
By default, the collector is disabled. To activate ingestion in an authorized forward shadow collection session:
```powershell
# 1. Set explicit environment variable
$env:COINBASE_L2_COLLECTOR_ENABLED = "1"

# 2. Launch research server
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000

# 3. Query L2 feed and evaluation status via API
curl http://127.0.0.1:8000/api/research/l2-gating-status
curl http://127.0.0.1:8000/api/research/l2-shadow-evaluation
```

### 7.2 Graceful Shutdown & Socket De-registration
To terminate collection cleanly:
```powershell
# Stop server process (Ctrl+C or Stop-Process)
Stop-Process -Name "python" -Force
# Verify port 8000 is clean with zero listening sockets
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
```

---

## 8. Research Limitations & Epistemic Boundaries

1. **Short Half-Life of Microstructure Features:** Order Flow Imbalance has an empirical memory of $< 5$ minutes. It acts strictly as an **execution-moment toxicity filter** at bar $t+1$ Open, not as a predictor of 7-day macroeconomic drift.
2. **Low 168h Breakout Frequency:** Macro breakouts occur approximately 40–50 times per year on BTC-USD. Accumulating $N \ge 100$ independent, non-overlapping clean trades requires approximately 2 years of forward prospective observation.
3. **Friction Hurdle:** Even if L2 gating eliminates 30% of false breakouts, the baseline 168h strategy operates from a net return of $-0.1778\text{ R}$ under 27 bps. Gating must produce a substantial gross lift to achieve economic viability ($EV_{\text{net}} > 0$).
4. **Governed Release Verdict:** **`NO_GO_NO_VALIDATED_EDGE`**. No live trading or model promotion is authorized until confirmatory prospective data satisfies the frozen pre-registered gate.
