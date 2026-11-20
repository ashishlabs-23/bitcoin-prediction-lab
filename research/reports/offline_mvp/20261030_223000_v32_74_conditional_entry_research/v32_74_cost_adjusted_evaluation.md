# V32.74 — Cost-Adjusted Economic Evaluation Report

**Milestone:** V32.74 — Conditional Entry Quality Research  
**Date:** 2026-10-30  
**Classification:** Microstructure & Execution Economics | OFFLINE_RESEARCH_ONLY  
**Cost Scenarios Source:** `research/entry_intelligence/cost_sensitivity.py`

---

> [!CAUTION]
> **Adverse Selection Warning:**
> `SCEN_3_PASSIVE_MAKER` assumes passive limit order fills with a 6.0 bps adverse selection haircut.
> In real markets, limit orders suffer from the **Winner's Curse**: limit orders are filled primarily when price is violently breaking against the order, and fail to fill when price moves favorably towards the target.
> `SCEN_3_PASSIVE_MAKER` is **UNVERIFIED RESEARCH ONLY** and must never be treated as verified production cost.

---

## 1. The Five Canonical Execution Scenarios

| Scenario ID | Name & Description | Maker / Taker Fee | Half-Spread | Slippage | Adverse Selection | Total Round-Trip Cost | Status |
|---|---|---|---|---|---|---|---|
| **`SCEN_0`** | `FRICTIONLESS` (Theoretical upper bound) | 0.0 bps / 0.0 bps | 0.0 bps | 0.0 bps | 0.0 bps | **0.0 bps (0.00%)** | Theoretical Bound |
| **`SCEN_1`** | `BINANCE_VIP0` (Standard retail spot tier) | 10.0 bps / 10.0 bps | 1.0 bps | 1.0 bps | 0.0 bps | **24.0 bps (0.24%)** | **Verified Production Baseline** |
| **`SCEN_2`** | `COINBASE_ADV` (Retail taker conservative) | 25.0 bps / 40.0 bps | 2.5 bps | 1.0 bps | 0.0 bps | **87.0 bps (0.87%)** | **Verified Conservative** |
| **`SCEN_3`** | `PASSIVE_MAKER` (Hypothetical limit orders) | 15.0 bps / 15.0 bps | 0.0 bps | 0.0 bps | 6.0 bps | **36.0 bps (0.36%)** | **UNVERIFIED RESEARCH** |
| **`SCEN_4`** | `STRESSED_VOL` (Market crisis / liquidity shock) | 40.0 bps / 80.0 bps | 10.0 bps | 15.0 bps | 12.0 bps | **197.0 bps (1.97%)** | **Stress Test Only** |

---

## 2. Complete Cost Matrix Across All Filters (OOS Test Set)

### 2.1 LONG Direction Net Expected Value (% per trade)

| Filter Name | Gross EV (`SCEN_0`) | Net EV `SCEN_1` (Binance) | Net EV `SCEN_2` (Coinbase) | Net EV `SCEN_3` (Passive [UNVERIFIED]) | Net EV `SCEN_4` (Stressed Vol) |
|---|---|---|---|---|---|
| `UNIFORM_BASELINE` | +0.0255% | -0.2145% | -0.8445% | -0.3345% | -1.9445% |
| `TREND_FOLLOWING_BASELINE` | +0.0523% | -0.1877% | -0.8177% | -0.3077% | -1.9177% |
| `VOLATILITY_FILTERED_BASELINE` | +0.0493% | -0.1907% | -0.8207% | -0.3107% | -1.9207% |
| `CANDIDATE_A_TREND_PULLBACK` | -0.0404% | -0.2804% | -0.9104% | -0.4004% | -2.0104% |
| `CANDIDATE_B_DONCHIAN_BREAKOUT` | -0.0728% | -0.3128% | -0.9428% | -0.4328% | -2.0428% |

### 2.2 SHORT Direction Net Expected Value (% per trade)

