# BTCognitive V32.34 — Frontend Feature Visibility & Disposition Matrix

**Date:** 2026-10-25  
**Version:** V32.34  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Governing Rule:** Every retained feature must either render correctly in an appropriate UI location or be clearly marked as research-only, unavailable, blocked, parked, or not executed. Zero synthetic fabrication or unearned profitability claims.

---

## 1. Executive Summary

This feature visibility matrix catalogs all 28 frontend, terminal, research, and infrastructure features within BTCognitive V32.34. Each feature is audited against its DOM marker, route location, operational state, research boundary, and browser verification status.

---

## 2. Master Feature Visibility & Disposition Matrix

| # | Feature Name | UI Route / Component | DOM Selector / Marker | Operational State | Disposition / Boundary Label | Browser QA Verification |
|---|---|---|---|---|---|---|
| 1 | **System Health & Posture Banner** | All Views (`Navbar`) | `#health-status-badge`, `#health-mode-badge` | Operational | `READY · AUTHORIZED (VOLATILITY RISK)` / `RESEARCH BLOCKED` | PASS (Desktop, Tablet, Mobile) |
| 2 | **System at a Glance (8-Point Telemetry)** | `#/landing` (`HeroSection`) | `.system-at-a-glance-card`, `#glance-system-mode` | Operational | Answers at a glance: System Mode, Market Data, Strategy State, Gate, Risk Model, Friction, Alerts, Verdict | PASS (Desktop, Tablet, Mobile) |
| 3 | **Live Coinbase BTC-USD Ticker** | Navbar & Landing | `#ticker-price-pill`, `#price-display` | Operational | Real-time WebSocket + REST Coinbase Spot ticker ($91k-$92k BTC-USD) | PASS |
| 4 | **Interactive Candlestick Chart** | `#/terminal` (`LiveTerminal`) | `#chart-canvas`, `#tradingview-canvas` | Operational | HTML5 Canvas 2D hardware-accelerated candle engine | PASS |
| 5 | **Multi-Timeframe Selectors** | `#/terminal` | `.tf-btn`, `[data-tf="1m"]`, `[data-tf="15m"]`, `[data-tf="1h"]` | Operational | Interactive resolution switching (1m, 15m, 1H, 4H, 1D) | PASS |
| 6 | **Technical Indicators Engine** | `#/terminal` | `.indicator-btn`, `[data-ind="ema"]`, `[data-ind="bb"]`, `[data-ind="rsi"]` | Operational | EMA 20/50, Bollinger Bands (20,2), RSI 14, ATR, ADX calculation overlays | PASS |
| 7 | **Pro Mode Chart Controls** | `#/terminal` | `#pro-mode-toggle`, `#terminal-fullscreen-btn` | Operational | Expanded workspace with detailed orderbook and trade tape | PASS |
| 8 | **Quick Smart Entry Drawer** | `#/terminal` | `#btn-quick-smart-entry`, `.smart-entry-drawer` | Operational | Slide-out entry gate drawer directly from live terminal | PASS |
| 9 | **Smart Entry Gate Main Panel** | `#/smart-entry` | `#smart-entry-panel`, `#v19-area-smart-entry` | Operational | Fail-closed multi-stage quantitative entry filtration gate | PASS |
| 10 | **Sync Live Terminal AI Context** | `#/smart-entry` | `#smart-entry-btn-live-context` | Operational | Synchronizes latest 15m candle bar and volatility regime into gate | PASS |
| 11 | **Synthetic Snapshot Demo** | `#/smart-entry` | `#smart-entry-btn-synthetic-demo` | Operational | Loads 1h benchmark candle fixture for reproducible offline testing | PASS |
| 12 | **Smart Entry Snapshot Evaluation** | `#/smart-entry` | `#smart-entry-btn-evaluate`, `#smart-entry-status-badge` | Operational | Evaluates snapshot under strict conservative SL_FIRST collision rule | PASS (Result: ABSTAIN / REJECTED) |
| 13 | **Directional Edge & Drift Display** | `#/smart-entry` | `#result-directional-auc`, `#result-evidence-quality` | Research Only | AUC ~0.504 ± 0.012; explicitly marked as driftless null ($\mu = 0.0$) | PASS (Truthful display) |
| 14 | **Multi-Tier Friction Breakdown** | `#/smart-entry` | `#result-rrr-costs`, `.cost-tier-table` | Operational | Itemized 27 bps (Active Trader) vs 87 bps (Retail) hurdle | PASS |
| 15 | **Excursion Distribution** | `#/smart-entry` | `#result-excursion-dist`, `.prob-density-bars` | Operational | Empirical first-passage probability density over forward horizon | PASS |
| 16 | **Coinbase L2 Gating Panel** | `#/smart-entry` | `#l2-gating-research-panel`, `L2GatingResearchPanel` | Research Only | Cont et al. (2014) Order Flow Imbalance and micro-price drift | PASS |
| 17 | **L2 Collector & Continuity Badges** | `#/smart-entry` | `#l2-collector-badge`, `#l2-trading-badge` | Diagnostic | Sequence counter continuity ($seq_t = seq_{t-1} + 1$), stall threshold (5.0s) | PASS |
| 18 | **Strategy Arena Leaderboard** | `#/arena` | `#strategy-arena-table`, `.leaderboard-row` | Operational | 5 archetypes evaluated (TSMOM, Donchian, Breakout, Mean Rev, Vol Carry) | PASS |
| 19 | **Paper Trading Disclaimer** | `#/arena` | `#paper-trading-disclaimer`, `#exec-disabled-badge` | Safeguard | Live trading permanently disabled; 0 active trades | PASS |
| 20 | **Verified Reports Registry** | `#/research` (Tab: Reports) | `#reports-list-container`, `.report-card` | Operational | 11 peer-reviewed research reports with SHA-256 validation | PASS |
| 21 | **Contradiction Reconciliations Banner**| `#/research` (Tab: Reports) | `#contradiction-reconciliations-banner` | Governance | Explicitly notes directional claims refuted by net friction audit | PASS |
| 22 | **Source Markdown Modal Inspector** | `#/research` (Tab: Reports) | `#report-markdown-modal`, `.modal-close-btn` | Operational | In-app inspection of raw research markdown; Escape key closes | PASS |
| 23 | **Forecast Model Architecture Registry**| `#/research` (Tab: Models) | `#model-registry-table`, `.model-status-badge` | Governance | HAR-RS-DOW (`ACTIVE`), Chronos-2 (`INFERENCE NOT EXECUTED`), Hawkes (`DATA UNAVAILABLE`), Mamba (`REJECTED`) | PASS (Truthful status badges) |
| 24 | **Historical Regimes & Analog Explorer**| `#/research` (Tab: Analogs) | `#historical-analogs-panel`, `#analog-search-btn` | Operational | Nearest-neighbor historical volatility matching against 2022-2026 data | PASS |
| 25 | **Data Provenance & Integrity Card** | `#/research` (Tab: Provenance)| `#dataset-provenance-card`, `#hash-integrity-table`| Governance | Certified Canonical (`data/raw/ohlcv.parquet`) vs Quarantined datasets | PASS (5/5 Bit-Identical) |
| 26 | **Observation Bell Alert Hurdle** | Navbar (`NotificationBell`) | `#btn-notification-bell`, `#notification-empty-note` | Operational | Empty state clearly explains alerts muted under `NO_GO_NO_VALIDATED_EDGE` | PASS |
| 27 | **Settings & Sound Alert Modal** | Navbar (`SettingsButton`) | `#btn-settings-gear`, `#settings-modal` | Operational | Audio volume sliders, test alert trigger, persistent localStorage prefs | PASS |
| 28 | **WCAG 2.2 AA Focus & Mobile Nav** | Global (`styles.css` / `app.js`)| `:focus-visible`, `#btn-mobile-nav-toggle` | Accessibility | #00E5A8 glow focus rings, 24x24px tap targets, responsive hamburger menu | PASS (Mobile 375x812) |

---

## 3. Epistemic Integrity and Non-Execution Attestation

1. **Operating Posture:** All 28 features operate strictly under `OFFLINE_RESEARCH_ONLY`.
2. **Trading Execution:** Zero live trading, order placement, or broker execution APIs exist or are authorized.
3. **Model Honesty:**
   - Amazon Chronos-2 is explicitly documented as `INFERENCE NOT EXECUTED` (foundation challenger not loaded in production runtime).
   - Hawkes Jump Intensity is explicitly documented as `DATA UNAVAILABLE` (requires live Coinbase L2 WebSocket collector stream).
   - Mamba Selective SSM is explicitly documented as `REJECTED` (numerical drift / non-convergence under CPU quantization).
   - Directional return prediction is presented honestly as an unvalidated research hypothesis ($\text{AUC} \approx 0.504$, net negative expectation after 27/87 bps friction).
4. **Conclusion:** 28 of 28 features pass architectural visibility and governance verification without synthetic fabrication.
