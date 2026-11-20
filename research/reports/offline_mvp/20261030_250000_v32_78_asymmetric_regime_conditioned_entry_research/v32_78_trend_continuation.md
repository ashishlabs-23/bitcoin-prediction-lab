# BTCognitive V32.78 — Trend Continuation and Pullback Research

**Document ID:** `BTC-TRN-V3278-001`  
**Milestone:** V32.78 — Asymmetric Regime-Conditioned Entry Research  
**Author:** Specialist Workstream 4 (Trend Dynamics & Pullback Mechanics)  
**Date:** October 30, 2026  
**Status:** COMPLETE / EMPIRICAL RESEARCH  
**Dataset:** `data/raw/ohlcv_checkpoint_42233_bars.parquet` (Frozen 42,233-bar checkpoint)  
**Sample Window:** Out-of-Sample Window (Bars 31,632 to 42,153; 10,521 hourly bars; Aug 2025 – Oct 2026)  

---

## 1. Executive Summary

Specialist Workstream 4 investigated whether conditioning entry on **trend continuation following a confirmed pullback** improves conditional trade economics compared with immediate trend-following or unconditional entry.

The central hypothesis posited that waiting for a price retrace to a moving trend anchor (50-period EMA slope $\ge |0.50\%|$ with 14-period RSI pulling back into the neutral consolidation zone: $40 \le \text{RSI} \le 50$ for Longs, $50 \le \text{RSI} \le 60$ for Shorts) avoids buying at overextended local tops or shorting at local bottoms, thereby dampening adverse excursion and elevating the reward-to-risk realization.

### Key Empirical Findings:
1. **The Pullback Hypothesis Fails Emphatically:** Across both Long and Short directions, trend continuation pullbacks experienced severe stop-out rates ($66.67\%$ for Long, $64.86\%$ for Short on 72h horizons).
2. **Negative Net Expected Value Across All Horizons:**
   - 72h Long Pullbacks: Mean gross return $-0.2454\%$; Net Binance VIP0 $-0.4854\%$; Net Coinbase $-1.1154\%$.
   - 72h Short Pullbacks: Mean gross return $-0.1250\%$; Net Binance VIP0 $-0.3650\%$; Net Coinbase $-0.9950\%$.
   - 24h Short Pullbacks: Mean gross return $-0.0002\%$; Net Binance VIP0 $-0.2402\%$.
   - 168h Short Pullbacks: Mean gross return $+0.1868\%$; Net Binance VIP0 $-0.0532\%$.
3. **The "Pullback vs. Reversal" Trap:** In Bitcoin hourly data, what appears causally as a "pullback into moving support" frequently develops into a full-scale trend reversal or liquidation cascade. The stop loss at $1.5\%$ is systematically triggered before the broader structural trend resumes.
4. **Excursion Profile:** Median MAE on 72h pullbacks was $1.58\%$ (Long) and $1.66\%$ (Short), both exceeding the $1.50\%$ stop-loss threshold, guaranteeing premature liquidation.

---

## 2. Experimental Setup & Signal Formulations

All conditions evaluated at candle $t$ close; entered at $O_{t+1}$:
- **Trend Alignment Slope:** $\text{TAS}_t = \frac{\text{EMA}_{20, t} - \text{EMA}_{50, t}}{\text{EMA}_{50, t}}$.
- **Volatility Filter:** $0.40\% \le \text{NATR}_{14, t} \le 0.78\%$ (excludes quiet consolidation and extreme turbulence).
- **Long Pullback Signal:** $\text{TAS}_t \ge +0.50\%$ and $40 \le \text{RSI}_{14, t} \le 50$.
- **Short Pullback Signal:** $\text{TAS}_t \le -0.50\%$ and $50 \le \text{RSI}_{14, t} \le 60$.
- **Barriers:**
  - 24h: TP $+1.5\%$, SL $-0.75\%$
  - 72h: TP $+3.0\%$, SL $-1.50\%$
  - 168h: TP $+5.0\%$, SL $-2.50\%$
- **Collision Rule:** Conservative worst-case `SL_FIRST`.

---

## 3. Empirical Results Across Horizons

| Configuration | Direction | Horizon | $N$ | TP Rate (%) | SL Rate (%) | Expire Rate (%) | Mean Gross (%) | Net VIP0 (%) | Net Coinbase (%) | Median MAE (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `TREND_PB_24H` | SHORT | 24h | 37 | 29.73% | 62.16% | 8.11% | -0.0002% | -0.2402% | -0.8702% | 0.80% |
| `TREND_PB_72H` | LONG | 72h | 42 | 26.19% | 66.67% | 7.14% | -0.2454% | -0.4854% | -1.1154% | 1.58% |
| `TREND_PB_72H` | SHORT | 72h | 37 | 27.03% | 64.86% | 8.11% | -0.1250% | -0.3650% | -0.9950% | 1.66% |
| `TREND_PB_168H` | SHORT | 168h | 32 | 28.12% | 53.12% | 18.75% | +0.1868% | -0.0532% | -0.6832% | 2.53% |

---

## 4. Deep-Dive: Why Pullback Strategies Fail in Crypto

1. **Path-Dependent Liquidation Dynamics:** In traditional equity or FX markets, pullbacks reflect orderly liquidity provision by specialists. In crypto derivatives, pullbacks frequently cascade due to leveraged stop-hunts. A 1.5% retracement in BTC is insufficient buffer to avoid stop hunting.
2. **Martingale Hitting Probabilities:** Under a 2:1 barrier ($TP = 2 \cdot SL$), the theoretical random-walk stop probability is $66.67\%$. The empirical stop-out rates of `TREND_PB_72H` ($66.67\%$ Long, $64.86\%$ Short) align almost perfectly with pure noise, demonstrating that RSI pullbacks within moving average trends provide **zero directional predictive advantage**.
3. **Severe Cost Drag:** Because the hit rate does not exceed martingale noise, trading friction (24 to 87 bps round-trip) produces a relentless linear capital depletion.

---

## 5. Workstream 4 Determination

Specialist Workstream 4 issues a definitive **REJECTION** of standard trend pullback entry conditioning for BTCUSD. Moving average slopes combined with RSI consolidation fail to protect against trend breakdown and do not generate an investable edge.

