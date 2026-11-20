# BTCognitive V33.3C — Sequential Portfolio Simulation & Equity Comparison

**Milestone:** V33.3C — HTF Strategy Final Evidence Reconciliation  
**Date:** 2026-10-31  
**Target:** Chronological Equity Curve, Drawdown Duration, Turnover, and Exposure Comparison  
**Simulation Engine:** `scripts/qa/v33_3c_final_reconciliation.py`  
**Summary Source:** `v33_3c_simulation_summary.json`  

---

## 1. Simulation Architecture & Contract Integrity

To address the Manager's mandate that *"mean return per trade is not the same as portfolio return"*, a sequential portfolio simulation was executed under identical baseline and filtered conditions:

- **Starting Capital:** \$100,000.00 USD cash baseline.
- **Execution Cost:** Strict Binance VIP0 26.0 bps modeled friction ($20\text{ commission} + 2\text{ spread} + 2\text{ base slip} + 2\text{ expansion slip}$).
- **Concurrency & Overlapping Position Audit:** A chronological scan of all 194 trade entry and exit timestamps proved there are **0 overlapping trades**. Every trade is strictly sequential (`in_pos` state lock prevents concurrent entries).
- **Two Governed Sizing Modes:**
  1. **100% Notional Equity Allocation:** Full compounding ($E_t = E_{t-1} \times (1 + 1.0 \times r_t)$), where 100% of available portfolio equity is allocated to BTC at each breakout.
  2. **10% Notional Equity Allocation:** Standard BTCognitive portfolio risk allocation ($E_t = E_{t-1} \times (1 + 0.10 \times r_t)$), where 10% of portfolio equity is exposed to BTC spot and 90% remains in cash.

---

## 2. Chronological Portfolio Performance Summary

### Table 1: Out-of-Sample Performance Comparison (2024–2026, $N_{\text{base}}=119, N_{\text{filt}}=64$)

| Performance Dimension | Baseline (100% Alloc) | Filtered (100% Alloc) | Baseline (10% Alloc) | Filtered (10% Alloc) | Filter Advantage (100% Alloc) | Filter Advantage (10% Alloc) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Starting Equity** | \$100,000.00 | \$100,000.00 | \$100,000.00 | \$100,000.00 | — | — |
| **Final Equity** | \$94,242.47 | **\$105,491.81** | \$100,225.42 | **\$101,009.13** | **+\$11,249.34** | **+\$783.71** |
| **Cumulative Return** | **−5.76%** | **+5.49%** | **+0.23%** | **+1.01%** | **+11.25 pp** | **+0.78 pp** |
| **Annualized Return (CAGR)** | **−2.15%** | **+1.98%** | **+0.08%** | **+0.37%** | **+4.13 pp** | **+0.29 pp** |
| **Maximum Drawdown (MDD)** | **47.35%** | **28.35%** | **5.88%** | **3.19%** | **−40.1% MDD reduction** | **−45.7% MDD reduction** |
| **Total Exposure Time** | 8,520 hours | 4,656 hours | 8,520 hours | 4,656 hours | **−3,864 hours (−45.3%)** | **−3,864 hours (−45.3%)** |
| **Exposure Percentage** | 35.69% | 19.50% | 35.69% | 19.50% | **−16.19 pp in market** | **−16.19 pp in market** |
| **Total Turnover** | \$27.69M | \$12.79M | \$2.42M | \$1.28M | **−53.8% turnover** | **−47.1% turnover** |
| **Sharpe Ratio** | 0.045 | **0.196** | 0.045 | **0.196** | **+0.151** | **+0.151** |
| **Sortino Ratio** | 0.108 | **0.498** | 0.108 | **0.498** | **+0.390** | **+0.390** |

### Table 2: Full-Period Performance Comparison (2022–2026, $N_{\text{base}}=194, N_{\text{filt}}=110$)

| Performance Dimension | Baseline (100% Alloc) | Filtered (100% Alloc) | Baseline (10% Alloc) | Filtered (10% Alloc) | Filter Advantage (100% Alloc) | Filter Advantage (10% Alloc) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Starting Equity** | \$100,000.00 | \$100,000.00 | \$100,000.00 | \$100,000.00 | — | — |
| **Final Equity** | \$100,553.99 | **\$171,809.04** | \$101,686.73 | **\$106,613.62** | **+\$71,255.05** | **+\$4,926.89** |
| **Cumulative Return** | **+0.55%** | **+71.81%** | **+1.69%** | **+6.61%** | **+71.26 pp** | **+4.93 pp** |
| **Annualized Return (CAGR)** | **+0.12%** | **+12.23%** | **+0.36%** | **+1.37%** | **+12.11 pp** | **+1.02 pp** |
| **Maximum Drawdown (MDD)** | **47.35%** | **28.35%** | **5.88%** | **3.19%** | **−40.1% MDD reduction** | **−45.7% MDD reduction** |
| **Total Exposure Time** | 13,720 hours | 7,928 hours | 13,720 hours | 7,928 hours | **−5,792 hours (−42.2%)** | **−5,792 hours (−42.2%)** |
| **Exposure Percentage** | 33.36% | 19.27% | 33.36% | 19.27% | **−14.08 pp in market** | **−14.08 pp in market** |
| **Total Turnover** | \$42.70M | \$31.53M | \$3.95M | \$2.29M | **−26.2% turnover** | **−42.0% turnover** |
| **Sharpe Ratio** | 0.141 | **0.635** | 0.141 | **0.635** | **+0.494** | **+0.494** |
| **Sortino Ratio** | 0.309 | **1.591** | 0.309 | **1.591** | **+1.282** | **+1.282** |

---

## 3. Analysis of Portfolio Risk Dynamics

1. **Drawdown Compression:**
   Under 100% full compounding, the baseline strategy suffers an excruciating peak-to-trough drawdown of **47.35%**, experiencing extended periods of negative equity.  
   The regime filter compresses this drawdown to **28.35%**, an absolute reduction of **19.0 percentage points** (40.1% relative reduction).  
   Under BTCognitive's institutional 10% notional equity allocation, maximum drawdown drops from **5.88% down to 3.19%** (a 45.7% relative reduction), well within acceptable excursion limits.
2. **Turnover & Capital Efficiency:**
   In the Out-of-Sample window, the baseline traded \$27.69M of notional volume to produce a −\$5,758 loss. The filtered configuration required only \$12.79M of turnover to generate a +\$5,492 profit. Capital efficiency improved substantially while reducing cumulative exchange fee drag.
3. **Exposure Minimization:**
   The filter reduced market exposure time from 35.69% to 19.50% in the OOS era, allowing the portfolio to remain in cash for 80.5% of the time, thereby avoiding catastrophic tail drawdowns during adverse regimes.

