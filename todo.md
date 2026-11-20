# BTCognitive — Master Project Todo & Phased Roadmap (`todo.md`)
## Phased Implementation Plan for Institutional BTC/USD Market Risk Intelligence

**Repository:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Current Milestone:** V35.4 / V35.5 Transition  
**Operating Posture:** `ANALYSIS_ONLY` | Live Trading: `PERMANENTLY DISABLED`  

---

## Milestone V35.4: Econometric Parameterization & Gateway Hardening (COMPLETED)

- [x] **M-01:** Reconcile Parkinson volatility calculation in `engine/strategy_signal_engine.py` with `annualize: bool = False, periods_per_year: float = 8760.0`, scaling by $\sqrt{8760}$.
- [x] **M-02:** Reconcile Sharpe, Sortino, and Calmar ratios in `models/risk_metrics.py` with explicit `freq="1h"` ($\sqrt{8760}$) and `freq="1d"` ($\sqrt{365}$) annualization.
- [x] **M-03:** Verify Bitstamp is recognized in `SUPPORTED_VENUES` and `BTCUSD`/`BTC-USD` in `SUPPORTED_INSTRUMENTS` (`engine/data_verification.py`).
- [x] **M-04:** Enforce 200-bar minimum warm-up window for EMA200 in regime tournament (`engine/regime_strategy_tournament.py`).
- [x] **L-01:** Clean impossible dead-code comparison condition in `engine/range_forecast_service.py`.
- [x] **L-02:** Align WebSocket tick event symbol from legacy `BTCUSDT` to canonical `BTC-USD` (`api/candle_manager.py`).
- [x] **L-03:** Verify Bitstamp integration tests use completed candle timestamps (`tests/test_v33_7_bitstamp_integration.py`).
- [x] **REC-01:** Implement consolidated gateway endpoint `GET /api/terminal/bundle` in `api/routes_terminal.py` to eliminate 13 independent client polls.
- [x] **REC-02:** Wrap root React application in `AppErrorBoundary` class component in `web/app.js` to prevent blank-screen unmounts.
- [x] **REC-03:** Optimize Three.js animation loop using squared distance comparisons and pause rendering on `document.hidden`.
- [x] **REC-05:** Enforce Content-Security-Policy (CSP) meta header in `web/index.html`.
- [x] **REG-01:** Achieve 100% PASS rate across all 3 active test categories (306/306 tests passing, zero protected hash changes).

---

## Milestone V35.5: Continuous Historical Ingestion & Tardis Ingestion Pipeline

- [ ] **TARDIS-01:** Run licensed sample trade parser across Bitstamp Spot BTC/USD monthly sample datasets.
- [ ] **TARDIS-02:** Validate millisecond timestamp monotonicity, duplicate trade deduplication, and exchange downtime interval detection.
- [ ] **TARDIS-03:** Construct continuous 4-year trade-to-candle aggregation generating 5m, 1h, and 4h immutable Parquet datasets.
- [ ] **TARDIS-04:** Compute and record SHA-256 provenance hashes for all newly created Parquet segments.
- [ ] **TARDIS-05:** Verify that indicator rolling warm-up windows reset cleanly across historical exchange outage boundaries.

---

## Milestone V35.6: Prospective Evidence Accumulation & Model Governance Gate

- [ ] **PROSPECT-01:** Maintain append-only prospective forecast ledger in `experiments/results/prospective_entry_ledger_v2.jsonl`.
- [ ] **PROSPECT-02:** Execute causal delayed outcome resolution for 168h forward realized variance without lookahead.
- [ ] **PROSPECT-03:** Track non-overlapping prospective block count toward the 100-block confirmatory hurdle (current: 3/100).
- [ ] **PROSPECT-04:** Upon reaching 100 clean blocks, execute formal Diebold-Mariano test with Harvey-Leybourne-Newbold (1997) sample correction.
- [ ] **PROSPECT-05:** Evaluate unpromoted challenger `HAR-RS-DOW-v1.0` against baseline `Standard-HAR-v1.0` under QLIKE loss.

---

## Milestone V35.7: Frontend Modernization & Component Virtualization

- [ ] **FE-01:** Implement DOM list virtualization for large historical ledgers in `ManualTradeJournalView` and `ResearchResultsView`.
- [ ] **FE-02:** Split monolithic `web/app.js` (1.03 MB) into clean, maintainable ES modules (`web/modules/`) using native browser ESM.
- [ ] **FE-03:** Add interactive hover tooltips displaying exact conformal prediction interval bounds ($\hat{q}_{0.05}$, $\hat{q}_{0.95}$) on the TradingView canvas.
- [ ] **FE-04:** Integrate debounced `ResizeObserver` on `LightweightCandleChart` to prevent layout thrashing on window resize.
- [ ] **FE-05:** Add visual connection quality indicator (RTT latency, lost ticks, reconnect counter) to the Institutional Ticker Ribbon.

---

## Milestone V35.8: CI/CD Quality Automation & CodeRabbit Integration

- [x] **CI-01:** Create `.coderabbit.yaml` tailored for quantitative finance, causal bounds, and fail-closed integrity.
- [x] **CI-02:** Create GitHub Actions workflow (`.github/workflows/ci.yml`) running frontend verification and full regression suite on every PR.
- [ ] **CI-03:** Configure branch protection rules on `main` requiring passing CI and CodeRabbit approval before merge.
- [ ] **CI-04:** Add automated dependency vulnerability scanning using GitHub Dependabot or pip-audit.
