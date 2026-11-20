# BTCognitive V33.3 — Authoritative Existing Strategy Inventory & Classification

**Version:** 33.3.0  
**Date:** 2026-10-31  
**Operating Contract:** OFFLINE_RESEARCH_ONLY  
**Lead Orchestrator:** Antigravity  
**Repository Working Tree:** `BTCognitive/` on branch `main`  

---

## 1. Executive Summary & Audit Purpose

In strict accordance with the V33.3 Manager Ruling, all external model importation, new strategy conception, indicator proliferation, and ad-hoc mathematical engineering have been halted. This audit investigates exclusively the **strategies, models, heuristics, and tournament candidates already implemented** within the BTCognitive repository.

Every algorithmic decision mechanism that initiates, screens, or prices trade candidates across `models/authoritative_model_registry.py`, `research/v12_strategy_tournament_engine.py`, `engine/regime_strategy_tournament.py`, `engine/strategy_selection.py`, and `engine/smart_entry_engine.py` was systematically inspected from source code.

Each existing strategy is classified into one of six mutually exclusive governed statuses:
1. **Active:** Fully implemented and integrated into executable runtime routes.
2. **Research-Only:** Implemented with backtest/replay infrastructure, but explicitly barred from production authorization.
3. **Dormant:** Implemented in codebase but unselected by default routing engines.
4. **Rejected:** Previously evaluated against rigorous empirical hurdles and statistically rejected.
5. **Disconnected:** Implemented as a stand-alone engine or heuristic, but isolated from the central `decoupled_analysis_engine.py` 5-question trade authorization pipeline.
6. **Unverified:** Present in codebase or registry, but lacking authentic empirical trade logs or reproducible backtest data.

---

## 2. Comprehensive Inventory Table of Existing Strategies

| Strategy Identifier | Subsystem Source File | Family / Archetype | Claimed / Modeled Direction | Governed Classification | Audit Findings & Connection State |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`HTF_RANGE_EXPANSION_BREAKOUT`** | `research/v12_strategy_tournament_engine.py`<br>`engine/regime_strategy_tournament.py` | 4h / 20-bar Donchian Range Breakout | LONG (Spot) / Both (Perp) | **Active / Research-Only** | **Only strategy in BTCognitive with net positive EV** (+11.0 bps Inst., +14.6 bps Perp, PF 1.07–1.09, N=194). Evaluated in Tournament routes, but disconnected from `decoupled_analysis_engine.py`. |
| **`MTF_MOMENTUM_TREND`** | `research/v12_strategy_tournament_engine.py` | Multi-Timeframe EMA Trend Following | LONG / SHORT | **Active (Tournament)** | Evaluated in tournament; net negative under retail (-72.0 bps) and institutional (-10.8 bps). Breakeven cost threshold is only 7.8 bps. |
| **`VOL_COMPRESSION_BREAKOUT`** | `research/v12_strategy_tournament_engine.py` | Bollinger Bandwidth Squeeze Breakout | LONG / SHORT | **Active (Tournament)** | Low trade frequency (N=46). Net negative across retail (-72.9 bps) and institutional (-4.5 bps). Breakeven cost threshold 14.1 bps. |
| **`SHORT_HORIZON_MEAN_REVERSION`** | `research/v12_strategy_tournament_engine.py` | Oversold BB Bounce + Volume Gate | LONG | **Active (Tournament)** | Catastrophic failure across all fee tiers (-106.7 bps retail, -38.3 bps inst., PF 0.03–0.35). High adverse selection on BTC price breakdowns. |
| **`REGIME_ADAPTIVE_ROUTER`** | `research/v12_strategy_tournament_engine.py` | Dynamic Regime Meta-Selector | Dynamic | **Active (Tournament)** | Fails net economics (-95.6 bps retail, -15.0 bps inst.). Inherits losses of underlying trend and reversion sub-strategies. |
| **`TSMOM_DONCHIAN_24H_168H`** | `engine/regime_strategy_tournament.py` | 24h Breakout / 168h EMA Filter | LONG (Spot) | **Disconnected / Unverified** | Displays 7/10 diagnostic screen (70% win rate) in registry; however, recent attempts are hardcoded static fixtures, not a continuous live ledger. |
| **`ATR_VOLATILITY_BREAKOUT_12H`** | `engine/regime_strategy_tournament.py` | 12h ATR Volatility Expansion | LONG (Spot) | **Disconnected / Unverified** | Displays 8/10 diagnostic screen (80% win rate) in registry; outcome list is a fixed regression test fixture, not a live automated execution log. |
| **`RANGE_BOLLINGER_REVERSION_20H`** | `engine/regime_strategy_tournament.py` | 20h Bollinger Reversion | LONG (Spot) | **Rejected / Disconnected** | Fails 7/10 screen (60.0% TP rate); negative expectancy after transaction friction. Barred from qualification. |
| **`MEIE-IGNITION`** | `engine/strategy_selection.py`<br>`engine/smart_entry_engine.py` | Order Flow Momentum Ignition | LONG / SHORT | **Disconnected / Unverified** | Claims +32.2 bps EV in code; audit revealed this EV is a hardcoded linear heuristic formula, NOT an empirical backtest ledger. Completely disconnected from Analysis. |
| **`MEIE-ABSORPTION`** | `engine/strategy_selection.py`<br>`engine/smart_entry_engine.py` | Limit Order Absorption Exhaustion | LONG / SHORT | **Disconnected / Unverified** | Heuristic formula weights; unverified against empirical tick/order-book data; disconnected from 5-question engine. |
| **`MEIE-VACUUM`** | `engine/strategy_selection.py`<br>`engine/smart_entry_engine.py` | Liquidity Gap / Air-Pocket Run | LONG / SHORT | **Disconnected / Unverified** | Heuristic formula weights; unverified against authentic execution records; disconnected from Analysis. |
| **`MEIE-TOXICITY`** | `engine/strategy_selection.py`<br>`engine/smart_entry_engine.py` | Adverse Selection Toxic Flow Avoidance | Neutral / Abstain | **Disconnected / Unverified** | Operates as an adverse selection filter; highly valuable as a gating condition, but unverified as a standalone return generator. |
| **`MEIE-COMBINED`** | `engine/strategy_selection.py`<br>`engine/smart_entry_engine.py` | Multi-Factor Composite Microstructure | Dynamic | **Disconnected / Unverified** | Linear weighted combination of heuristic MEIE scores; disconnected from `decoupled_analysis_engine.py`. |
| **`directional-gbm-4lag-v1`** | `models/authoritative_model_registry.py` | 4-Lag LightGBM Return Sign Classifier | Binary Direction (+1 / -1) | **Rejected / Research-Only** | 53.28% OOS accuracy; Net EV = -13.07 bps/bar after 7 bps friction. Fails economic hurdle. Directional prediction permanently locked. |
| **`price-forecast-ridge-lagged`** | `models/authoritative_model_registry.py`<br>`engine/price_forecast_engine.py` | Regularized Ridge on Lagged Returns | Forecast Price ($P_{t+h}$) | **Rejected / Research-Only** | Walk-forward OOS evaluation confirms failure to outperform zero-drift random walk under Harvey-Leybourne-Newbold test ($p \ge 0.05$). |
| **`price-forecast-rolling-drift`** | `models/authoritative_model_registry.py`<br>`engine/price_forecast_engine.py` | 168h Rolling Historical Drift | Forecast Price ($P_{t+h}$) | **Rejected / Research-Only** | Fails HLN test against random walk ($p \ge 0.05$). Extrapolates past trends into mean-reverting regimes. |
| **`price-forecast-persistence-rw`** | `models/authoritative_model_registry.py` | Zero-Drift Persistence Random Walk | Benchmark Null | **Active (Research Baseline)** | Primary statistical null hypothesis benchmark for all price prediction attempts. Never rejected. |
| **`CHRONOS2_FOUNDATION`** | `engine/regime_strategy_tournament.py` | Amazon Chronos-2 Foundation Model | Zero-Shot Time Series | **Rejected / Quarantined** | Formally quarantined under V32.37 decision: Underperformed random-walk persistence on BTC-USD. |
| **`FUNDING_DISLOCATION_STRATEGY`** | `research/reports/v32_79A/`<br>`data/raw/funding.parquet` | Funding Dislocation Arbitrage | LONG / SHORT | **Rejected / Quarantined** | Formally quarantined under V32.80B decision: Unresolved source lineage conflict between Binance and local datasets. Research permanently frozen. |
| **`HAR-RS-DOW-v1.0`** | `models/authoritative_model_registry.py` | Heterogeneous Autoregressive Semivariance | Volatility / Risk Envelope | **Active / Production-Baseline** | Approved baseline volatility risk engine. Invariant: Measures variance and excursion bounds; strictly non-directional. |

