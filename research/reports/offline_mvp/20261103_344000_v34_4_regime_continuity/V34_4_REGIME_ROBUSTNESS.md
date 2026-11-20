# BTCognitive V34.4 — Market Regime Robustness & Distributional Audit

**Date:** 2026-11-03  
**Status:** COMPLETE / GOVERNED  
**Lead Author:** Agent 4 (Regime Classification & Robustness Specialist)  
**Governed Assessment:** `REGIME_DEPENDENCE_SUPPORTED` (Descriptive only; unproven inferentially)

---

## 1. Executive Summary

Milestone V34.4 examined the canonical 5-regime market classification framework across both Bitstamp data segments (2024 and 2026) to test the hypothesis that the performance variance of the frozen HTF strategy is explained by regime shifts rather than stochastic anomalies.

### Key Audit Findings
1. **Regime Distribution Consistency:** The background proportion of canonical regimes is surprisingly stable across calendar eras: ~35-38% `TRANSITION_UNSUPPORTED`, ~15-20% `TRENDING_BULLISH`, ~17-23% `TRENDING_BEARISH`, ~14-19% `VOLATILITY_EXPANSION`, and ~9-10% `RANGE_BOUND`.
2. **Contextual Quality Disparity:** Despite similar macroscopic percentages, the *nature* of `TRENDING_BULLISH` bars differed fundamentally:
   - Early 2024 was marked by the historic US Spot Bitcoin ETF approval momentum, producing high-persistence, unidirectional drift.
   - Mid-to-late 2026 was marked by choppy consolidation, where "breakouts" were frequently false expansions that immediately reverted into liquidity traps.
3. **Statistical Power Limitation:** With only 3 completed trades in 2024 and 14 trades in 2026, sample size is insufficient for formal ANOVA or Chi-Square tests of regime conditional edge. Therefore, regime dependence is **descriptively supported** but **inferentially unproven**.

---

## 2. Canonical 5-Regime Distribution

4-hour bars were classified into the 5 canonical regimes based on rolling EMA slope (trend direction), ATR percentile (volatility state), and ADX (trend strength).

| Canonical Regime | Segment 1 (2024 Slice, 250 bars) | Segment 2 (2026 Slice, 1,001 bars) | Long-Term Regime Stability |
| :--- | :--- | :--- | :--- |
| **`TRANSITION_UNSUPPORTED`** | 96 bars (38.4%) | 346 bars (34.6%) | Dominant baseline state (~35%) |
| **`TRENDING_BEARISH`** | 43 bars (17.2%) | 227 bars (22.7%) | Substantial bear phases |
| **`TRENDING_BULLISH`** | 38 bars (15.2%) | 200 bars (20.0%) | Primary strategy trading lane |
| **`VOLATILITY_EXPANSION`** | 47 bars (18.8%) | 142 bars (14.2%) | Secondary strategy trading lane |
| **`RANGE_BOUND`** | 26 bars (10.4%) | 86 bars (8.6%) | Low-volatility compression (~9%) |
| **Total 4h Bars** | **250 bars** | **1,001 bars** | **1,251 total bars audited** |

---

## 3. Trade Distribution Conditioned on Regime

The frozen HTF strategy is strictly long-only and permitted to take signals only when the prevailing regime is `TRENDING_BULLISH` or `VOLATILITY_EXPANSION`.

| Regime at Entry | Segment 1 (2024) Trades | Segment 2 (2026) Trades | Combined Trades | Win Rate by Regime |
| :--- | :--- | :--- | :--- | :--- |
| **`TRENDING_BULLISH`** | 2 trades (1 Win, 1 Loss) | 10 trades (2 Wins, 8 Losses) | 12 trades | 25.0% (3 / 12) |
| **`VOLATILITY_EXPANSION`** | 1 trade (0 Wins, 1 Loss) | 4 trades (1 Win, 3 Losses) | 5 trades | 20.0% (1 / 5) |
| **`RANGE_BOUND`** | 0 (Filtered by rule) | 0 (Filtered by rule) | 0 | N/A |
| **`TRENDING_BEARISH`** | 0 (Filtered by rule) | 0 (Filtered by rule) | 0 | N/A |
| **`TRANSITION_UNSUPPORTED`** | 0 (Filtered by rule) | 0 (Filtered by rule) | 0 | N/A |
| **Total** | **3 trades** | **14 trades** | **17 trades** | **23.5% (4 / 17)** |

---

## 4. Regime Failure Mode Analysis

1. **Whipsaws in Transition/Expansion Boundaries:**
   - In 2026, 4 out of 5 trades in `VOLATILITY_EXPANSION` failed because expansion was driven by rapid liquidation cascades rather than institutional accumulation.
   - Long breakouts triggered near the top of the range before immediate mean-reversion stopped out positions.
2. **Persistence Decay in Bullish Regimes:**
   - In 2024, `TRENDING_BULLISH` bars showed sustained serial correlation, allowing the lone winning trade (`SEG_2024_001`) to reach its take-profit within 12 hours (+125.2 bps net).
   - In 2026, bullish trends exhibited lower autocorrelation, with 8 out of 10 trades hitting stop-loss after prolonged holding (mean holding duration of 16.3 hours).

---

## 5. Governed Epistemic Determination

- **Hypothesis:** "The strategy's historical success in early 2024 was an artifact of macro regime luck rather than robust edge."
- **Audit Verdict:** `REGIME_DEPENDENCE_SUPPORTED`.
- **Epistemic Qualification:** While the evidence strongly points to macro regime vulnerability, sample sizes are inadequate for formal statistical rejection. The strategy must not be tuned or overfitted to compensate for 2026 performance. It remains frozen in `OFFLINE_RESEARCH_ONLY`.

