# BTCognitive V33.4 — HTF Breakout Prospective Shadow Validation Handover

**Milestone:** V33.4 — HTF Breakout Prospective Shadow Validation  
**Date:** 2026-11-01  
**Git Branch:** `main` | **Commit SHA:** `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Operating Boundary:** Strict Read-Only Offline Research (`live_trading = DISABLED — ANALYSIS ONLY`)  
**Collector State:** `INACTIVE_AWAITING_MANAGEMENT_AUTHORIZATION` (Network access blocked)  

---

## 1. Executive Summary & Four Governed Decisions

| Decision Area | Governed Value | Operational Detail |
| :--- | :--- | :--- |
| **1. Research Experiment** | **`FROZEN_RESEARCH_PROTOCOL_PRE_REGISTERED`** | HTF breakout strategy and regime filter pre-registered and frozen for forward shadow validation |
| **2. Prospective Evidence** | **`FROZEN — 7/100 (CONFORMAL) / 0/100 (HTF SHADOW)`** | Conformal ledger frozen at 7/100; HTF shadow ledger pre-registered in separate append-only file |
| **3. Model Authorization** | **`OFFLINE_RESEARCH_ONLY`** | Analysis runtime locked at `ABSTAIN`; Q2 locked at `INSUFFICIENT_EVIDENCE` |
| **4. Live Trading** | **`DISABLED`** | Real execution permanently disabled; network collector strictly inactive |

---

## 2. Pre-Registered Protocol Specifications

Following the Manager's ruling, the forward validation protocol has been formally locked and pre-registered:

1. **Strategy Specification (Frozen):** `HTF_RANGE_EXPANSION_BREAKOUT`
   - Timeframe: 4-hour candles.
   - Lookback: 20-bar Donchian channel strictly shifted by 1 bar (`.shift(1)`).
   - Execution Fill: Open of immediately following candle (`nxt["open"]`).
   - Stop Loss: 20-bar Donchian low (`range_low_20_4h`).
   - Maximum Holding Horizon: 18 4h bars (72.0 hours).
   - Parameter Optimization: **Zero** (no tuning of channel length, stop distance, or holding time).
2. **Filter Specification (Frozen):** `MarketRegimeClassifier`
   - Timeframe: 1-hour candles.
   - Confirmation Hysteresis: Strict 3 consecutive closed 1h bars.
   - Suppression Rule: Trades are suppressed (`SUPPRESSED_CHOP`) if and only if macro regime is `CONSOLIDATION_RANGE`.
   - Execution Rule: Trades are executed in shadow (`EXECUTED_SHADOW`) if macro regime is `BULL_TREND`, `BEAR_TREND`, or `VOLATILITY_EXPANSION`.
3. **Execution Economics (Frozen):**
   - Modeled Cost: Fixed **26.0 bps** Binance VIP0 friction ($20\text{ commission} + 2\text{ spread} + 2\text{ base slip} + 2\text{ exp slip}$).
   - Position Sizing: **10% Notional Equity Allocation** ($E_t = E_{t-1} \times (1 + 0.10 \times r_t)$).
4. **Separate Append-Only Ledger:**
   - **Path:** `data/htf_prospective_shadow_ledger.jsonl`.
   - **Separation Invariant:** Strictly isolated from `data/prospective_forecast_ledger.jsonl` (which remains frozen at 7/100 conformal blocks).
   - **Dual Accounting:** Both executed signals and suppressed signals are recorded with counterfactual price excursion tracking.
5. **Dependence-Aware Statistical Inference:**
   - Evaluates paired daily portfolio return differences: $\Delta_t = r_{\text{filt}, t} - r_{\text{base}, t}$.
   - Primary Gate: Stationary block bootstrap ($B = 2,000$, mean block length $L = 3\text{ days}$), requiring $q_{0.025}(\bar{\Delta}) > 0.0\%$.
   - Secondary Gate: Diebold–Mariano with Harvey–Leybourne–Newbold (1997) finite-sample correction ($p < 0.025$).
6. **Pre-Registered Minimum Sample Size:**
   - Minimum hurdle: **$N = 100$ non-overlapping trade blocks** before confirmatory evaluation gate.
   - Strict non-peeking stopping rule: No interim tests prior to block 100.
7. **Operational Prerequisite & Network Lock:**
   - The market data collector is **`INACTIVE`** and network access remains **`BLOCKED`**.
   - No forward collection will commence without separate, explicit managerial authorization.

---

## 3. Deliverable Manifest

All deliverables are archived in [`research/reports/offline_mvp/20261101_330400_v33_04_htf_prospective_protocol/`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261101_330400_v33_04_htf_prospective_protocol/):
1. `v33_4_prospective_validation_protocol.md`
2. `v33_4_shadow_ledger_schema.json`
3. `v33_4_pre_registered_statistical_gates.md`
4. `v33_4_governance_and_collector_boundary.md`
5. `v33_4_protected_hash_verification.json`
6. `v33_4_manager_handover.md`
- **Engine Module:** [`engine/htf_prospective_shadow_runner.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/htf_prospective_shadow_runner.py)
- **Acceptance Test Suite:** `tests/test_v33_4_htf_prospective_protocol.py`

