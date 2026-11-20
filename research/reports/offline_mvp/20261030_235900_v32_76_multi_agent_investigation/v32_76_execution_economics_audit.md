# V32.76 — Execution Economics & Market Microstructure Audit Report

**Workstream:** Agent 4 — Market Microstructure and Cost Specialist  
**Milestone:** BTCognitive V32.76 — Multi-Agent Research Integrity & Conditional Entry Investigation  
**Date:** 2026-10-30  
**Evaluator:** Microstructure & Execution Specialist (Agent 4)  
**Governing Repo:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Classification:** Microstructure Governance Authority Record  

---

## 1. Executive Summary & Cost Model Audit

| Cost Tier | Implemented Round-Trip Friction | Empirical Validity | Trading Viability |
|---|---|---|---|
| **SCEN_1_BINANCE_VIP0** | **24.0 bps** (10 bps fee $\times 2$ + 2 bps spread $\times 2$) | **VERIFIED RETAIL TIER** | All tested filters produce negative net EV (-16 to -28 bps). |
| **SCEN_2_COINBASE_ADVANCED** | **87.0–127.0 bps** (40–60 bps fee $\times 2$ + 3.5 bps spread $\times 2$) | **VERIFIED RETAIL TIER** | Severe negative drift (-79 to -93 bps per trade). |
| **SCEN_3_PASSIVE_MAKER** | **4.0 bps** (2 bps rebate/fee $\times 2$) | **UNVERIFIED / UNPROVEN** | Assumes 100% fill rate and zero adverse selection. Flawed. |
| **SCEN_4_ZERO_COST** | **0.0 bps** (Academic theoretical ceiling) | **HYPOTHETICAL ONLY** | Even with 0 fees, best gross edge was only +7.6 bps. |
| **SCEN_5_STRESSED_SLIPPAGE** | **174.0 bps** (High volatility stress test) | **EXTREME STRESS** | Illustrates catastrophic fee drag during market panics. |

---

## 2. Market Microstructure Mechanics: The Five Friction Sources

### 2.1 Exchange Fees (Explicit Cash Drain)
- **Binance VIP 0 Spot:** 10.0 bps taker fee per side = 20.0 bps round trip.
- **Coinbase Advanced Retail:** 40.0 to 60.0 bps taker fee per side = 80.0 to 120.0 bps round trip.
- **Impact:** On a 24-hour trade with a 1.5% target (+150 bps) and 0.75% stop (-75 bps), retail Coinbase fees consume **58% of the gross profit** and amplify the stop-loss by **116%**.

### 2.2 Bid-Ask Spread (Crossing the Spread)
- On BTC/USD, median half-spread during normal liquidity is $1.5 \text{ to } 2.5\text{ bps}$ ($3.0 \text{ to } 5.0\text{ bps}$ full spread).
- Taker orders must cross the spread at entry and exit, costing an unavoidable $\sim 4.0\text{ bps}$.

### 2.3 Market Impact & Slippage
- When stop-loss orders are triggered at high velocity, prices frequently slip past the stop price.
- In `engine/execution_cost_model.py`, slippage is modeled at 2.0 to 5.0 bps under normal conditions, rising to 20.0+ bps during volatility spikes.

### 2.4 The Passive Maker Order Fallacy (SCEN_3 Dissection)
Many academic backtests assume orders are filled as **passive makers** to claim low fees or rebates. This assumption is **fatally flawed** in live trading due to two microstructure phenomena:
1. **Queue Position & Non-Execution:** A limit order placed at the inside quote will not execute unless market orders exhaust the prevailing queue. In strong breakouts, price moves away without filling the order, causing **100% missed winning trades**.
2. **Adverse Selection (The Winner's Curse):** A limit order is disproportionately filled when informed traders cross the book with large orders, pushing the market immediately against the position. You get filled on trades that continue running against you, but get left behind on trades that take off.
**Agent 4 Ruling:** `SCEN_3_PASSIVE_MAKER` must be labeled **`UNVERIFIED_AND_UNREALISTIC`** in all reports. No strategy may claim viability based on maker execution without millisecond Level 3 queue simulation.

### 2.5 Holding Costs & Perpetual Funding
- For Spot BTC/USD, holding costs are 0 (unless borrowing on margin).
- For Perpetual Futures (e.g. Binance BTCUSDT Perp), funding rates settle every 8 hours. Analysis of `data/raw/binance_funding_2022_2026.parquet` shows a median annualized funding rate of $+11.2\%$ (longs pay shorts). Holding a 24-hour long position costs an additional $\approx 3.1\text{ bps}$ in funding fees.

---

## 3. The Economic Hurdle: Minimum Win Rate Required for Profitability

Under the standard 2:1 geometry (TP = $+1.50\% = +150\text{ bps}$, SL = $-0.75\% = -75\text{ bps}$), the net expected value per trade is:
$$\text{EV}_{\text{net}} = p \cdot (\text{TP} - C) + (1 - p) \cdot (-\text{SL} - C) = p \cdot (\text{TP} + \text{SL}) - \text{SL} - C$$
where $C$ is the total round-trip friction in basis points.

Setting $\text{EV}_{\text{net}} = 0$ yields the **Break-Even Win Rate ($p^*$)**:
$$p^* = \frac{\text{SL} + C}{\text{TP} + \text{SL}} = \frac{75 + C}{225}$$

| Scenario | Round-Trip Cost ($C$) | Required Break-Even Win Rate ($p^*$) | Observed Win Rate (Candidate B) | Net Expected Return |
|---|---|---|---|---|
| **Zero Cost (SCEN 4)** | 0.0 bps | **33.33%** | 34.42% | +0.0762% (+7.6 bps) |
| **Passive Maker (SCEN 3)** | 4.0 bps | **35.11%** | 34.42% | -0.0156% (-1.6 bps) |
| **Binance VIP 0 (SCEN 1)** | 24.0 bps | **44.00%** | 34.42% | **-0.1638% (-16.4 bps)** |
| **Coinbase Advanced (SCEN 2)** | 87.0 bps | **72.00%** | 34.42% | **-0.7938% (-79.4 bps)** |

### Economic Conclusion:
To trade profitably on Binance VIP0, an entry filter must lift the TP hit rate from the random baseline of $33.3\%$ to **at least $44.0\%$** (+10.7 percentage points of pure alpha). On Coinbase Advanced, it must lift it to **$72.0\%$** (+38.7 percentage points).
The best observed filter in V32.74 achieved only $34.42\%$ (a marginal $+1.1\%$ lift over random walk).
**Conclusion:** The entry filters tested are **economically unviable by a factor of 10**.

*Signed by Specialist Agent 4 (Market Microstructure & Cost Specialist)*

