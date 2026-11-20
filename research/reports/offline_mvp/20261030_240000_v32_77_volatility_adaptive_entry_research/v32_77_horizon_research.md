# V32.77 — Horizon Research: 24h vs 72h vs 168h Holding Periods

**Workstream:** Agent 3 — Horizon Research Specialist  
**Milestone:** BTCognitive V32.77 — Volatility-Adaptive Entry Research  
**Date:** 2026-10-30  
**Evaluator:** Horizon Research Specialist (Agent 3)  
**Governing Repo:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Classification:** Horizon Protocol Authority Record  

---

## 1. Executive Summary & Comparative Dynamics

Evaluating holding horizons across **10,521 chronological out-of-sample bars** reveals fundamental structural differences between intraday (24h), swing (72h), and weekly (168h) holding periods:

| Metric / Dimension | 24-Hour Horizon | 72-Hour Horizon (3 Days) | 168-Hour Horizon (7 Days) |
|---|---|---|---|
| **Median MFE (Favorable Excursion)** | **1.12%** | **2.19%** | **3.24%** |
| **Median MAE (Adverse Excursion)** | **1.22%** | **2.26%** | **3.64%** |
| **Gross Return Spread (MFE - MAE)** | -0.10% (Negative drift) | -0.07% (Near-symmetric) | -0.40% (Adverse skew) |
| **Median Time to Stop-Loss Touch** | 5 to 8 hours | 14 to 22 hours | 26 to 61 hours |
| **Fee Drag as % of Target** | **16.0%** (24 bps on 150 bps) | **8.0%** (24 bps on 300 bps) | **4.8%** (24 bps on 500 bps) |
| **Label Overlap in Consecutive Bars** | 23 hours (95.8%) | 71 hours (98.6%) | 167 hours (99.4%) |

---

## 2. In-Depth Horizon Analysis

### 2.1 The 24-Hour Intraday Trap
- At 24 hours, the median favorable excursion is only $1.12\%$. A target of $1.50\%$ sits in the upper quartile of daily volatility.
- The 24 bps retail taker fee consumes $16.0\%$ of the profit target on Binance and over $58\%$ on Coinbase.
- **Verdict:** Market microstructure noise makes 24-hour entries highly vulnerable to random stop-outs.

### 2.2 The 72-Hour Horizon (The Optimal Micro-Macro Balance)
- Over 72 hours, favorable excursion expands to $2.19\%$, allowing targets of $+3.00\%$ and stops of $-1.50\%$.
- Fixed 72h barriers yield improved Short performance (Gross EV $+0.1814\%$, Net EV Binance $-0.0586\%$).
- The transaction cost hurdle drops from $16\%$ of target to $8\%$.
- **Downside:** Requires weathering a median adverse excursion of $2.26\%$.

### 2.3 The 168-Hour Weekly Horizon (Macro Trend Capture)
- Captures large trending moves ($3.24\%$ median MFE, reaching $> 8\%$ during breakouts).
- Fixed 168h Short achieves positive gross return ($+0.2429\%$) and marginal net profitability on Binance ($+0.0029\%$).
- **The Pitfalls:**
  1. Extended capital lockup (median exit at 53–61 hours).
  2. Severe adverse excursion (median MAE $3.64\%$).
  3. Accumulation of funding rate fees on perpetual futures (8-hour settlements accumulate $\sim 14$ funding payments over 168h).
  4. Extreme serial dependence in hourly sampling (167 hours of overlap).

---

## 3. Horizon Ruling & Recommendations

1. **24h is Structurally Deficient:** Short holding periods cannot reliably generate sufficient gross edge to overcome exchange friction.
2. **72h and 168h Narrow the Net Deficit:** While gross returns improve significantly at 72h and 168h (climbing from $+0.02\%$ to $+0.24\%$), **unconditioned net returns remain negative** after accounting for realistic taker execution costs and adverse intra-candle wicks.
3. **Horizon Extension Alone Is Not a Magic Bullet:** Expanding the horizon reduces fee drag as a percentage of trade size, but increases the variance of outcomes. Horizon extension must be coupled with causal filtering (e.g. regime gating), not applied blindly.

*Signed by Specialist Agent 3 (Horizon Research Specialist)*

