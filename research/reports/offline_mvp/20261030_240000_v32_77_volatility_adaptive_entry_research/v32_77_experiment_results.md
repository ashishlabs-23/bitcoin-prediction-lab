# BTCognitive V32.77 — Empirical Experiment Results

**Document ID:** `BTC-RES-V3277-001`  
**Milestone:** V32.77 — Volatility-Adaptive Entry Research  
**Date:** October 30, 2026  
**Dataset Evaluated:** `data/raw/ohlcv_checkpoint_42233_bars.parquet` (Frozen 42,233-bar checkpoint)  
**Sample Window:** Out-of-Sample Window (Bars 31,632 to 42,153; August 11, 2025 to October 23, 2026; 10,521 hourly bars)  
**Evaluation Units:** 432 strictly non-overlapping evaluation blocks (sampled every 24 bars)  
**Intra-Bar Collision Rule:** Conservative `SL_FIRST` (Worst-Case Path Resolution)  

---

## 1. Master Empirical Results Grid

The table below presents the full empirical results across all 24 pre-registered evaluation configurations (12 barrier/horizon configurations $\times$ Long and Short directions).

| Index | Configuration | Dir | Horizon | TP Rate (%) | SL Rate (%) | Exp Rate (%) | Mean Gross (%) | Mean Net Binance VIP0 (%) | Mean Net Coinbase Adv (%) | Median MFE (%) | Median MAE (%) | Median Exit Bars |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | `FIXED_24H_TP1.5_SL0.75` | LONG | 24h | 28.01% | 57.41% | 14.58% | +0.0237% | -0.2163% | -0.8463% | 1.121% | 1.224% | 8 |
| 1 | `FIXED_24H_TP1.5_SL0.75` | SHORT | 24h | 28.70% | 60.65% | 10.65% | -0.0135% | -0.2535% | -0.8835% | 1.224% | 1.121% | 8 |
| 2 | `FIXED_72H_TP3.0_SL1.50` | LONG | 72h | 26.62% | 62.27% | 11.11% | -0.0383% | -0.2783% | -0.9083% | 2.189% | 2.259% | 21 |
| 3 | `FIXED_72H_TP3.0_SL1.50` | SHORT | 72h | 32.64% | 57.64% | 9.72% | +0.1814% | -0.0586% | -0.6886% | 2.259% | 2.189% | 22 |
| 4 | `FIXED_168H_TP5.0_SL2.50` | LONG | 168h | 25.69% | 59.95% | 14.35% | -0.0612% | -0.3012% | -0.9312% | 3.236% | 3.643% | 61 |
| 5 | `FIXED_168H_TP5.0_SL2.50` | SHORT | 168h | 28.24% | 55.56% | 16.20% | +0.2429% | **+0.0029%** | -0.6271% | 3.643% | 3.236% | 53 |
| 6 | `ATR_24H_K1.5_0.75` | LONG | 24h | 29.63% | 66.67% | 3.70% | -0.0341% | -0.2741% | -0.9041% | 1.121% | 1.224% | 3 |
| 7 | `ATR_24H_K1.5_0.75` | SHORT | 24h | 33.56% | 63.66% | 2.78% | +0.0234% | -0.2166% | -0.8466% | 1.224% | 1.121% | 3 |
| 8 | `ATR_24H_K2.0_1.00` | LONG | 24h | 30.79% | 62.96% | 6.25% | -0.0180% | -0.2580% | -0.8880% | 1.121% | 1.224% | 5 |
| 9 | `ATR_24H_K2.0_1.00` | SHORT | 24h | 30.56% | 63.89% | 5.56% | +0.0101% | -0.2299% | -0.8599% | 1.224% | 1.121% | 5 |
| 10 | `ATR_24H_K3.0_1.50` | LONG | 24h | 26.16% | 57.87% | 15.97% | -0.0433% | -0.2833% | -0.9133% | 1.121% | 1.224% | 11 |
| 11 | `ATR_24H_K3.0_1.50` | SHORT | 24h | 27.08% | 56.94% | 15.97% | +0.0672% | -0.1728% | -0.8028% | 1.224% | 1.121% | 11 |
| 12 | `ATR_72H_K2.0_1.00` | LONG | 72h | 34.49% | 65.51% | 0.00% | +0.0025% | -0.2375% | -0.8675% | 2.189% | 2.259% | 5 |
| 13 | `ATR_72H_K2.0_1.00` | SHORT | 72h | 32.18% | 67.82% | 0.00% | -0.0164% | -0.2564% | -0.8864% | 2.259% | 2.189% | 5 |
| 14 | `ATR_72H_K3.0_1.50` | LONG | 72h | 33.56% | 65.97% | 0.46% | -0.0093% | -0.2493% | -0.8793% | 2.189% | 2.259% | 11 |
| 15 | `ATR_72H_K3.0_1.50` | SHORT | 72h | 32.41% | 66.90% | 0.69% | +0.0184% | -0.2216% | -0.8516% | 2.259% | 2.189% | 11 |
| 16 | `ATR_72H_K4.0_2.00` | LONG | 72h | 32.41% | 62.04% | 5.56% | +0.0279% | -0.2121% | -0.8421% | 2.189% | 2.259% | 14 |
| 17 | `ATR_72H_K4.0_2.00` | SHORT | 72h | 33.80% | 62.50% | 3.70% | +0.1260% | -0.1140% | -0.7440% | 2.259% | 2.189% | 15 |
| 18 | `ATR_168H_K3.0_1.50` | LONG | 168h | 33.56% | 66.44% | 0.00% | -0.0244% | -0.2644% | -0.8944% | 3.236% | 3.643% | 11 |
| 19 | `ATR_168H_K3.0_1.50` | SHORT | 168h | 32.87% | 67.13% | 0.00% | +0.0196% | -0.2204% | -0.8504% | 3.643% | 3.236% | 11 |
| 20 | `ATR_168H_K5.0_2.50` | LONG | 168h | 34.26% | 64.81% | 0.93% | +0.0329% | -0.2071% | -0.8371% | 3.236% | 3.643% | 19 |
| 21 | `ATR_168H_K5.0_2.50` | SHORT | 168h | 34.26% | 64.81% | 0.93% | +0.1629% | -0.0771% | -0.7071% | 3.643% | 3.236% | 20 |
| 22 | `ATR_168H_K6.0_3.00` | LONG | 168h | 31.71% | 64.81% | 3.47% | -0.0590% | -0.2990% | -0.9290% | 3.236% | 3.643% | 26 |
| 23 | `ATR_168H_K6.0_3.00` | SHORT | 168h | 33.80% | 63.19% | 3.01% | +0.1936% | -0.0464% | -0.6764% | 3.643% | 3.236% | 30 |

