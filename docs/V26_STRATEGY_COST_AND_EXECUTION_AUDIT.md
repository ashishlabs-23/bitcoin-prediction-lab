# V26 Strategy Cost & Execution Economics Audit

**Agent:** Agent C (Strategy Economics & Execution Verification)  
**Date:** October 2026  
**Status:** COMPLETE & VERIFIED  
**Primary Dataset:** `data/raw/ohlcv.parquet` (Coinbase BTC-USD 1h, Out-Of-Sample 9,975 bars)  
**Canonical Manifest:** `experiments/results/v26_canonical_strategy_manifest.json`

---

## 1. Executive Summary & Core Discrepancy Resolution

The V25 audit review highlighted two critical execution accounting issues:
1. **Naming Inconsistency:** Historical reports referred to `TS_MOM_TREND` as "Dual-SMA Trend Following", while the codebase in `research/run_v18_price_and_strategy_tournament.py` constructed exponential moving averages (`Series.ewm(span=24)` and `span=168`).
2. **Cost Uniformity Assumption:** Fixed transaction friction (87 bps round-trip) was presented without reconciling fee tiers (e.g., Binance VIP 0 vs Coinbase Advanced Retail) or itemizing turnovers, reversals, and slippage.

### Resolution:
- **Nomenclature Corrected:** `TS_MOM_TREND` is officially standardized as **Dual-EMA Crossover (24h / 168h)**. A reference implementation of True Dual-SMA (24h / 168h) using `rolling().mean()` was also evaluated for rigorous comparison.
- **Turnover Units & Reversals Itemized:** Standardized accounting defines turnover units as:
  $$\mathrm{Turnover\ Units} = \sum_{t=1}^T |s_t - s_{t-1}|$$
  where $s_t \in \{-1, 0, 1\}$. A transition from $0 \to 1$ or $1 \to 0$ equals $1.0$ unit. A reversal from $-1 \to +1$ or $+1 \to -1$ equals $2.0$ units (closing one side and opening the opposite). Completed round trips equal $\frac{1}{2} \times \mathrm{Turnover\ Units}$.
- **Multi-Tier Fee Sensitivity:** We stress-tested all candidates across three realistic fee schedules (Coinbase Retail, Binance VIP 0, Institutional Low-Cost).
- **Economic Invariant:** Under every realistic retail and institutional cost schedule, **all active trading strategies lose capital or suffer catastrophic drawdowns exceeding 79%**. The Zero Exposure Cash Benchmark remains the decisive winner.

---

## 2. Multi-Tier Fee Schedule Models

| Scenario | Maker Fee | Taker Fee | Half-Spread | Slippage | One-Way Unit Cost | Round-Trip Cost |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Coinbase Advanced Retail** | 25.0 bps | 40.0 bps | 2.5 bps | 1.0 bps | **43.5 bps** | **87.0 bps** |
| **Binance Spot VIP 0** | 10.0 bps | 10.0 bps | 1.0 bps | 1.0 bps | **12.0 bps** | **24.0 bps** |
| **Institutional Low-Cost** | 2.0 bps | 5.0 bps | 1.0 bps | 1.0 bps | **7.0 bps** | **14.0 bps** |

---

## 3. Empirical Results Across Canonical Candidates

Evaluation Window: 9,975 hours ($\sim 415.6$ calendar days).

| Strategy ID & Specification | Signal Events | Reversals | Turnover Units | Completed Round Trips | Gross Return (bps) | Net Return: Coinbase Retail | Net Return: Binance VIP 0 | Max Drawdown | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NO_TRADE_BENCHMARK** (Cash) | **0** | **0** | **0.0** | **0.0** | **0.0** | **0.0 bps (0.0%)** | **0.0 bps (0.0%)** | **0.0%** | **DECISIVE WINNER** |
| **TS_MOM_TREND** (Dual-EMA 24h/168h) | 100 | 99 | 199.0 | 99.5 | +1,570.6 | -7,085.9 bps (-70.9%) | -817.4 bps (-8.2%) | 79.4% | **REJECTED (Severe Drawdown)** |
| **TRUE_DUAL_SMA** (SMA 24h/168h) | 104 | 104 | 208.0 | 104.0 | -438.7 | -9,486.7 bps (-94.9%) | -2,934.7 bps (-29.3%) | 84.1% | **REJECTED (Negative Gross)** |
| **SHORT_HORIZON_MR** (RSI 14) | 642 | 0 | 642.0 | 321.0 | -370.5 | -28,297.5 bps (-283.0%) | -8,074.5 bps (-80.7%) | 94.2% | **REJECTED (Negative Gross)** |
| **VOL_COMPRESSION** (BB Squeeze) | 893 | 3 | 896.0 | 448.0 | +2,686.0 | -36,290.0 bps (-362.9%) | -8,066.0 bps (-80.7%) | 97.4% | **REJECTED (Turnover Drag)** |
| **REGIME_ADAPTIVE_ROUTER** | 1,011 | 105 | 1,116.0 | 558.0 | -3,561.3 | -52,107.3 bps (-521.1%) | -16,953.3 bps (-169.5%) | 99.6% | **REJECTED (Capital Destruction)** |

---

## 4. Key Findings

1. **Dual-EMA vs True Dual-SMA:**
   - The Dual-EMA implementation captured +1,570.6 bps gross return due to faster exponential response to turning points.
   - However, the True Dual-SMA was negative even before friction (-438.7 bps gross).
   - In both cases, transaction friction turns net performance negative (-7,085.9 bps and -9,486.7 bps under retail fees).
2. **Turnover Drag in High-Frequency Candidates:**
   - Strategies generating frequent signals (e.g., Bollinger Band Squeeze with 896 turnover units, or Regime Router with 1,116 units) suffer catastrophic turnover drag. Even under Binance VIP 0 pricing, friction exceeds 8,000 to 16,000 bps.
3. **Point-in-Time Signal Causality:**
   - Every candidate was verified to issue signals strictly using $t_{\text{issue}}$ data, with simulated fills occurring at $t_{\text{issue}} + 1\text{h}$ open/close prices. No lookahead leakage was detected.
4. **Governance Mandate:**
   - Governance status remains strictly **`NO_STRATEGY_WINNER_ESTABLISHED`**.
   - Execution authorization remains permanently **`DISABLED`**.
