# BTCognitive V35.0 — Strategy Lifecycle Decision: Formal Deprecation of HTF Breakout

**Milestone:** BTCognitive V35.0 — Research Product Finalization and Project Closure  
**Date:** 2026-11-03  
**Status:** COMPLETE / GOVERNED  
**Lead Author:** Agent 1 (Strategy Lifecycle Auditor)  
**Governed Decision:** `RETIRE_HTF_STRATEGY` | `DEPRECATED_RESEARCH_ONLY`

---

## 1. Executive Summary & Verification of V34.5 Results

In Milestone V34.5, the High-Timeframe (HTF) 4-hour Donchian breakout strategy was subjected to rigorous, causal point-in-time evaluation across all available Bitstamp observation periods (1,000 bars in early 2024 and 4,000 bars in mid-to-late 2026).

Agent 1 audited the experimental ledger, reproduced the trade-event logs, and re-verified all quantitative metrics:

| Verified Metric | Target Expectation | Empirical Observed Value | Audit Status |
| :--- | :--- | :--- | :--- |
| **Total Completed Causal Trades** | $\ge 15$ | **17 trades** (3 in 2024, 14 in 2026) | **CONFIRMED** |
| **Gross Expectancy (0 bps Friction)** | $> 0$ bps | **-102.9 bps per trade** (Sum: -1,748.6 bps) | **CONFIRMED (NEGATIVE)** |
| **Net Expectancy (70 bps Friction)** | $> 0$ bps | **-172.9 bps per trade** (Sum: -2,938.6 bps) | **CONFIRMED (NEGATIVE)** |
| **Overall Win Rate** | $\ge 50\%$ | **17.6%** (3 wins, 14 losses) | **CONFIRMED (SUB-20%)** |
| **Profit Factor (70 bps Friction)** | $\ge 1.50$ | **0.12** | **CONFIRMED (SUB-0.20)** |
| **Regime Difference Significance** | $p < 0.05$ | Welch $t = -0.199, \mathbf{p = 0.851}$ | **CONFIRMED (INSIGNIFICANT)** |
| **Stop-Loss Termination Rate** | $< 40\%$ | **82.4%** (14 of 17 trades stopped out) | **CONFIRMED (SEVERE CHOP)** |

---

## 2. Forensic Diagnosis of Strategy Failure

The empirical evidence confirms that the HTF breakout strategy suffers from two fatal structural flaws on Bitcoin spot markets:

1. **Pre-Cost Inherent Negative Drift (-102.9 bps Gross):**
   - The strategy is structurally unprofitable **before any exchange fees, spread, or slippage are deducted**.
   - Donchian channel breakouts on 4-hour candles in BTC spot markets are prone to liquidity exhaustion and immediate mean reversion.
2. **Execution Friction Amplification (-172.9 bps Net):**
   - Adding realistic 70 bps round-trip friction (50 bps fee + 20 bps spread/slippage) deepens average trade losses to -172.9 bps.
   - The win rate of 17.6% provides insufficient winning excursions to overcome the cumulative drag.
3. **Absence of Regime Conditioning ($p = 0.851$):**
   - Early claims of positive performance in early 2024 were an artifact of small-sample luck during the historic US Spot ETF approval run ($N=3$ trades).
   - In steady-state markets, `TRENDING_BULLISH` (-177.4 bps) and `VOLATILITY_EXPANSION` (-158.2 bps) produce statistically indistinguishable losses ($p = 0.851$).

---

## 3. Formal Strategy Lifecycle Governance Decision

In accordance with BTCognitive Prime Directive §1 and Research Boundaries:

1. **Retire from Active Research Recommendation:**
   - The HTF breakout strategy is formally retired.
   - It will **never** be presented as an active trade recommendation, shadow candidate, or production signal.
2. **Assign Status `DEPRECATED_RESEARCH_ONLY`:**
   - The strategy registry entry in `engine/regime_strategy_tournament.py` is updated to `status="DEPRECATED_RESEARCH_ONLY"`.
   - The analysis UI card in `web/app.js` is updated to display `HISTORICAL RESEARCH: HTF RANGE EXPANSION BREAKOUT (DEPRECATED)`.
3. **Preservation of Code, Provenance, and Artifacts:**
   - In accordance with provenance integrity rules, the strategy implementation (`engine/htf_setup_detector.py`), trade-event logs, and historical milestone reports are preserved in full.
   - No code is deleted or overwritten.
4. **No Automatic Promotion of Un-tested Alternatives:**
   - Mean-reversion or counter-trend strategies will **not** be automatically promoted to replace the breakout strategy.
   - Any new trading hypothesis must undergo independent pre-registration, formal walk-forward testing, and 100+ prospective blocks before consideration.

---

## 4. Final Sign-Off

The HTF breakout strategy development cycle is permanently **CLOSED**. BTCognitive will focus exclusively on its validated core competence: **BTC/USD Market Risk Intelligence, Volatility Modeling, and Excursion Analysis**.

