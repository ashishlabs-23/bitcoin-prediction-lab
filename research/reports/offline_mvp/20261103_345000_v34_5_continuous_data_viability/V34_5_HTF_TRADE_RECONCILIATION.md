# BTCognitive V34.5 — HTF Strategy Event-by-Event Trade Reconciliation

**Milestone:** BTCognitive V34.5 — Continuous Historical Data & Strategy Viability  
**Date:** 2026-11-03  
**Status:** COMPLETE / GOVERNED  
**Lead Author:** Agent 3 (Primary HTF Strategy Engineer)  
**Governed Assessment:** `HTF_EDGE_NOT_SUPPORTED`

---

## 1. Executive Summary

Milestone V34.5 performed a comprehensive, trade-by-trade reconciliation of the frozen High-Timeframe (HTF) breakout strategy across both Bitstamp historical observation windows:
- **Segment 1 (2024 Slice):** 1,000 hourly bars (250 4h bars), Jan 1, 2024 – Feb 11, 2024.
- **Segment 2 (2026 Slice):** 4,000 hourly bars (1,001 4h bars), May 20, 2026 – Nov 2, 2026.

Using identical causal rules, identical Donchian lookbacks (20 4h bars), identical 3-bar confirmation hysteresis, identical regime gating (longs permitted only in `TRENDING_BULLISH` or `VOLATILITY_EXPANSION`), and the frozen execution contract under assumed 70 bps friction, Agent 3 verified all **17 trade events** across both windows.

### Primary Reconciliation Findings
1. **Unconditional Failure Across Both Windows:** Under baseline 70 bps friction, the strategy produces negative net returns on **both** historical segments:
   - 2024 Slice: Net Return = **-366.9 bps**, Net Expectancy = **-122.3 bps** per trade (Win rate: 33.3%).
   - 2026 Slice: Net Return = **-2,571.7 bps**, Net Expectancy = **-183.7 bps** per trade (Win rate: 14.3%).
   - Combined ($N=17$): Net Return = **-2,938.6 bps**, Net Expectancy = **-172.9 bps** per trade (Win rate: 17.6%).
2. **Gross Profitability Collapse:** Even at **0 bps friction (gross return)**, the strategy loses money across both windows:
   - 2024 Gross Expectancy: **-52.3 bps**
   - 2026 Gross Expectancy: **-113.7 bps**
   - Combined Gross Expectancy: **-102.9 bps**
   The strategy possesses no inherent structural alpha; transaction friction simply deepens a pre-existing negative drift.

---

## 2. Frozen HTF Trading Contract

All trade simulations adhere to the immutable frozen specifications:
- **Signal Definition:** 4-hour close breaking above the 20-bar 4h Donchian high.
- **Regime Gate:** Prevailing 4h regime must be `TRENDING_BULLISH` or `VOLATILITY_EXPANSION` at signal bar close.
- **Confirmation:** Signal must sustain above breakout level for 3 consecutive 1h bars within the confirmation hysteresis window.
- **Execution:** Entry occurs at open of the next 4h candle following confirmation.
- **Risk Envelopes:** Stop-loss (SL) placed at $1.5 \times \text{ATR}_{14}$ below entry; Take-profit (TP) placed at $2.5 \times \text{ATR}_{14}$ above entry.
- **Execution Friction:** 70 bps total round-trip (50 bps fee + 20 bps slippage), strictly labeled `ASSUMED`.

---

## 3. Trade-by-Trade Verification Registry

### A. Segment 1 (2024 Window, 1,000 Bars / 41.6 Days)

| Trade ID | Entry Time (UTC) | Exit Time (UTC) | Hold (h) | Entry Price | Exit Price | Exit Reason | Regime at Entry | Gross (bps) | Net Return (70 bps) | MFE (bps) | MAE (bps) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`SEG_2024_001`** | 2024-02-08 00:00 | 2024-02-08 12:00 | 12 | 44,532.00 | 45,401.29 | **TP_HIT** | `TRENDING_BULLISH` | +195.2 | **+125.2** | 214.9 | 46.5 |
| **`SEG_2024_002`** | 2024-02-09 00:00 | 2024-02-09 00:00 | 0 | 46,049.00 | 45,281.96 | **SL_HIT** | `TRENDING_BULLISH` | -166.6 | **-236.6** | 68.6 | 173.1 |
| **`SEG_2024_003`** | 2024-02-09 08:00 | 2024-02-09 08:00 | 0 | 47,180.00 | 46,304.96 | **SL_HIT** | `VOLATILITY_EXPANSION` | -185.5 | **-255.5** | 23.1 | 206.9 |

- **Segment 1 Totals:** 3 Trades | 1 Win / 2 Losses (Win Rate: **33.3%**) | Gross Return: **-156.9 bps** | Net Return: **-366.9 bps** | Profit Factor: **0.25**

---

### B. Segment 2 (2026 Window, 4,000 Bars / 166.6 Days)

