# BTCognitive V32.78 — Compression and Breakout Entry Research

**Document ID:** `BTC-CMP-V3278-001`  
**Milestone:** V32.78 — Asymmetric Regime-Conditioned Entry Research  
**Author:** Specialist Workstream 3 (Volatility Compression & Breakout Dynamics)  
**Date:** October 30, 2026  
**Status:** COMPLETE / EMPIRICAL RESEARCH  
**Dataset:** `data/raw/ohlcv_checkpoint_42233_bars.parquet` (Frozen 42,233-bar checkpoint)  
**Sample Window:** Out-of-Sample Window (Bars 31,632 to 42,153; 10,521 hourly bars; Aug 2025 – Oct 2026)  

---

## 1. Executive Summary

Specialist Workstream 3 evaluated whether conditioning directional entries on **volatility compression** (defined causally as 14-period NATR $\le 0.40\%$ or 20-period Bollinger Band Width $\le 1.30\%$) followed by a 20-bar Donchian channel breakout resolves the negative expected value identified in unconditional entry models.

### Key Empirical Findings:
1. **Short Breakouts Exhibit Directional Asymmetry:** Over the 72-hour primary holding horizon (`COMP_BO_72H`), Short breakouts produced an unconditional gross return of $+0.3527\%$ (+35.3 bps) and a net return of $+0.1127\%$ (+11.3 bps) under institutional Binance VIP0 taker fees (24 bps RT).
2. **Long Breakouts Fail Completely:** Under the identical compression filter, Long breakouts (`COMP_BO_72H Long`) yielded $-0.0230\%$ gross and $-0.2630\%$ net under Binance VIP0 fees, with a $58.8\%$ stop-loss hit rate.
3. **Severe Sample Size Limitation:** The strict compression filter triggered only $N = 33$ Short trades across the entire 14-month OOS period (averaging ~2.3 trades per month).
4. **Chronological Sub-Period Breakdown:** Split-sample verification reveals extreme temporal instability:
   - **H1 (Aug 2025 – Mar 2026):** $N = 12$, Mean Gross $+1.0317\%$, Net VIP0 $+0.7917\%$.
   - **H2 (Mar 2026 – Oct 2026):** $N = 21$, Mean Gross $-0.0352\%$, Net VIP0 $-0.2752\%$.
   The apparent gross edge in H1 disappeared during H2, proving that the signal was riding a secular market downtrend rather than an enduring structural alpha.
5. **Retail Cost Inviability:** Under standard retail fee schedules (Coinbase Advanced, 87 bps RT), `COMP_BO_72H Short` realized a net loss of $-0.5173\%$ (-51.7 bps per trade).

---

## 2. Experimental Setup & Signal Definitions

Entries are strictly point-in-time:
- **Conditioning State:** Candle $t$ must satisfy $\text{NATR}_{14, t} \le 0.40\%$ OR $\text{BBW}_{20, 2, t} \le 1.30\%$.
- **Long Breakout Trigger:** $C_t > \max_{1 \le i \le 20} H_{t-i}$.
- **Short Breakout Trigger:** $C_t < \min_{1 \le i \le 20} L_{t-i}$.
- **Execution:** Position enters at $O_{t+1}$.
- **Barriers (72h Primary):** Take-Profit at $+3.0\%$ (Long) / $-3.0\%$ (Short); Stop-Loss at $-1.5\%$ (Long) / $+1.5\%$ (Short).
- **Collision Rule:** Worst-case `SL_FIRST`.
- **Non-Overlapping Spacing:** 24-hour minimum spacing between trade exits and subsequent entries.

---

## 3. Empirical Results Across Horizons

| Metric | Long (24h) | Short (24h) | Long (72h) | Short (72h) | Short (168h) |
|---|:---:|:---:|:---:|:---:|:---:|
| **Sample Count ($N$)** | 59 | 42 | 51 | 33 | 27 |
| **TP Hit Rate (%)** | 16.95% | 28.57% | 25.49% | 33.33% | 29.63% |
| **SL Hit Rate (%)** | 59.32% | 59.52% | 58.82% | 48.48% | 48.15% |
| **Time Expiration (%)** | 23.73% | 11.90% | 15.69% | 18.18% | 22.22% |
| **Mean Gross Return (%)** | -0.0932% | -0.0071% | -0.0230% | **+0.3527%** | **+0.5273%** |
| **Net Return (Binance VIP0: 24 bps)** | -0.3332% | -0.2471% | -0.2630% | **+0.1127%** | **+0.2873%** |
| **Net Return (Coinbase Adv: 87 bps)** | -0.9632% | -0.8771% | -0.8930% | -0.5173% | -0.3427% |
| **Median MFE (%)** | 0.54% | 0.68% | 1.69% | 1.60% | 3.17% |
| **Median MAE (%)** | 0.78% | 0.81% | 1.56% | 1.33% | 2.22% |
| **Median Exit Bars** | 10 | 9 | 33 | 23 | 85 |

---

## 4. Workstream 3 Determination

1. **Rejection of Bilateral Alpha:** Compression breakouts do not produce a robust, two-sided edge. The Long side is consistently negative across all horizons ($-26.3\text{ bps}$ net at 72h).
2. **Rejection of Short Breakout for Production:** Although Short 72h achieved $+11.3\text{ bps}$ net under institutional VIP0 fees, it fails every governance standard:
   - Sample count ($N = 33$) falls far short of the minimum 100-event requirement.
   - Chronological breakdown confirms regime decay ($-27.5\text{ bps}$ in H2).
   - Under retail execution costs, it loses $-51.7\text{ bps}$ per trade.
3. **Recommendation:** Do NOT promote compression breakouts to candidate production models.