*Note: Fee schedules applied: Binance VIP0 = 24.0 bps round-trip (10 bps fee + 2 bps slip $\times$ 2 legs); Coinbase Advanced = 87.0 bps round-trip (35 bps fee + 8.5 bps slip $\times$ 2 legs).*

---

## 2. Hypothesis-by-Hypothesis Analysis

### 2.1 Hypothesis 1 ($H_1$): Volatility-Adaptive Barriers

- **Question:** Does scaling take-profit and stop-loss barriers proportionally to local ATR(14) yield higher net expected value than fixed percentage barriers?
- **Empirical Findings:**
  - In 24h holding windows:
    - Fixed 24h Long net return: $-0.2163\%$ (Binance VIP0).
    - ATR 24h ($K=1.5/0.75$) Long net return: $-0.2741\%$.
    - ATR 24h ($K=2.0/1.00$) Long net return: $-0.2580\%$.
    - ATR 24h ($K=3.0/1.50$) Long net return: $-0.2833\%$.
  - In 72h holding windows:
    - Fixed 72h Short net return: $-0.0586\%$.
    - ATR 72h ($K=4.0/2.00$) Short net return: $-0.1140\%$.
  - In 168h holding windows:
    - Fixed 168h Short net return: $+0.0029\%$.
    - ATR 168h ($K=6.0/3.00$) Short net return: $-0.0464\%$.
- **Statistical Significance (Diebold-Mariano test vs Fixed 24h):**
  - None of the ATR-scaled configurations demonstrated a statistically significant improvement over the fixed baseline ($p > 0.35$ across all paired HLN-corrected DM tests).