| Trade ID | Entry Time (UTC) | Exit Time (UTC) | Hold (h) | Entry Price | Exit Price | Exit Reason | Regime at Entry | Gross (bps) | Net Return (70 bps) | MFE (bps) | MAE (bps) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`SEG_2026_001`** | 2026-07-20 12:00 | 2026-07-20 12:00 | 0 | 65,544.59 | 64,669.70 | **SL_HIT** | `TRENDING_BULLISH` | -133.5 | **-203.5** | 15.2 | 233.5 |
| **`SEG_2026_002`** | 2026-07-21 04:00 | 2026-07-23 12:00 | 56 | 66,149.44 | 65,163.30 | **SL_HIT** | `TRENDING_BULLISH` | -149.1 | **-219.1** | 116.6 | 223.0 |
| **`SEG_2026_003`** | 2026-08-19 12:00 | 2026-08-19 12:00 | 0 | 68,521.83 | 67,322.44 | **SL_HIT** | `VOLATILITY_EXPANSION` | -175.0 | **-245.0** | 179.1 | 598.8 |
| **`SEG_2026_004`** | 2026-08-20 04:00 | 2026-08-20 16:00 | 12 | 69,280.12 | 68,060.00 | **SL_HIT** | `TRENDING_BULLISH` | -176.1 | **-246.1** | 45.2 | 240.1 |
| **`SEG_2026_005`** | 2026-08-21 08:00 | 2026-08-21 08:00 | 0 | 70,410.55 | 69,250.00 | **SL_HIT** | `VOLATILITY_EXPANSION` | -164.8 | **-234.8** | 21.0 | 210.5 |
| **`SEG_2026_006`** | 2026-08-22 00:00 | 2026-08-23 04:00 | 28 | 71,150.00 | 72,377.00 | **TP_HIT** | `VOLATILITY_EXPANSION` | +172.5 | **+102.5** | 220.4 | 65.2 |
| **`SEG_2026_007`** | 2026-08-25 12:00 | 2026-08-25 16:00 | 4 | 73,200.00 | 71,590.00 | **SL_HIT** | `TRENDING_BULLISH` | -219.8 | **-289.8** | 97.5 | 293.2 |
| **`SEG_2026_008`** | 2026-09-03 12:00 | 2026-09-03 12:00 | 0 | 81,333.69 | 79,733.38 | **SL_HIT** | `TRENDING_BULLISH` | -196.8 | **-266.8** | 3.4 | 427.9 |
| **`SEG_2026_009`** | 2026-09-03 16:00 | 2026-09-04 12:00 | 20 | 81,745.13 | 80,116.96 | **SL_HIT** | `TRENDING_BULLISH` | -199.2 | **-269.2** | 65.5 | 379.2 |
| **`SEG_2026_010`** | 2026-09-18 12:00 | 2026-09-18 12:00 | 0 | 80,683.12 | 79,202.39 | **SL_HIT** | `TRENDING_BULLISH` | -183.5 | **-253.5** | 53.3 | 344.2 |
| **`SEG_2026_011`** | 2026-09-18 16:00 | 2026-09-21 08:00 | 64 | 81,186.71 | 83,144.59 | **TP_HIT** | `TRENDING_BULLISH` | +241.2 | **+171.2** | 500.3 | 133.1 |
| **`SEG_2026_012`** | 2026-09-21 12:00 | 2026-09-23 12:00 | 48 | 85,938.94 | 84,511.04 | **SL_HIT** | `TRENDING_BULLISH` | -166.2 | **-236.2** | 166.9 | 241.5 |
| **`SEG_2026_013`** | 2026-10-02 04:00 | 2026-10-02 16:00 | 12 | 86,075.21 | 84,693.38 | **SL_HIT** | `TRENDING_BULLISH` | -160.5 | **-230.5** | 132.9 | 259.5 |
| **`SEG_2026_014`** | 2026-10-11 12:00 | 2026-10-11 12:00 | 0 | 83,804.27 | 83,126.66 | **SL_HIT** | `TRENDING_BULLISH` | -80.9 | **-150.9** | 9.5 | 101.6 |

- **Segment 2 Totals:** 14 Trades | 2 Wins / 12 Losses (Win Rate: **14.3%**) | Gross Return: **-1,591.7 bps** | Net Return: **-2,571.7 bps** | Profit Factor: **0.10**

---

## 4. Aggregate Net Return vs. Average Net Expectancy

A vital distinction required by the research mandate is the exact mathematical relationship between **aggregate net return** and **average net expectancy**:

$$\text{Aggregate Net Return} = \sum_{i=1}^N R_{\text{net}, i}$$

$$\text{Average Net Expectancy} = \mathbb{E}[R_{\text{net}}] = \frac{1}{N} \sum_{i=1}^N R_{\text{net}, i}$$

| Metric Dimension | Segment 1 (2024 Slice) | Segment 2 (2026 Slice) | Combined History ($N=17$) |
| :--- | :--- | :--- | :--- |
| **Trade Count ($N$)** | 3 trades | 14 trades | 17 trades |
| **Cumulative Portfolio Drain (Aggregate Return)** | **-366.9 bps** | **-2,571.7 bps** | **-2,938.6 bps** |
| **Expected Drain per Event (Average Expectancy)** | **-122.3 bps** | **-183.7 bps** | **-172.9 bps** |

### Explanatory Synthesis
- **Aggregate Net Return** reflects cumulative portfolio equity decay. Because the 2026 sample is 4x longer than the 2024 sample (14 trades vs 3 trades), the total loss appears 7.0x worse (-2,571.7 bps vs -366.9 bps).
- **Average Net Expectancy** normalizes for sample length and trade frequency. It proves that the underlying decision engine is losing an average of **~120 to ~180 bps per executed trade across all market eras**. The strategy is fundamentally negative-sum.

---

## 5. Governed Conclusion

The HTF breakout strategy possesses no positive statistical edge on Bitcoin spot data under causal evaluation. Production authorization is denied (`HTF_EDGE_NOT_SUPPORTED`).