| Filter Name | Gross EV (`SCEN_0`) | Net EV `SCEN_1` (Binance) | Net EV `SCEN_2` (Coinbase) | Net EV `SCEN_3` (Passive [UNVERIFIED]) | Net EV `SCEN_4` (Stressed Vol) |
|---|---|---|---|---|---|
| `UNIFORM_BASELINE` | -0.0536% | -0.2936% | -0.9236% | -0.4136% | -2.0236% |
| `TREND_FOLLOWING_BASELINE` | +0.0433% | -0.1967% | -0.8267% | -0.3167% | -1.9267% |
| `VOLATILITY_FILTERED_BASELINE` | +0.0154% | -0.2246% | -0.8546% | -0.3446% | -1.9546% |
| `CANDIDATE_A_TREND_PULLBACK` | +0.0493% | -0.1907% | -0.8207% | -0.3107% | -1.9207% |
| `CANDIDATE_B_DONCHIAN_BREAKOUT` | **+0.0762%** | **-0.1638%** | **-0.7938%** | **-0.2838%** | **-1.8938%** |

---

## 3. Economic Analysis & Microstructure Mechanics

### 3.1 The Gross vs Net Divergence
In the frictionless academic world (`SCEN_0`), four out of five filters appear mildly profitable on the gross level:
- Short Donchian Breakout: +7.62 bps / trade
- Long Trend Following: +5.23 bps / trade
- Short Trend Pullback: +4.93 bps / trade
- Long Volatility Filter: +4.93 bps / trade

**However, this gross edge is a mathematical mirage.**
The moment the lowest verified retail fee structure (`SCEN_1_BINANCE_VIP0`: 24 bps round trip) is applied:
- Every positive return turns deeply negative.
- The best performing strategy (`CANDIDATE_B` Short) loses **-16.38 bps per trade**.
- Under conservative institutional / retail taker conditions (`SCEN_2_COINBASE_ADV`), the strategy loses **-79.38 bps per trade**.

### 3.2 The Winner's Curse of Passive Execution (`SCEN_3`)
A common proposal in algorithmic trading is to replace taker orders with passive maker limit orders to earn maker rebates or avoid taker fees.

In `SCEN_3_PASSIVE_MAKER`:
- Maker fees reduce nominal fees to 15 bps each way (30 bps total).
- However, our empirical testing assumes a 6.0 bps adverse selection haircut.
- Even under this optimistic, unverified assumption, Net EV remains **negative (-28.38 bps to -43.28 bps)**.
- In actual live markets, fill probability is endogenous:
  1. When price is about to rally sharply to the TP barrier, a passive buy limit order at the bid is left unfilled (lost upside).
  2. When price cascades downward to the SL barrier, the passive buy limit order fills immediately (full adverse exposure).
- Therefore, passive execution cannot rescue an entry system whose gross edge is less than the adverse selection cost.

---

## 4. Required Edge for Economic Viability

To survive verified execution friction and achieve positive net expected value:
$$\text{Gross EV}_{\text{required}} > \text{Round-Trip Fee} + 2 \times \text{Slippage} + \text{Half-Spread}$$

For BTCUSD 24-hour entries:
- Minimum Gross Edge required for Binance VIP 0: **> +24.0 bps**
- Minimum Gross Edge required for Coinbase Advanced: **> +87.0 bps**
- Best observed Gross Edge across all 10 candidate variations: **+7.62 bps**

**Deficit:** The best causal filter falls short of economic viability by at least **16.38 basis points per trade**.

---

## 5. Governance Decision

Under the BTCognitive Epistemic Principles:
> *"No model may be authorized for production or paper trading with negative net expected value after verified fees."*

Because Net EV is negative across all 5 cost scenarios for all evaluated filters:
- **Model Promotion:** `BLOCKED_BY_RESEARCH_VALIDITY`.
- **Trading Authorization:** `DISABLED`.

---

*End of Cost-Adjusted Evaluation Report.*