- **Conclusion:** **$H_1$ Fails to Reject the Null Hypothesis.** ATR scaling dynamically accommodates market width, but in an unconditional entry context, it does not create positive risk-adjusted alpha.

---

### 2.2 Hypothesis 2 ($H_2$): Extended Holding Horizons

- **Question:** Does extending the maximum holding horizon ($H = 24\text{h} \to 72\text{h} \to 168\text{h}$) reduce the proportional fee drag sufficiently to achieve profitable trading economics?
- **Empirical Findings:**
  - Fee burden contracts substantially as horizon lengthens:
    - At 24h ($TP = 1.5\%$), 24 bps round-trip fee is $16.0\%$ of nominal target.
    - At 72h ($TP = 3.0\%$), 24 bps round-trip fee is $8.0\%$ of nominal target.
    - At 168h ($TP = 5.0\%$), 24 bps round-trip fee is $4.8\%$ of nominal target.
  - As a direct result, gross short returns scale from $-0.0135\%$ (24h) $\to +0.1814\%$ (72h) $\to +0.2429\%$ (168h).
  - On `FIXED_168H_TP5.0_SL2.50` Short, net return on Binance VIP0 crosses slightly into positive territory ($+0.0029\%$).
- **The Excursion & Asymmetry Penalty:**
  - Long 168h suffered net losses of $-0.3012\%$, reflecting directional regime bias rather than bilateral edge.
  - Median Maximum Adverse Excursion (MAE) expanded from $1.12\%$ at 24h to $3.64\%$ at 168h.
  - Under Coinbase Advanced retail costs, `FIXED_168H` Short lost $-0.6271\%$ per trade.
  - Adding unhedged 8h funding rate drag (+11.2% annualized in bull phases) wipes out the nominal $+0.29\text{ bps}$ Binance edge.
- **Conclusion:** **$H_2$ Provides Gross Fee Relief but Suffers Unacceptable Excursion Risk.** While 72h and 168h reduce relative fee friction, they cannot be deployed without an external directional regime filter to avoid holding through major adverse trends.

---

### 2.3 Hypothesis 3 ($H_3$): Microstructure Confirmation

- **Question:** Can Level 2 order-book imbalance or depth skew confirm entry and improve win rates?
- **Empirical Findings:**
  - Local disk audit reveals only 5 files in `data/research/l2_stream/`, spanning 59 minutes on October 25, 2026.
  - Zero historical L2 data exists across the 10,521 OOS bars.
  - Synthetic fabrication is prohibited under Prime Directive §2.5.
- **Conclusion:** **$H_3$ Declared `BLOCKED_BY_DATA`.**

---

## 3. Cost-Sensitivity Summary

| Cost Tier | Description | Round-Trip Cost | Best Config Net EV | Status |
|---|---|:---:|:---:|:---:|
| **SCEN_1 (Binance VIP0 Taker)** | Institutional Baseline | 24.0 bps | `FIXED_168H` Short: +0.29 bps | Fragile / Trend Asymmetry |
| **SCEN_2 (Coinbase Advanced Taker)** | Governed Retail Baseline | 87.0 bps | `FIXED_168H` Short: -62.71 bps | **FAIL (Deficit)** |
| **SCEN_3 (Passive Maker)** | Pure Post-Only Limit | -1.0 bps rebate | Hypothesized +25.29 bps | **DISQUALIFIED (Zero fill proof)** |
| **SCEN_4 (Conservative Taker)** | Adverse Slippage Stress | 114.0 bps | All configs < -89.0 bps | **FAIL (Deficit)** |
| **SCEN_5 (Institutional VIP9)** | Zero Fee / Rebate Tier | 4.0 bps | `FIXED_168H` Short: +20.29 bps | Inaccessible to standard deployment |

---

## 4. Final Scientific Synthesis

Milestone V32.77 has rigorously evaluated volatility adaptation and horizon extension across 432 non-overlapping OOS blocks under conservative path-collision assumptions. The empirical verdict is unequivocal: **Neither ATR scaling nor extended holding periods solve the fundamental profitability deficit in the absence of an asymmetric directional signal.**