---

## 3. Subsystem Breakdown & Architecture Allocation

The existing strategies within BTCognitive are split across three primary subsystems:

1. **Subsystem 1: Macro & Swing Strategy Tournament (`research/v12_strategy_tournament_engine.py` & `api/routes_tournament.py`)**
   - Implements multi-day and multi-hour swing strategies evaluated across 41,273 hourly bars.
   - Contains the only empirically tested positive-expectancy strategy in the entire codebase: `HTF_RANGE_EXPANSION_BREAKOUT`.
   - Accessible via tournament API endpoints (`/api/tournament/status`, `/api/tournament/replay`, `/api/tournament/setup/{id}`).

2. **Subsystem 2: Microstructure Execution & Entry Engine (MEIE) (`engine/strategy_selection.py` & `engine/smart_entry_engine.py`)**
   - Implements 5 high-frequency order-flow archetypes (`MEIE-IGNITION`, `MEIE-ABSORPTION`, `MEIE-VACUUM`, `MEIE-TOXICITY`, `MEIE-COMBINED`).
   - Relies on VPIN, Hawkes jump intensity, and OFI.
   - **Crucial Finding:** The expected value (+32.2 bps) reported in MEIE documentation is generated from a synthetic linear formula combining indicator thresholds, NOT an empirical execution backtest.

3. **Subsystem 3: Central Decoupled Analysis & Trade Authorization Engine (`engine/decoupled_analysis_engine.py`)**
   - Implements the 5-Question trade authorization gate (Q1 Regime, Q2 Directional, Q3 Entry Location, Q4 Economics, Q5 Confidence).
   - Currently, Q4 evaluates a generic static setup (empirical win rate 33.5%, 2.0R/1.0R) rather than querying the tournament or MEIE strategies.
   - **Conclusion:** A major structural disconnection exists between the evaluated strategies and the decoupled analysis engine.

